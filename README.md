# Python Scripts for Cron/Interval Updates in OpenShift/Release Repo

## Overview
This folder contains Python scripts designed to modify cron/interval values in the OpenShift/Release repository. The scripts target different versions and organizations within the repository.

### Key Scripts
- `adapted-original.py`: Alters schedules for version 4.13.
- `adapted-original-2.py`: Alters schedules for OpenShift org versions 4.11 and lower.
- `adapted-original-3.py`: Alters schedules for non-OpenShift org versions 4.12 and lower.

## Changes Summary

### 4.13 Changes
- Changes are applied to versions equal to 4.13.
- Cron schedules more frequent than weekly are changed to weekly.
- Weekly schedules are randomly set to either Saturday or Sunday.
- The time for each schedule is randomized.

### 4.12 and Lower (Non-OpenShift Org)
- Applies to versions lower than or equal to 4.12, excluding OpenShift org.
- Schedules more frequent than bi-weekly are changed to bi-weekly.
- Bi-weekly schedules are set on two randomly selected days in a month.
- The time for each schedule is randomized.

### 4.11 and Lower (OpenShift Org)
- Applies to OpenShift org versions 4.11 and lower.
- Follows similar logic to non-OpenShift org 4.12 and lower changes.

## PR References
- Changes for 4.13: [PR #46628](https://github.com/openshift/release/pull/46628)
- Changes for 4.12 and lower: [PR #46628](https://github.com/openshift/release/pull/46628)

## Usage
- Set the `TARGET_VERSION` in the script as required.
- Run the script providing YAML file paths as arguments.

### Example Command
```bash
find your_file_location/ci-operator/config/ your_file_location/ci-operator/jobs/ -name "*.yaml" -exec python your_script_location/main.py {} \;
```

## Post-Script Steps
- Use `make update` command to ensure no changes from double to single quotes in YAML files.

## Notes
- The scripts log changes to YAML files for transparency.
- Discuss any issues or uncertainties in a 1-1 setting for clarity.

