import sys
import re
import ruamel.yaml
from packaging import version
import random
import logging

# This line has been commened out as it is the verbose  logging option.
# comment in this line and comment out the non verbose option below if required for more complex logging.
# logging.basicConfig(level=logging.INFO)

# This is the non verbose logging view
logging.basicConfig(level=logging.INFO, format='%(message)s')

TARGET_VERSION = "4.13"

IDX_DAY_OF_MONTH = 2
IDX_DAY_OF_WEEK = 4

# Define a dictionary to store version-specific cron strings
VERSION_SCHEDULES = {
    '4.13': "weekly-weekend",
    '4.12': "do_not_touch",
    '4.7-4.11': "bi-weekly-weekend",
    'default': "bi-weekly-weekend",
    'end_of_life': "yearly",
}

# Checks if the given version (ver) is lower or equal to the target version.
def version_lower_than_or_equal(ver, target):
    ver_v = version.parse(ver)
    if ver.find("priv") != -1:
        v = ver.split("-")
        ver_v = version.parse(v[0])
    target_v = version.parse(target)
    return (ver_v < target_v or ver_v == target_v)

# Generates a random cron string based on the schedule type (e.g., bi-weekly, monthly).
def generate_cron_string(schedule_type):
    if schedule_type == "weekly-weekend-4.13":
        day = random.choice([6, 7])  # Randomly pick either Saturday (6) or Sunday (7)
        return f"{random.randint(0, 59)} {random.randint(0, 23)} * * {day}"  # Random minute and hour
    elif schedule_type == "bi-weekly-weekend":
        return f"{random.randint(0, 59)} {random.randint(0, 23)} */14 * 6-7"
    elif schedule_type == "bi-weekly-other":
        return f"{random.randint(0, 59)} {random.randint(0, 23)} */14 * 1-5"
    elif schedule_type == "monthly-weekend":
        return f"{random.randint(0, 59)} {random.randint(0, 23)} 1 * 6-7"
    elif schedule_type == "weekly-weekend":
        return f"{random.randint(0, 59)} {random.randint(0, 23)} * * 6-7"
    elif schedule_type == "yearly":
        return f"{random.randint(0, 59)} {random.randint(0, 23)} 1 1 *"
    else:
        # Default cron: every 2nd week (choose the best day for you)
        return f"{random.randint(0, 59)} {random.randint(0, 23)} */14 * *"

# Categorizes the frequency of a given cron job (e.g., daily, monthly).
def categorize_cron_frequency(cron, filename):
    try:
        if cron is None:
            with open("cron_errors.txt", "a") as f:
                f.write(f"{filename}: None input\n")
            return 'Edge case exception'

        if not cron:
            with open("cron_errors.txt", "a") as f:
                f.write(f"{filename}: Empty input\n")
            return 'Edge case exception'

        if len(cron) > 5:
            with open("cron_errors.txt", "a") as f:
                f.write(f"{filename}: Too many elements\n")
            return 'Edge case exception'

        if len(cron) != 5:
            if cron[0] in ['@yearly', '@annually']:
                return 'Yearly'
            if cron[0] == '@monthly':
                return 'Monthly'
            if cron[0] == '@weekly':
                return 'Weekly'
            if cron[0] == '@daily':
                return 'Daily'
            if cron[0] == '@hourly':
                return 'Hourly'
            return 'Edge case exception'

        minute, hour, day_of_month, month, day_of_week = cron

        # Special Cases
        if day_of_month == '18' and month == '*/12':
            return 'Semi-annually'
        
        if day_of_month == '16' and month == '*/12':
            return 'Semi-annually'
        
        # Additional Special Cases
        if minute == '0' and hour == '12' and day_of_month == '*' and month == '*' and day_of_week == '6':
            return 'Every Saturday at noon'
        
        if minute == '0' and hour == '0' and day_of_month == '1' and month == '1' and day_of_week == '*':
            return 'Every January 1st at midnight'
        
        if minute == '0' and hour == '12' and day_of_month == '*' and month == '*' and day_of_week == '6':
            return 'Every Saturday at noon'
            
        if minute == '0' and hour == '0' and day_of_month == '1' and month == '1' and day_of_week == '*':
            return 'Every January 1st at midnight'
        
        # Daily
        if minute != '*' and hour != '*' and day_of_month == '*' and month == '*' and day_of_week == '*':
            return 'Daily'

        # Weekly
        if minute != '*' and hour != '*' and day_of_month == '*/7' and month == '*' and day_of_week == '*':
            return 'Weekly'

        # Bi-weekly
        if minute != '*' and hour != '*' and day_of_month == '*/14' and month == '*' and day_of_week == '1-5':
            return 'Bi-weekly weekdays only'
        if minute != '*' and hour != '*' and day_of_month == '*/14' and month == '*' and day_of_week == '6-7':
            return 'Bi-weekly weekends only'
        if minute != '*' and hour != '*' and day_of_month == '*/14' and month == '*' and day_of_week == '*':
            return 'Bi-weekly any day'

        # Monthly
        if minute != '*' and hour != '*' and day_of_month != '*' and month == '*' and day_of_week == '*':
            return 'Monthly'
        if minute != '*' and hour != '*' and day_of_month != '*' and month == '*' and day_of_week == '1-5':
            return 'Monthly weekdays'
        if minute != '*' and hour != '*' and day_of_month != '*' and month == '*' and day_of_week == '6-7':
            return 'Monthly weekends'
        
        # Weekly on specific day(s)
        if minute != '*' and hour != '*' and day_of_month == '*' and month == '*' and day_of_week != '*':
            return 'Weekly on specific day(s)'
        
        # Monthly on specific day(s)
        if minute != '*' and hour != '*' and day_of_month != '*' and month == '*' and day_of_week == '*':
            return 'Monthly on specific day(s)'
        
        # Monthly on specific weekday(s)
        if minute != '*' and hour != '*' and day_of_month == '*' and month == '*' and day_of_week != '*':
            return 'Monthly on specific weekday(s)'
        
        # Yearly
        if minute != '*' and hour != '*' and day_of_month != '*' and month != '*' and day_of_week == '*':
            return 'Yearly'
        
        # Daily
        if minute != '*' and hour != '*' and day_of_month == '*' and month == '*' and day_of_week == '*':
            return 'Daily'
        
        # Hourly
        if minute != '*' and hour == '*' and day_of_month == '*' and month == '*' and day_of_week == '*':
            return 'Hourly'
        
        # Unclassified for anything else
        return 'Unclassified'

    except Exception as e:
        with open("cron_errors.txt", "a") as f:
            f.write(f"{filename}: {e}\n")
        return 'Edge case exception'

# Fetches the cron schedule for a specific version using a predefined dictionary.
def get_version_schedule(ver):
    if ver == '4.13':
        return 'weekly-weekend-4.13'
    elif ver == '4.12':
        return 'do_not_touch'
    elif '4.7' <= ver <= '4.11':
        return 'bi-weekly-weekend'
    return VERSION_SCHEDULES.get(ver, VERSION_SCHEDULES['default'])

# Processes the 'interval' key in a test and converts it to a default bi-weekly cron schedule regardless of its original frequency.
# This helps maintain consistent cron scheduling across all tests and this replaces all interval tests.
def process_interval(test):
    changes_made = []
    name = test['as'] if 'as' in test else test['name']
    
    if 'interval' not in test:
        logging.info(f'test {name} does not have an interval key')
        return []
        
    # Generate bi-weekly cron string regardless of the original interval
    schedule_type = "bi-weekly-weekend"  # Default to bi-weekly on a random day and time
    cron_string = generate_cron_string(schedule_type)
    
    logging.info(f'Converting interval {test["interval"]} to cron {cron_string}')
    del test['interval']
    test["cron"] = cron_string
    changes_made.append("converted_to_cron")

    return changes_made

# Appends unrecognized cron strings to a text file.
def save_unrecognized_cron(cron, filename):
    with open("unrecognized_crons.txt", "a") as f:
        f.write(f"{cron} in {filename}\n")

# Processes the 'cron' key in a test. Replaces it if it's daily or less than bi-weekly.
def process_cron(test, ver, filename):
    changes_made = []
    name = test['as'] if 'as' in test else test['name']
    logging.info(f'found test {name} with cron {test["cron"]}')
    
    cron = re.split(r'\s+', test['cron'].strip())
    cron_category = categorize_cron_frequency(cron, FILENAME)
    logging.info(f'Cron category: {cron_category}')

    # Get the desired schedule type for this version
    schedule_type = get_version_schedule(ver)
    cron_string = generate_cron_string(schedule_type)

    # Handle versions older than 4.12
    if version.parse(ver) < version.parse('4.12'):
        if cron_category not in ['Bi-weekly any day', 'Monthly']:
            logging.info(f'Updating older version {ver} to be either bi-weekly or monthly')
            schedule_type = random.choice(['bi-weekly-weekend', 'monthly-weekend'])  # Randomize to either bi-weekly or monthly
            cron_string = generate_cron_string(schedule_type)
            del test['cron']
            test["cron"] = cron_string
            changes_made.append("updated_old_version")

    # Decision based on cron_category
    elif cron_category in ['Daily', 'Less than bi-weekly']:
        logging.info(f'Replacing cron {cron} based on its category {cron_category}')
        del test['cron']
        test["cron"] = cron_string
        changes_made.append("replaced")

    elif cron_category == 'Unrecognized':
        logging.info(f'Unrecognized cron {cron}')
        save_unrecognized_cron(test["cron"], filename)

    else:
        logging.info(f'No changes for cron {cron} in category {cron_category}')

    return changes_made

# Adds a 'promote' key to tests that start with 'promote-'.
def process_promote(test):
    changes_made = []
    name = test['as'] if 'as' in test else test['name']
    logging.info(f'found promote test {name}')
    
    # Your specific logic for 'promote-' tests can go here
    # For example, let's say you want to add a 'promote' key to the test dict
    test['promote'] = True
    changes_made.append("promoted")

    return changes_made

# Calls specific processing functions based on the keys present in the test.
def replace(test, ver, filename):
    changes_made = []
    
    name = test['as'] if 'as' in test else test['name']
    
    if name.startswith('promote-'):
        changes_made.extend(process_promote(test))
    elif 'interval' in test:
        changes_made.extend(process_interval(test, ver))
    elif 'cron' in test:
        changes_made.extend(process_cron(test, ver, filename))
        
    return changes_made

# Processes 'ciops' data, replacing intervals and crons if needed.
def process_ciops(data, filename):
    section_latest = data.get('releases', {}).get('latest', {})
    if not section_latest:
        return False
    release_ref = list(section_latest.keys())[0]

    if 'version' in section_latest[release_ref]:
        ver = section_latest[release_ref].get('version')
    elif 'name' in section_latest[release_ref]:
        ver = section_latest[release_ref].get('name')
    elif 'version_bounds' in section_latest[release_ref]:
        ver = section_latest[release_ref].get('version_bounds', {}).get('upper')

    if not ver or not version_lower_than_or_equal(ver, TARGET_VERSION):
        return False

    pending_replacements = []
    logging.info(f'Found version {ver} lower than the target version {TARGET_VERSION} in {filename}')
    for test in data.get('tests', []):
        pending_replacements.extend(replace(test, ver, FILENAME))  # Call 'replace' here
    
    return pending_replacements

# Processes 'job' data, replacing cron strings if they meet certain conditions.
def process_job(data, filename):
    for periodic in data.get('periodics', []):
        if 'ci.openshift.io/generator' in periodic.get('labels', {}):
            continue

        if periodic.get('name', '').startswith('promote-'):
            continue

        version_satisfied = False
        for ref in periodic.get('extra_refs', []):
            base_ref = ref.get('base_ref', '').split('-')
            if len(base_ref) != 2:
                logging.info(f'unrecognised base_ref {base_ref}')
                continue
            ver = base_ref[1]
            if ver and version_lower_than_or_equal(ver, TARGET_VERSION):
                version_satisfied = True
                break

        if 'job-release' in periodic.get('labels', {}):
            ver = periodic.get('labels', {}).get('job-release')
            if ver and version_lower_than_or_equal(ver, TARGET_VERSION):
                version_satisfied = True

        if not version_satisfied:
            return False

        # Get the schedule type for this version
        schedule_type = get_version_schedule(ver)
        
        # Skip this file entirely if it's a "do_not_touch" type
        if schedule_type == "do_not_touch":
            return []

        pending_replacements = []
        logging.info(f'Found version {ver} lower than the target version {TARGET_VERSION} in {filename}')
        pending_replacements.extend(process_cron(periodic, ver, FILENAME))

        return pending_replacements

if __name__ == '__main__':
    FILENAME = sys.argv[1]

    with open(FILENAME, 'r', encoding='utf-8') as fp:
        ycontent = fp.read()

    yaml = ruamel.yaml.YAML()
    pending = []
    all_data = list(yaml.load_all(ycontent))
    file_changed = False
    for data in all_data:
        ret = process_ciops(data, FILENAME)
        ret2 = process_job(data, FILENAME)
        if ret or ret2:
            file_changed = True

    if file_changed:
        with open(FILENAME, 'w', encoding='utf-8') as fp:
            yaml.dump_all(all_data, fp)