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

# Load environment variables
load_dotenv()

# Path configurations
CONFIG_PATHS = {
    'companies': 'config/companies.csv',
    'meeting_config': 'config/meeting_config.csv',
    'mentors': 'config/mentors.csv'
}

# Output paths
OUTPUT_PATHS = {
    'descriptions': 'output/descriptions',
    'summaries': 'output/summaries',
    'backups': 'output/backups',
    'schedule': 'output/meeting_schedule.csv'
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

def refresh_mentors():
    """Call refresh_mentors.py to update mentors.csv from Airtable"""
    logger.info("Refreshing mentors data from Airtable...")
    try:
        refresh_script = os.path.join('config', 'refresh_mentors.py')
        result = subprocess.run(['python', refresh_script], 
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
    parser.add_argument('--refresh', action='store_true', help='Refresh mentors data from Airtable')
    args = parser.parse_args()
    
    # Handle refresh option
    if args.refresh:
        success = refresh_mentors()
        if not success:
            logger.warning("Continuing with existing mentor data...")
    
    # Handle date
    if args.date:
        return args.date
    
    while True:
        date_str = input("Enter target date (YYYY-MM-DD): ").strip()
        try:
            # Validate date format
            datetime.strptime(date_str, '%Y-%m-%d')
            
            # Ask about refreshing mentors if not specified in command line
            if not args.refresh and input("Refresh mentors data from Airtable? (y/n): ").lower().startswith('y'):
                refresh_mentors()
                
            return date_str
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD format.")

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
    
    # Balance the lists by adding BREAK placeholders to the shorter list
    if num_mentors < num_companies:
        logger.info(f"Adding {num_companies - num_mentors} BREAK placeholders to mentors list")
        mentors.extend(["BREAK"] * (num_companies - num_mentors))
    elif num_companies < num_mentors:
        logger.info(f"Adding {num_mentors - num_companies} BREAK placeholders to companies list")
        company_list.extend(["BREAK"] * (num_mentors - num_companies))
    
    # Update counts after balancing
    num_companies = len(company_list)
    num_mentors = len(mentors)
    logger.info(f"Balanced counts: {num_mentors} total slots (mentors + breaks), {num_companies} total slots (companies + breaks)")
    
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