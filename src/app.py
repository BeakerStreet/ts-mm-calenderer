import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Timing parameters
MEETING_DURATION = 15 
FIRST_MTG_START = '09:30' # often after a briefing of some kind
LAST_MTG_END = '13:40' # when does the last mtg end?
LUNCH = False # are you doing lunch?
LUNCH_START = '12:15' # lunch start time (if lunch)
LUNCH_END = '12:15' # lunch end time (if lunch)

# Meeting slots configuration
MEETING_SLOTS = {
    'morning': {
        'start_time': FIRST_MTG_START,
        'end_time': LUNCH_START if LUNCH else LAST_MTG_END,
        'break_duration': 10,  # minutes between meetings
    },
    'afternoon': {
        'start_time': LUNCH_END if LUNCH else LAST_MTG_END,
        'end_time': LAST_MTG_END,
        'break_duration': 5,  # minutes between meetings
    }
}

def load_companies():
    """Load companies data from CSV file"""
    companies_file = os.path.join('config', 'companies.csv')
    df = pd.read_csv(companies_file)
    
    # Convert DataFrame to dictionary format
    companies = {}
    for _, row in df.iterrows():
        companies[row['company_name']] = {
            'emails': row['founder_emails']
        }
    return companies

# Load companies from CSV
COMPANIES = load_companies()

# Airtable setup
AIRTABLE_TOKEN = os.getenv('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_ID = 'tbllbtrlfcmReNxQR'

logger.info(f"Using Base ID: {AIRTABLE_BASE_ID}")
logger.info(f"Using Table ID: {AIRTABLE_TABLE_ID}")
logger.info(f"Using Token: {AIRTABLE_TOKEN[:10]}...")  # Only show first 10 chars for security

# Airtable API configuration
AIRTABLE_API_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_ID}"
AIRTABLE_HEADERS = {
    'Authorization': f'Bearer {AIRTABLE_TOKEN}',
    'Content-Type': 'application/json'
}

# Output paths
OUTPUT_PATHS = {
    'descriptions': 'output/descriptions',
    'summaries': 'output/summaries',
    'backups': 'output/backups',
    'schedule': 'output/meeting_schedule.csv'
}

def get_target_date():
    """Get the target date from command line arguments or user input"""
    parser = argparse.ArgumentParser(description='Generate mentor meeting schedule')
    parser.add_argument('--date', type=str, help='Target date in YYYY-MM-DD format')
    args = parser.parse_args()
    
    if args.date:
        return args.date
    
    while True:
        date_str = input("Enter target date (YYYY-MM-DD): ").strip()
        try:
            # Validate date format
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD format.")

def get_airtable_records():
    """Fetch all records from Airtable"""
    response = requests.get(AIRTABLE_API_URL, headers=AIRTABLE_HEADERS)
    response.raise_for_status()
    return response.json()['records']

def generate_time_slots(date_str, num_slots):
    """
    Generate time slots for meetings based on configuration
    """
    slots = []
    date = datetime.strptime(date_str, '%Y-%m-%d')
    
    # Process each time period (morning/afternoon)
    for period, config in MEETING_SLOTS.items():
        current_time = datetime.strptime(f"{date_str} {config['start_time']}", '%Y-%m-%d %H:%M')
        end_time = datetime.strptime(f"{date_str} {config['end_time']}", '%Y-%m-%d %H:%M')
        
        while current_time < end_time:
            start_time = current_time
            end_time = start_time + timedelta(minutes=MEETING_DURATION)
            
            # Only add slot if it doesn't exceed the period end time
            if end_time <= datetime.strptime(f"{date_str} {config['end_time']}", '%Y-%m-%d %H:%M'):
                slots.append({
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                })
            
            # Add break between meetings
            current_time = end_time + timedelta(minutes=config['break_duration'])
    
    logger.info(f"Generated {len(slots)} meeting slots for {date_str}")
    return slots

def convert_name_to_url_format(name):
    """Convert a mentor name to URL format with lowercase and dashes instead of spaces"""
    # Remove any special characters and replace spaces with dashes
    url_name = name.lower().strip()
    # Replace multiple spaces with a single dash
    url_name = '-'.join([part for part in url_name.split() if part])
    return url_name

def create_schedule(records, companies, target_date):
    """Create a schedule of meetings between companies and mentors"""
    schedule = []
    
    # Group records by date and store full record info
    date_groups = {}
    mentor_details = {}  # Store mentor details for descriptions
    
    # Log all dates found in records
    logger.info("\n=== Available Dates in Records ===")
    all_dates = set()
    for record in records:
        fields = record['fields']
        if 'Date' in fields:
            all_dates.add(fields['Date'])
    logger.info(f"Found dates: {sorted(list(all_dates))}")
    logger.info(f"Looking for date: {target_date}")
    
    for record in records:
        fields = record['fields']
        if 'Date' in fields and 'Name' in fields:
            date = fields['Date']
            # Only process records for the target date
            if date != target_date:
                continue
                
            if date not in date_groups:
                date_groups[date] = []
            
            # Store full mentor details for description
            mentor_name = fields['Name']
            mentor_role = fields.get('Role', 'Mentor')
            mentor_company = fields.get('Company', '')
            mentor_bio = fields.get('Bio', '')
            
            mentor_details[mentor_name] = {
                'role': mentor_role,
                'company': mentor_company,
                'bio': mentor_bio
            }
            
            # Add mentor to this date group
            date_groups[date].append(mentor_name)

    # For each date, create the schedule
    for date, mentors in date_groups.items():
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
        
        # Determine number of slots needed based on the larger of mentors or companies
        num_slots = max(num_mentors, num_companies)
        time_slots = generate_time_slots(date, num_slots)
        
        logger.info(f"Scheduling for date {date}: {len(mentors)} mentors, {num_companies} companies, {num_slots} slots")
        
        # For each time slot
        for slot_index, slot in enumerate(time_slots):
            logger.info(f"Scheduling slot {slot_index+1}: {slot['start']} - {slot['end']}")
            
            # For each mentor in this slot
            for mentor_index, mentor in enumerate(mentors):
                # Get company in round-robin fashion
                company_index = (slot_index + mentor_index) % num_companies
                company = company_list[company_index]
                
                # Create formatted description with mentor details
                details = mentor_details[mentor]
                description = f"{mentor}, {details['role']}, {details['company']}: {details['bio']}"
                
                # Get the attendees (founder emails) for this company, handling BREAK case
                try:
                    attendees = companies[company]["emails"]
                except KeyError:
                    attendees = ""
                
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
                    'date': date
                }
                
                schedule.append(meeting)
    
    # Add debug information about total meetings created
    logger.info(f"Created a total of {len(schedule)} meetings")
    
    return schedule

def main():
    try:
        # Test the connection
        response = requests.get(
            AIRTABLE_API_URL,
            headers=AIRTABLE_HEADERS,
            params={'maxRecords': 1}
        )
        response.raise_for_status()
        logger.info("Successfully connected to Airtable")
        
        # Get target date from command line or user input
        target_date = get_target_date()
        logger.info(f"Filtering mentors for date: {target_date}")
        
        # Get all records
        records = get_airtable_records()
        logger.info(f"Found {len(records)} records in Airtable")
        
        # Debug: Print fields from first record
        if records:
            logger.info(f"Available fields in first record: {list(records[0]['fields'].keys())}")
        
        # Create schedule with target date
        schedule = create_schedule(records, COMPANIES, target_date)
        
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