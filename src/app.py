import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys
import argparse
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define paths
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SRC_DIR, '..'))

# Load environment variables - try different possible locations
env_paths = [
    os.path.join(SRC_DIR, '.env'),  # src/.env
    os.path.join(PROJECT_ROOT, '.env'),  # .env in root directory
    '.env'  # current directory
]

for env_path in env_paths:
    if os.path.exists(env_path):
        logger.info(f"Loading environment variables from: {env_path}")
        load_dotenv(env_path)
        break
else:
    logger.warning("No .env file found in expected locations. Looking for environment variables directly.")

# Path configurations
CONFIG_PATHS = {
    'companies': os.path.join(PROJECT_ROOT, 'config', 'companies.csv'),
    'meeting_config': os.path.join(PROJECT_ROOT, 'config', 'meeting_config.csv'),
    'mentors': os.path.join(PROJECT_ROOT, 'config', 'mentors.csv')
}

# Output paths
OUTPUT_PATHS = {
    'descriptions': os.path.join(PROJECT_ROOT, 'output', 'descriptions'),
    'summaries': os.path.join(PROJECT_ROOT, 'output', 'summaries'),
    'backups': os.path.join(PROJECT_ROOT, 'output', 'backups'),
    'schedule': os.path.join(PROJECT_ROOT, 'output', 'meeting_schedule.csv')
}

def load_companies():
    """Load companies data from CSV file"""
    companies_file = CONFIG_PATHS['companies']
    df = pd.read_csv(companies_file)
    
    # Convert DataFrame to dictionary format
    companies = {}
    for _, row in df.iterrows():
        companies[row['company_name']] = {
            'emails': row['founder_emails']
        }
    return companies

def load_meeting_config():
    """Load meeting configuration from CSV file"""
    config_file = CONFIG_PATHS['meeting_config']
    df = pd.read_csv(config_file)
    
    # Extract meeting times from column headers (skip first column which is 'mentor')
    time_slots = []
    for col in df.columns[1:]:
        # Parse the time range (e.g., "09:30-09:45")
        start_time, end_time = col.split('-')
        time_slots.append({
            'start': start_time,
            'end': end_time
        })
    
    logger.info(f"Loaded {len(time_slots)} meeting slots from config")
    return time_slots

def load_mentors(target_date=None):
    """Load mentors data from CSV file, optionally filtering by date"""
    mentors_file = CONFIG_PATHS['mentors']
    df = pd.read_csv(mentors_file)
    
    # Filter mentors by date if specified
    if target_date:
        # First fill NaN values with empty string to avoid filtering errors
        df['dates'] = df['dates'].fillna('')
        df = df[df['dates'].str.contains(target_date)]
    
    # Convert DataFrame to a list of dictionaries
    mentors = []
    mentor_details = {}
    
    for _, row in df.iterrows():
        mentor_name = row['name']
        mentors.append(mentor_name)
        
        mentor_details[mentor_name] = {
            'role': row['role'],
            'company': row['company'],
            'bio': row['bio']
        }
    
    logger.info(f"Loaded {len(mentors)} mentors for date {target_date}")
    return mentors, mentor_details

def refresh_mentors(target_date=None):
    """Call refresh_mentors.py to update mentors.csv from Airtable
    
    Args:
        target_date (str, optional): If specified, only include mentors for this date
    """
    logger.info(f"Refreshing mentors data from Airtable{' for date: ' + target_date if target_date else ''}...")
    try:
        refresh_script = os.path.join(PROJECT_ROOT, 'config', 'refresh_mentors.py')
        cmd = ['python', refresh_script]
        
        if target_date:
            cmd.extend(['--date', target_date])
            
        result = subprocess.run(cmd, 
                               capture_output=True, 
                               text=True, 
                               check=True)
        logger.info("Mentors data refreshed successfully")
        logger.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error refreshing mentors data: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def get_target_date_and_options():
    """Get the target date and options from command line arguments or user input"""
    parser = argparse.ArgumentParser(description='Generate mentor meeting schedule')
    parser.add_argument('--date', type=str, help='Target date in YYYY-MM-DD format')
    parser.add_argument('--cache', action='store_true', help='Use cached mentor data instead of refreshing from Airtable')
    args = parser.parse_args()
    
    # If date is specified via command line, validate and use it
    if args.date:
        try:
            # Validate date format
            datetime.strptime(args.date, '%Y-%m-%d')
            selected_date = args.date
            
            # By default, refresh mentors unless --cache is specified
            if not args.cache:
                refresh_mentors(selected_date)
                
            return selected_date
        except ValueError:
            logger.error(f"Invalid date format: {args.date}. Please use YYYY-MM-DD format.")
            # Continue to interactive date selection
    
    # Always refresh first to get available dates, unless --cache is specified
    if not args.cache:
        logger.info("Refreshing mentor data from Airtable (use --cache to skip)")
        refresh_mentors()  # Full refresh to get all available dates
    
    # Get available dates from mentors.csv
    try:
        mentors_df = pd.read_csv(CONFIG_PATHS['mentors'])
        available_dates = set()
        
        for dates_str in mentors_df['dates'].dropna():
            dates = dates_str.split(',')
            available_dates.update(dates)
        
        # Sort dates for display
        available_dates = sorted(list(available_dates))
        
        if not available_dates:
            logger.warning("No available dates found in mentors data. Refreshing data from Airtable...")
            refresh_mentors()  # Full refresh to get all available dates
            
            # Try again after refresh
            mentors_df = pd.read_csv(CONFIG_PATHS['mentors'])
            available_dates = set()
            
            for dates_str in mentors_df['dates'].dropna():
                dates = dates_str.split(',')
                available_dates.update(dates)
                
            available_dates = sorted(list(available_dates))
            
            if not available_dates:
                logger.warning("Still no available dates after refresh. Please enter date manually.")
                return input("Enter target date (YYYY-MM-DD): ").strip()
        
        # Display available dates to user
        print("\nAvailable dates from Airtable:")
        for i, date in enumerate(available_dates):
            print(f"{i+1}. {date}")
        
        # Let user select a date
        selected_date = None
        while not selected_date:
            try:
                selection = input("\nSelect a date by entering its number: ")
                index = int(selection) - 1
                
                if 0 <= index < len(available_dates):
                    selected_date = available_dates[index]
                    logger.info(f"Selected date: {selected_date}")
                else:
                    print(f"Please enter a number between 1 and {len(available_dates)}")
            except ValueError:
                print("Please enter a valid number")
        
        # By default, refresh data for the selected date unless --cache is specified
        if not args.cache:
            refresh_mentors(selected_date)
        else:
            logger.info("Using cached mentor data (--cache flag used)")
        
        return selected_date
    
    except Exception as e:
        logger.error(f"Error reading available dates: {str(e)}")
        
        # If we can't read dates for some reason, ask if user wants to refresh
        if not args.cache and input("Would you like to refresh mentors data from Airtable? (y/n): ").lower().startswith('y'):
            refresh_mentors()  # Full refresh since we don't have a date yet
            
        # Fall back to manual entry
        date_input = input("Enter target date (YYYY-MM-DD): ").strip()
        
        # Ask if user wants to refresh for this specific date
        if not args.cache:
            refresh_mentors(date_input)
        
        return date_input

def convert_name_to_url_format(name):
    """Convert a mentor name to URL format with lowercase and dashes instead of spaces"""
    # Remove any special characters and replace spaces with dashes
    url_name = name.lower().strip()
    # Replace multiple spaces with a single dash
    url_name = '-'.join([part for part in url_name.split() if part])
    return url_name

def create_schedule(mentors, mentor_details, companies, target_date, time_slots):
    """Create a schedule of meetings between companies and mentors"""
    schedule = []
    
    # Convert companies dict to list for ordered iteration
    company_list = list(companies.keys())
    num_companies = len(company_list)
    num_mentors = len(mentors)
    
    logger.info(f"Initial counts: {num_mentors} mentors, {num_companies} companies")
    
    # Balance the lists by adding BREAK placeholders to the shorter list
    if num_mentors < num_companies:
        breaks_needed = num_companies - num_mentors
        logger.info(f"Adding {breaks_needed} BREAK placeholders to mentors list")
        
        # Add BREAK placeholders to mentors to match the number of companies
        mentors = mentors.copy()  # Create a copy to avoid modifying the original list
        mentors.extend(["BREAK"] * breaks_needed)
        
        logger.info(f"Balanced: {len(mentors)} total slots (mentors + breaks), {num_companies} companies")
    elif num_companies < num_mentors:
        breaks_needed = num_mentors - num_companies
        logger.info(f"Adding {breaks_needed} BREAK placeholders to companies list")
        
        # Add BREAK placeholders to companies to match the number of mentors
        company_list = company_list.copy()  # Create a copy to avoid modifying the original list
        company_list.extend(["BREAK"] * breaks_needed)
        
        logger.info(f"Balanced: {num_mentors} mentors, {len(company_list)} total slots (companies + breaks)")
    else:
        logger.info(f"Already balanced: {num_mentors} mentors, {num_companies} companies")
    
    # Update counts after balancing
    num_companies = len(company_list)
    num_mentors = len(mentors)
    
    # Verify the lists are balanced
    if num_mentors != num_companies:
        logger.warning(f"Lists not properly balanced! Mentors: {num_mentors}, Companies: {num_companies}")
    else:
        logger.info(f"Successfully balanced both lists to {num_mentors} slots each")
    
    # Convert time slots to include date
    date_time_slots = []
    for slot in time_slots:
        start_datetime = datetime.strptime(f"{target_date} {slot['start']}", '%Y-%m-%d %H:%M')
        end_datetime = datetime.strptime(f"{target_date} {slot['end']}", '%Y-%m-%d %H:%M')
        date_time_slots.append({
            'start': start_datetime.isoformat(),
            'end': end_datetime.isoformat()
        })
    
    logger.info(f"Scheduling for date {target_date}: {len(mentors)} mentors, {num_companies} companies, {len(date_time_slots)} time slots")
    
    # For each time slot
    for slot_index, slot in enumerate(date_time_slots):
        logger.info(f"Scheduling slot {slot_index+1}: {slot['start']} - {slot['end']}")
        
        # For each mentor in this slot
        for mentor_index, mentor in enumerate(mentors):
            # Skip if this is a BREAK
            if mentor == "BREAK":
                continue
                
            # Get company in round-robin fashion
            company_index = (slot_index + mentor_index) % num_companies
            company = company_list[company_index]
            
            # Skip if this is a BREAK
            if company == "BREAK":
                continue
            
            # Create formatted description with mentor details
            details = mentor_details[mentor]
            description = f"{mentor}, {details['role']}, {details['company']}: {details['bio']}"
            
            # Get the attendees (founder emails) for this company
            attendees = companies[company]["emails"]
            
            # Generate mentor URL for location field
            mentor_url_name = convert_name_to_url_format(mentor)
            location_url = f"https://techstars-ldn-mentor-lookbook.lovable.app/mentor/{mentor_url_name}"
            
            # Create the meeting entry
            meeting = {
                'summary': f"{mentor} <> {company}",
                'start_time': slot['start'],
                'end_time': slot['end'],
                'company': company,
                'mentor': mentor,
                'description': description,
                'attendees': attendees,
                'location': location_url,
                'date': target_date
            }
            
            schedule.append(meeting)
    
    # Add debug information about total meetings created
    logger.info(f"Created a total of {len(schedule)} meetings")
    
    return schedule

def main():
    try:
        # Get target date from command line or user input, with refresh option
        target_date = get_target_date_and_options()
        logger.info(f"Scheduling meetings for date: {target_date}")
        
        # Load configuration
        companies = load_companies()
        time_slots = load_meeting_config()
        mentors, mentor_details = load_mentors(target_date)
        
        # Create schedule
        schedule = create_schedule(mentors, mentor_details, companies, target_date, time_slots)
        
        # Convert to DataFrame and save to CSV
        df = pd.DataFrame(schedule)
        output_file = OUTPUT_PATHS['schedule']
        
        # Check if file exists and remove it first to ensure clean write
        if os.path.exists(output_file):
            logger.info(f"Removing existing file: {output_file}")
            os.remove(output_file)
        
        # Write to CSV with mode='w' to ensure overwriting
        df.to_csv(output_file, index=False, mode='w')
        logger.info(f"Schedule has been exported to {output_file}")
        
        # Create backups directory if it doesn't exist
        backup_dir = OUTPUT_PATHS['backups']
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            logger.info(f"Created backup directory: {backup_dir}")
        
        # Save timestamped backup in backups directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'meeting_schedule_{timestamp}.csv')
        df.to_csv(backup_file, index=False)
        logger.info(f"Backup schedule saved to {backup_file}")
        
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main() 