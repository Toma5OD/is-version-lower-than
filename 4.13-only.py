import sys
import ruamel.yaml
from packaging import version
import random
import logging
from croniter import croniter
from datetime import datetime, timedelta
from calendar import monthrange

# THIS FILE SIMPLY REPLACES ALL CRONS AND REPLACES ALL INTERVALS THAT AREN'T WEARLY, ANNUALLY, OR MONTHLY.

# This is the non verbose logging view
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Check for yaml files that are equal to or lower than the target version.
TARGET_VERSION = "4.13"


# Set of special cron strings to keep
keep_intervals = {'@yearly', '@annually', '@monthly'}

def process_interval(test, ver):
    changes_made = []
    name = test.get('as', test.get('name', 'Unknown'))

    # Check if name was found, and log if it defaults to 'Unknown'
    if name == 'Unknown':
        log_missing_name(test)

    # Initial Check
    if name.startswith("promote-") or name.startswith("mirror-nightly-image"):
        logging.info(f"Found and ignored {name}")
        return []

    # Logging Interval
    logging.info(f'Found test in {name} with interval {test["interval"]}')

    # Process for version 4.13
    if ver == "4.13":
        if 'interval' in test:
            interval = test['interval'].strip()

            # Check if interval is already weekly or more
            if interval in keep_intervals or (interval.endswith('h') and int(interval[:-1]) >= 24 * 7) or (interval.endswith('m') and int(interval[:-1]) >= 24 * 7 * 60):
                pass  # Do nothing, keep the interval as it's already weekly or more
            else:
                # Replace intervals more frequent than weekly
                new_cron = f"{random.randint(0, 59)} {random.randint(0, 23)} * * {random.choice([6, 0])}"
                del test['interval']
                test['cron'] = new_cron
                changes_made.append(f"Replaced interval with cron for {test['name']} for 4.13")

    return changes_made

def process_cron(test, ver):
    changes_made = []
    name = test.get('as', test.get('name', 'Unknown'))

    # Check if name was found, and log if it defaults to 'Unknown'
    if name == 'Unknown':
        log_missing_name(test)

    # Logging and Early Return for Certain Tests
    if name.startswith("promote-") or name.startswith("mirror-nightly-image"):
        logging.info(f"Found and ignored {name}")
        return []

    # Processing for specific version conditions
    if ver == "4.13":
        # Logic for version 4.13
        cron_expression = test['cron']
        year, month = 2023, 1
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        cron = croniter(cron_expression, start_date)
        execution_count = 0
        while cron.get_next(datetime) <= end_date:
            execution_count += 1
        if execution_count > 4:
            new_cron = f"{random.randint(0, 59)} {random.randint(0, 23)} * * {random.choice([6, 0])}"
            test['cron'] = new_cron
            changes_made.append(f"Updated cron for {test['name']} to weekly on Saturday or Sunday for 4.13")

    return changes_made

def log_missing_name(test):
    log_path = 'missing_names_log.txt'
    with open(log_path, 'a') as log_file:
        log_file.write(f"Missing name or as field in test: {test}\n")

def process_promote(test):
    changes_made = []
    name = test.get('as', test.get('name', 'Unknown'))

    # Check if name was found, and log if it defaults to 'Unknown'
    if name == 'Unknown':
        log_missing_name(test)
        return []  # Skip processing this test if the name is unknown

    logging.info(f'Found promote test {name}')

    # Your specific logic for 'promote-' tests can go here
    test['promote'] = True
    changes_made.append("promoted")

    return changes_made

def replace(test):
    changes_made = []
    name = test.get('as', test.get('name', 'Unknown'))

    if name == 'Unknown':
        log_missing_name(test)
        return []  # Skip processing this test if the name is unknown

    if name.startswith('promote-') or name.startswith('mirror-nightly-image'):
        return changes_made

    # Process based on test type for version 4.13
    if 'interval' in test:
        changes_made.extend(process_interval(test))
    elif 'cron' in test:
        changes_made.extend(process_cron(test))

    return changes_made

def process_ciops(data, filename):
    section_latest = data.get('releases', {}).get('latest', {})
    if not section_latest:
        return []

    release_ref = list(section_latest.keys())[0]

    if 'version' in section_latest[release_ref]:
        ver = section_latest[release_ref].get('version')
    elif 'name' in section_latest[release_ref]:
        ver = section_latest[release_ref].get('name')
    elif 'version_bounds' in section_latest[release_ref]:
        ver = section_latest[release_ref].get(
            'version_bounds', {}).get('upper')

    # Skip if filename starts with "promote-" or "mirror-nightly-image"
    if filename.startswith("promote-") or filename.startswith("mirror-nightly-image"):
        logging.info(
            f"Skipping file {filename} starting with promote- or mirror-nightly-image")
        return []

    pending_replacements = []
    logging.info(
        f'Found version \033[91m{ver}\033[0m in \033[94m{filename}\033[0m')
    for test in data.get('tests', []):
        pending_replacements.extend(replace(test, ver))

    return pending_replacements

# Processes 'job' data, replacing cron strings if they meet certain conditions.
def process_job(data, filename):

    # Skip if filename starts with "promote-" or "mirror-nightly-image"
    if filename.startswith("promote-") or filename.startswith("mirror-nightly-image"):
        logging.info(
            f"Skipping file {filename} starting with promote- or mirror-nightly-image")
        return []

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

        pending_replacements = []
        logging.info(
            f'Found version {ver} lower than {TARGET_VERSION} in \033[94m{filename}\033[0m')
        for periodic in data.get('periodics', []):
            pending_replacements.extend(
                replace(periodic, ver))  # include filename here

        return pending_replacements
    return []


if __name__ == '__main__':
    FILENAME = sys.argv[1]

    # Define the exact strings to look for in the path
    config_path = '/home/Toma5OD/dev/release/ci-operator/config/openshift'
    jobs_path = '/home/Toma5OD/dev/release/ci-operator/jobs/openshift'

    # Check if the file path contains either of these strings
    if not (config_path in FILENAME or jobs_path in FILENAME):
        print(f"Skipping file: {FILENAME}")
        sys.exit(0)

    with open(FILENAME, 'r', encoding='utf-8') as fp:
        ycontent = fp.read()

    yaml = ruamel.yaml.YAML()
    all_data = list(yaml.load_all(ycontent))
    file_changed = False

    # Check for version 4.13 in the YAML content
    is_version_413 = any('4.13' in data.get('version', '') for data in all_data)
    if not is_version_413:
        print("Skipping file, not version 4.13")
        sys.exit(0)

    changes_made = []
    for data in all_data:
        changes = process_ciops(data, FILENAME) + process_job(data, FILENAME)
        if changes:
            changes_made.extend(changes)
            file_changed = True

    if file_changed:
        logging.info("Changes made!")
        # Apply your changes to all_data here
        with open(FILENAME, 'w', encoding='utf-8') as fp:
            yaml.dump_all(all_data, fp)
