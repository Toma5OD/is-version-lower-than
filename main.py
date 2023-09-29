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
    # logging.info("We entered cron_string")
    if ver == "4.13":
        # Weekly (Saturday or Sunday)
        return f"{random.randint(0, 59)} {random.randint(0, 23)} * * {random.choice([6, 7])}"
    # COMMENTED OUT LINE AS 4.12 will be ignored.
    # elif ver == "4.12":
    #     # Bi-weekly (existing, so no change)
    #     return f"{random.randint(0, 59)} {random.randint(0, 23)} */14 * *"
    else:
        # Older than 4.12, bi-weekly at random time between 1:00 and 10:00
        # First occurrence between 5th and 10th day, second between 15th and 25th day
        cron_string = lambda: f"{random.randint(1, 59)} {random.randint(1, 10)} {random.choice([5, 6, 7, 8, 9, 10])},{random.randint(15, 25)} * *"
        return cron_string()

def process_interval(test, ver):
    # logging.info("We entered process_interval")
    changes_made = []
    # Get the name of the test from 'as' or 'name' fields
    name = test['as'] if 'as' in test else test['name']
    
    # If these conditions are met, log and return an empty list
    if ver == "4.12" or name.startswith("promote-") or name.startswith("mirror-nightly-image"):
        if ver == "4.12":
            logging.info(f"Found and ignored 4.12 {name}")
        if name.startswith("promote-"):
            logging.info(f"Found and ignored promote test {name}")
        if name.startswith("mirror-nightly-image"):
            logging.info(f"Found and ignored mirror-nightly-image test {name}")
        return []

    logging.info(f'Found test in {name} with interval {test["interval"]}')

    if 'interval' in test:
        interval = test['interval'].strip()
        
        if 'cron' in test:
            del test['interval']
            changes_made.append(f"Removed interval for {name}")
        elif 'cron' not in test:
            del test['interval']
            test['cron'] = cron_string(ver)
            changes_made.append(f"Replaced interval with cron for {name}")

    return changes_made

def process_cron(test, ver):
    # logging.info("We entered process_cron")
    changes_made = []
    name = test['as'] if 'as' in test else test['name']
    logging.info(f'Found test in \033[94m{name}\033[0m with cron \033[92m{test["cron"]}\033[0m')

    if ver == "4.12" or name.startswith("promote-") or name.startswith("mirror-nightly-image"):
        if ver == "4.12":
            logging.info(f"Found and ignored 4.12 {name}")
        if name.startswith("promote-"):
            logging.info(f"Found and ignored promote test {name}")
        if name.startswith("mirror-nightly-image"):
            logging.info(f"Found and ignored mirror-nightly-image test {name}")
        return []
    
    # Update the cron based on the version_number
    test["cron"] = cron_string(ver)  # Assuming cron_string() can accept a version number
    changes_made.append(f"Updated cron for {name} based on version {ver}")

    return changes_made

def process_promote(test):
    # logging.info("We entered process_promote")
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

    # logging.info(f"We entered replace for file: {filename}")

    # Skip if version is 4.12
    if ver == "4.12":
        return changes_made

    name = test['as'] if 'as' in test else test['name']
    
    if name.startswith('promote-'):
        changes_made.extend(process_promote(test))
    elif 'interval' in test:
        changes_made.extend(process_interval(test, ver))
    elif 'cron' in test:
        changes_made.extend(process_cron(test, ver))
        
    return changes_made

def process_ciops(data, filename):
    # logging.info("We entered process_ciops")
    # logging.info(f"Number of tests in {filename}: {len(data.get('tests', []))}")
    section_latest = data.get('releases', {}).get('latest', {})
    if not section_latest:
        return []
    
    release_ref = list(section_latest.keys())[0]

    if 'version' in section_latest[release_ref]:
        ver = section_latest[release_ref].get('version')
    elif 'name' in section_latest[release_ref]:
        ver = section_latest[release_ref].get('name')
    elif 'version_bounds' in section_latest[release_ref]:
        ver = section_latest[release_ref].get('version_bounds', {}).get('upper')

    # Skip if version is 4.12
    if ver == "4.12":
        logging.info(f"Skipping file {filename} with version 4.12")
        return []

    # Skip if filename starts with "promote-" or "mirror-nightly-image"
    if filename.startswith("promote-") or filename.startswith("mirror-nightly-image"):
        logging.info(f"Skipping file {filename} starting with promote- or mirror-nightly-image")
        return []
    
    if not ver or not version_lower_than_or_equal(ver, TARGET_VERSION):
        return []

    pending_replacements = []
    logging.info(f'Found version \033[91m{ver}\033[0m in \033[94m{filename}\033[0m')
    for test in data.get('tests', []):
        # logging.info(f"Processing test: {test.get('name', 'Unknown')} in file: {filename}")
        pending_replacements.extend(replace(test, ver, filename)) 


    # print(f"Returning from process_ciops: {pending_replacements}, type: {type(pending_replacements)}")
    return pending_replacements

# Processes 'job' data, replacing cron strings if they meet certain conditions.
def process_job(data, filename):
    # logging.info("We entered process_job")
    # logging.info(f"Number of tests in {filename}: {len(data.get('periodics', []))}")

    # Skip if filename starts with "promote-" or "mirror-nightly-image"
    if filename.startswith("promote-") or filename.startswith("mirror-nightly-image"):
        logging.info(f"Skipping file {filename} starting with promote- or mirror-nightly-image")
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
            
            # Skip if version is 4.12
            if ver == "4.12":
                logging.info(f"Skipping due to version 4.12")
                continue

            if ver and version_lower_than_or_equal(ver, TARGET_VERSION):
                version_satisfied = True
                break

        if 'job-release' in periodic.get('labels', {}):
            ver = periodic.get('labels', {}).get('job-release')
            if ver and version_lower_than_or_equal(ver, TARGET_VERSION):
                version_satisfied = True

        if not version_satisfied:
            return []

        pending_replacements = []
        logging.info(f'Found version {ver} lower than {TARGET_VERSION} in \033[94m{filename}\033[0m')
        for periodic in data.get('periodics', []):
            # logging.info(f"Processing test: {periodic.get('name', 'Unknown')} in file: {filename}")
            pending_replacements.extend(replace(periodic, filename, ver))  # include filename here


        # print(f"Returning from process_job: {pending_replacements}, type: {type(pending_replacements)}")
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
        # Apply your changes to all_data here
        with open(FILENAME, 'w', encoding='utf-8') as fp:
            yaml.dump_all(all_data, fp)
