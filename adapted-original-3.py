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

# THIS FILE REPLACES 4.12 AND LOWER CRONS AND INTERVALS
# Changes more frequent than bi-weekly to bi-weekly
# SKIPS OPENSHIFT ORGANIZATION FILES

TARGET_VERSION = '4.12'  # Update to target versions equal to or lower than 4.11

# Set of special cron strings to keep
keep_intervals = {'@yearly', '@annually', '@monthly'}

def is_version_equal_or_lower_than_target(ver, target_ver):
    # Skip if '-priv' is in the version string
    if '-priv' in ver:
        return False

    # Strip 'scos-' prefix if it exists
    if ver.startswith('scos-'):
        ver = ver.replace('scos-', '')

    # Exclude version 4.13
    try:
        ver_v = version.parse(ver)
        target_v = version.parse(target_ver)
        version_4_13 = version.parse("4.13")
        return ver_v <= target_v and ver_v < version_4_13
    except packaging.version.InvalidVersion:
        logging.error(f"Invalid version format: {ver}")
        return False

def replace(test, ver):
    name = test['as'] if 'as' in test else test['name']
    changes_made = False

    # Check if the version is 4.11 or lower
    if not is_version_equal_or_lower_than_target(ver, TARGET_VERSION):
        return test, False

    # Proceed with existing logic for intervals and crons
    if name.startswith("promote-") or name.startswith("mirror-nightly-image"):
        print(f"Found and ignored {name}")
        return test, False

    if 'interval' in test:
        interval = test['interval'].strip()
        if interval in keep_intervals:
            print(f"Keeping interval for {name}: {interval}")
        elif interval.endswith('h') and int(interval[:-1]) >= 24 * 14:
            print(f"Keeping bi-weekly or more infrequent interval for {name}: {interval}")
        elif interval.endswith('m') and int(interval[:-1]) >= 24 * 14 * 60:
            print(f"Keeping bi-weekly or more infrequent interval for {name}: {interval}")
        else:
            print(f"Replacing interval for {name}: {interval}")
            del test['interval']
            day1 = random.randint(5, 10)
            day2 = random.randint(max(15, day1 + 14), 25)
            minute = random.randint(0, 59)
            hour = random.randint(1, 10)
            new_cron = f"{minute} {hour} {day1},{day2} * *"
            test['cron'] = new_cron
            print(f"Replaced interval with cron for {name}")
            changes_made = True

    if 'cron' in test:
        cron_expression = test['cron']
        year, month = 2023, 1
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        cron = croniter(cron_expression, start_date)
        execution_count = 0
        while cron.get_next(datetime) <= end_date:
            execution_count += 1
        if execution_count > 2:
            print(f"Replacing cron for {name}: {cron_expression}")
            day1 = random.randint(5, 10)
            day2 = random.randint(max(15, day1 + 14), 25)
            minute = random.randint(0, 59)
            hour = random.randint(1, 10)
            new_cron = f"{minute} {hour} {day1},{day2} * *"
            test['cron'] = new_cron
            print(f"Replaced cron with new bi-weekly schedule for {name}")
            changes_made = True

    return test, changes_made

def process_ciops(data, filename, target_ver):
    file_changed = False
    section_latest = data.get('releases', {}).get('latest', {})
    
    if not section_latest:
        return False

    release_ref = list(section_latest.keys())[0]
    ver = None

    if 'version' in section_latest[release_ref]:
        ver = section_latest[release_ref].get('version')
    elif 'name' in section_latest[release_ref]:
        ver = section_latest[release_ref].get('name')
    elif 'version_bounds' in section_latest[release_ref]:
        ver = section_latest[release_ref].get('version_bounds', {}).get('upper')

    if ver and is_version_equal_or_lower_than_target(ver, target_ver):
        print(f'Processing version {ver} that matches our target of {target_ver} and lower in {filename}')
        for i, test in enumerate(data.get('tests', [])):
            modified_test, changed = replace(test, ver)
            if changed:
                data['tests'][i] = modified_test  # Update the test in data
                file_changed = True

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
            if ver and is_version_equal_or_lower_than_target(ver, target_ver):
                version_satisfied = True
                break

        if 'job-release' in periodic.get('labels', {}):
            ver = periodic.get('labels', {}).get('job-release')
            if ver and is_version_equal_or_lower_than_target(ver, target_ver):
                version_satisfied = True

        if version_satisfied:
            file_changed = replace(periodic, ver)

    return file_changed

if __name__ == '__main__':
    FILENAME = sys.argv[1]
    file_changed = False

    # Define paths to exclude
    exclude_paths = [
        '/home/Toma5OD/dev/release/ci-operator/config/openshift/',
        '/home/Toma5OD/dev/release/ci-operator/jobs/openshift/'
    ]

    # Exclude specific openshift organization paths
    if any(exclude_path in FILENAME for exclude_path in exclude_paths):
        print(f"Skipping file from openshift organization: {FILENAME}")
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