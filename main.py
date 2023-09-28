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

# Check for yaml files that are equal to or lower than the target version.
TARGET_VERSION = "4.13"

def version_lower_than_or_equal(ver, target):
    ver_v = version.parse(ver)
    if ver.find("priv") != -1:
        v = ver.split("-")
        ver_v = version.parse(v[0])
    target_v = version.parse(target)
    return (ver_v < target_v or ver_v == target_v)


def cron_string(ver):
    return str(random.randint(0, 59)) + ' ' + str(random.randint(0, 23)) + ' ' + "*/" + str(random.randint(13, 14)) + " * *"

# Modify fix_cron_and_interval to accept filename
def fix_cron_and_interval(test, filename):
    if 'cron' in test and 'interval' in test:
        # Add the filename to a .txt file
        with open("files-with-cronAndInterval.txt", "a") as f:
            f.write(f"{filename}\n")
        del test['interval']  # Delete the 'interval' field
        return True  # Return True if changes are made
    return False  # Return False otherwise

def process_interval(test, ver):
    changes_made = []
    # Get the name of the test from 'as' or 'name' fields
    name = test['as'] if 'as' in test else test['name']
    logging.info(f'found test {name} with interval \033[92m{test["interval"]}\033[0m')

    if name.startswith('promote-'):
        logging.info(f'found promote test {name}')
        return []
        
    interval = test['interval'].strip()
    
    # Remove the interval if both cron and interval exist
    if 'cron' in test:
        del test['interval']
        changes_made.append(f"Removed interval for {name}")
    
    # Replace the interval with a cron value based on the version number if only interval exists
    elif 'cron' not in test:
        del test['interval']
        test['cron'] = cron_string(ver)  # Assuming cron_string() can accept a version number
        changes_made.append(f"Replaced interval with cron for {name}")

    return changes_made

def process_cron(test, ver):
    changes_made = []
    name = test['as'] if 'as' in test else test['name']
    logging.info(f'found test {name} with cron \033[92m{test["cron"]}\033[0m')
    
    # Update the cron based on the version_number
    test["cron"] = cron_string(ver)  # Assuming cron_string() can accept a version number
    changes_made.append(f"Updated cron for {name} based on version {ver}")

    return changes_made

def process_promote(test):
    changes_made = []
    name = test['as'] if 'as' in test else test['name']
    logging.info(f'found promote test {name}')
    
    # Your specific logic for 'promote-' tests can go here
    # For example, let's say you want to add a 'promote' key to the test dict
    test['promote'] = True
    changes_made.append("promoted")

    return changes_made

def replace(test, filename, ver):
    changes_made = []

    if fix_cron_and_interval(test, filename):
        changes_made.append("fixed_cron_and_interval")

    name = test['as'] if 'as' in test else test['name']
    
    if name.startswith('promote-'):
        changes_made.extend(process_promote(test))
    elif 'interval' in test:
        changes_made.extend(process_interval(test, ver))
    elif 'cron' in test:
        changes_made.extend(process_cron(test, ver))
        
    # TODO: Edit this section later for other responsibilities
    
    return changes_made


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
    logging.info(f'Found version \033[91m{ver}\033[0m in \033[94m{filename}\033[0m')
    for test in data.get('tests', []):
        pending_replacements.extend(replace(test, filename, ver))

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

        pending_replacements = []
        logging.info(f'Found version {ver} lower than {TARGET_VERSION} in \033[94m{filename}\033[0m')
        pending_replacements.extend(replace(periodic, filename, ver))

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