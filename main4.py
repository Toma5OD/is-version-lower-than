import sys
import ruamel.yaml
from packaging import version
import random
import logging
from croniter import croniter
from datetime import datetime
from calendar import monthrange

# This is the non verbose logging view
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Check for yaml files that are equal to or lower than the target version.
TARGET_VERSION = "4.13"

def version_lower_than_or_equal(ver, target_ver):
    return ver == target_ver


# Set of special cron strings to keep
keep_intervals = {'@yearly', '@annually', '@monthly'}


def cron_string(ver):
    # logging.info("We entered cron_string")
    if ver == "4.13":
        # Weekly (Saturday or Sunday)
        return f"{random.randint(0, 59)} {random.randint(0, 23)} * * {random.choice([6, 0])}"


def process_interval(test, ver):
    changes_made = []
    name = test['as'] if 'as' in test else test['name']
    if name.startswith("promote-") or name.startswith("mirror-nightly-image"):
        logging.info(f"Found and ignored {name}")
        return []

    logging.info(f'Found test in {name} with interval {test["interval"]}')

    if 'interval' in test:
        interval = test['interval'].strip()

        if interval in keep_intervals:
            # Do nothing, keep the interval
            pass
        elif interval.endswith('h') and int(interval[:-1]) > 24 * 7:
            pass  # Keep it if it's weekly or more
        elif interval.endswith('m') and int(interval[:-1]) > 24 * 7 * 60:
            pass  # Keep it if it's weekly or more
        else:
            if 'cron' in test:
                del test['interval']
                changes_made.append(f"Removed interval for {name}")
            else:
                del test['interval']
                test['cron'] = cron_string(ver)
                changes_made.append(f"Replaced interval with cron for {name}")

    return changes_made

def process_cron(test, ver):
    changes_made = []
    name = test['as'] if 'as' in test else test['name']

    if name.startswith("promote-") or name.startswith("mirror-nightly-image"):
        logging.info(f"Found and ignored {name}")
        return []

    logging.info(f'Found test in {name} with cron {test["cron"]}')

    cron_expression = test['cron']
    if cron_expression not in keep_intervals:
        # February as a reference
        year, month = 2023, 2
        start_date = datetime(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = datetime(year, month, last_day)

        cron = croniter(cron_expression, start_date)
        execution_count = 0
        while cron.get_next(datetime) <= end_date:
            execution_count += 1

        # If execution_count > 4, it means it's more frequent than weekly
        if execution_count > 4:
            new_cron = cron_string(ver)
            test['cron'] = new_cron
            changes_made.append(f"Updated cron for {name} to {new_cron}")

    return changes_made

def process_promote(test):
    changes_made = []
    name = test['as'] if 'as' in test else test['name']
    logging.info(f'Found promote test {name}')

    # Your specific logic for 'promote-' tests can go here
    # For example, let's say you want to add a 'promote' key to the test dict
    test['promote'] = True
    changes_made.append("promoted")

    return changes_made


def replace(test, ver, filename):
    changes_made = []

    name = test['as'] if 'as' in test else test['name']

    if name.startswith('promote-'):
        changes_made.extend(process_promote(test))
    elif 'interval' in test:
        changes_made.extend(process_interval(test, ver))
    elif 'cron' in test:
        changes_made.extend(process_cron(test, ver))

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

    if not ver or not version_lower_than_or_equal(ver, TARGET_VERSION):
        return []

    pending_replacements = []
    logging.info(
        f'Found version \033[91m{ver}\033[0m in \033[94m{filename}\033[0m')
    for test in data.get('tests', []):
        pending_replacements.extend(replace(test, ver, filename))

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

            if ver and version_lower_than_or_equal(ver, TARGET_VERSION):
                version_satisfied = True
                break

        if 'job-release' in periodic.get('labels', {}):
            ver = periodic.get('labels', {}).get('job-release')
            if ver and version_lower_than_or_equal(ver, TARGET_VERSION):
                version_satisfied = True

        if not version_satisfied:
            return [False]

        pending_replacements = []
        logging.info(
            f'Found version {ver} lower than {TARGET_VERSION} in \033[94m{filename}\033[0m')
        for periodic in data.get('periodics', []):
            pending_replacements.extend(
                replace(periodic, ver, filename))  # include filename here

        return pending_replacements
    return []


if __name__ == '__main__':
    FILENAME = sys.argv[1]

    with open(FILENAME, 'r', encoding='utf-8') as fp:
        ycontent = fp.read()

    yaml = ruamel.yaml.YAML()
    pending = []
    all_data = list(yaml.load_all(ycontent))
    file_changed = False

    changes_made = []
    for data in all_data:
        changes1 = process_ciops(data, FILENAME)
        changes2 = process_job(data, FILENAME)
        if changes1 or changes2:
            changes_made.extend(changes1)
            changes_made.extend(changes2)
            file_changed = True

    if file_changed:
        logging.info("Changes made!")
        # Apply your changes to all_data here
        with open(FILENAME, 'w', encoding='utf-8') as fp:
            yaml.dump_all(all_data, fp)
