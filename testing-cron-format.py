def validate_and_convert_cron(cron_str):
    # Special cron strings and their 5-param equivalent
    special_crons = {
        "@yearly": "0 0 1 1 *",
        "@annually": "0 0 1 1 *",
        "@monthly": "0 0 1 * *",
        "@weekly": "0 0 * * 0",
        "@daily": "0 0 * * *",
        "@hourly": "0 * * * *"
    }
    
    # Handle special cron strings
    if cron_str in special_crons:
        return special_crons[cron_str], f"Cron category: {cron_str[1:].capitalize()}"
    
    # Assume the cron_str is already in 5-param format
    params = cron_str.split(" ")
    
    # Strict validation
    if len(params) != 5:
        return None, "Invalid cron string: must have exactly 5 components"
    
    # Categorize the cron string
    minute, hour, day_of_month, month, day_of_week = params
    
    if minute != '*' and hour != '*' and day_of_month != '*' and month == '*' and day_of_week == '*':
        category = 'Monthly'
    elif minute != '*' and hour != '*' and day_of_month != '*' and month == '*' and day_of_week == '1-5':
        category = 'Monthly weekdays'
    elif minute != '*' and hour != '*' and day_of_month != '*' and month == '*' and day_of_week == '6-7':
        category = 'Monthly weekends'
    else:
        category = 'Custom'
    
    return " ".join(params), f"Cron category: {category}"

if __name__ == '__main__':
    # Define the file path
    file_path = '/home/Toma5OD/dev/is-version-lower-than/unrecognized_crons.txt'
    
    # Open the file and read line by line
    with open(file_path, 'r') as f:
        for line in f:
            cron_str = line.strip()  # Remove any leading/trailing whitespaces or newline characters
            converted, category = validate_and_convert_cron(cron_str)
            print(f"Original: {cron_str}\nConverted: {converted}\n{category}\n")
