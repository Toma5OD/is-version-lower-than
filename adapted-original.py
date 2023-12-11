import sys
import re
import packaging
import ruamel.yaml
from packaging import version
import random
import logging
from croniter import croniter
from datetime import datetime, timedelta
import random

# THIS FILE REPLACES 4.13 CRONS AND INTERVALS
# Changes more weekly and more frequent than weekly to weekly

TARGET_VERSION = '4.13'

# Set of special cron strings to keep
keep_intervals = {'@yearly', '@annually', '@monthly'}

def is_version_4_13(ver, target_ver):
    # Check if the version is exactly 4.13 and does not include '-priv'.
    if '-priv' in ver:
        return False  # Skip if '-priv' is in the version string

    # Strip 'scos-' prefix if it exists
    if ver.startswith('scos-'):
        ver = ver.replace('scos-', '')

    try:
        ver_v = version.parse(ver)
        target_v = version.parse(target_ver)
        return ver_v == target_v
    except packaging.version.InvalidVersion:
        # Handle the case where version cannot be parsed
        logging.error(f"Invalid version format: {ver}")
        return False

def cron_string():
    return str(random.randint(0, 59)) + ' ' + str(random.randint(0, 23)) + ' ' + "*/" + str(random.randint(13, 14)) + " * *"

def replace(test, ver, file_changed):
    name = test['as'] if 'as' in test else test['name']
    changes_made = []

    if name.startswith("promote-") or name.startswith("mirror-nightly-image"):
        print(f"Found and ignored {name}")
        return file_changed
    if 'interval' in test:
            interval = test['interval'].strip()
            if interval in keep_intervals:
                # Do nothing, keep the interval
                print(f"Keeping interval for {name}: {interval}")
            elif interval.endswith('h') and int(interval[:-1]) >= 24 * 7:
                # Do nothing, keep the interval
                print(f"Keeping bi-weekly or more infrequent interval for {name}: {interval}")
            elif interval.endswith('m') and int(interval[:-1]) >= 24 * 7 * 60:
                # Do nothing, keep the interval
                print(f"Keeping bi-weekly or more infrequent interval for {name}: {interval}")
            else:
                # Replace weekly or more frequent intervals
                print(f"Replacing interval for {name}: {interval}")
                del test['interval']
                if ver == "4.13":
                    new_cron = f"{random.randint(0, 59)} {random.randint(0, 23)} * * {random.choice([6, 0])}"
                    test['cron'] = new_cron
                    changes_made.append(f"Updated cron for {name} to weekly on Saturday or Sunday for 4.13")
                    file_changed = True
                else:
                    # Handle other versions if necessary
                    pass

    if 'cron' in test and ver == "4.13":
        cron_expression = test['cron']
        year, month = 2023, 1  # Assuming the year and month are fixed for the check
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

        cron = croniter(cron_expression, start_date)
        execution_count = 0
        while cron.get_next(datetime) <= end_date:
            execution_count += 1

        if execution_count > 4:  # More frequent than weekly
            new_cron = f"{random.randint(0, 59)} {random.randint(0, 23)} * * {random.choice([6, 0])}"
            test['cron'] = new_cron
            changes_made.append(f"Updated cron for {name} to weekly on Saturday or Sunday for 4.13")
            print(f"Updated cron for {name} to weekly on Saturday or Sunday for 4.13")
            file_changed = True

    return file_changed

def process_ciops(data, filename, target_ver):
    file_changed = False
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

    if not ver or not is_version_4_13(ver, target_ver):
        return []
    
    if ver == TARGET_VERSION:  
        print('Found version', ver, 'equal to', TARGET_VERSION,'in', filename)

    for test in data.get('tests', []):
        file_changed = replace(test, ver, file_changed)
    return file_changed

def process_job(data, filename, target_ver):
    file_changed = False

    for periodic in data.get('periodics', []):
        # Skip jobs based on labels and prefixes
        if 'ci.openshift.io/generator' in periodic.get('labels', {}):
            continue
        if periodic.get('name', '').startswith(('promote-', 'mirror-nightly-image')):
            continue

        version_satisfied = False
        for ref in periodic.get('extra_refs', []):
            base_ref = ref.get('base_ref', '').split('-')
            if len(base_ref) != 2:
                print('unrecognised base_ref', base_ref)
                continue
            ver = base_ref[1]
            if ver and is_version_4_13(ver, target_ver):
                version_satisfied = True
                break

        if 'job-release' in periodic.get('labels', {}):
            ver = periodic.get('labels', {}).get('job-release')
            if ver and is_version_4_13(ver, target_ver):
                version_satisfied = True

        if version_satisfied:
            file_changed = replace(periodic, ver, file_changed)

    return file_changed

if __name__ == '__main__':
    FILENAME = sys.argv[1]
    file_changed = False

    # Define the exact strings to look for in the path
    config_path = '/home/Toma5OD/dev/release/ci-operator/config/openshift'
    jobs_path = '/home/Toma5OD/dev/release/ci-operator/jobs/openshift'

    # Check if the file path contains either of these strings
    if config_path in FILENAME or jobs_path in FILENAME:
        # The file is in one of the desired directories, process it
        pass  # The rest of your script logic goes here
    else:
        print(f"Skipping file: {FILENAME}")
        sys.exit(0)

    with open(FILENAME, 'r', encoding='utf-8') as fp:
        ycontent = fp.read()

    yaml = ruamel.yaml.YAML()
    all_data = list(yaml.load_all(ycontent))

    for data in all_data:
        file_changed_ciops = process_ciops(data, FILENAME, TARGET_VERSION)
        file_changed_job = process_job(data, FILENAME, TARGET_VERSION)
        file_changed = file_changed or file_changed_ciops or file_changed_job

    if file_changed:
        with open(FILENAME, 'w', encoding='utf-8') as fp:
            yaml.dump_all(all_data, fp)