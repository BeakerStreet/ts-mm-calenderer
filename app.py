import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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

def get_airtable_records():
    """Fetch all records from Airtable"""
    response = requests.get(AIRTABLE_API_URL, headers=AIRTABLE_HEADERS)
    response.raise_for_status()
    return response.json()['records']

def generate_time_slots(date_str):
    """
    Generate exact time slots as specified:
    09:30 - 09:50 Meeting 1
    09:55 - 10:15 Meeting 2
    10:20 - 10:40 Meeting 3
    10:55 - 11:15 Meeting 4
    11:20 - 11:40 Meeting 5
    11:50 - 12:50 Lunch
    12:50 - 13:10 Meeting 6
    13:15 - 13:35 Meeting 7
    13:40 - 14:00 Meeting 8
    """
    slots = []
    date = datetime.strptime(date_str, '%Y-%m-%d')
    
    # Define the exact time slots as specified
    time_ranges = [
        ('09:30', '09:50'),
        ('09:55', '10:15'),
        ('10:20', '10:40'),
        ('10:55', '11:15'),
        ('11:20', '11:40'),
        # Lunch break 11:50 - 12:50
        ('12:50', '13:10'),
        ('13:15', '13:35'),
        ('13:40', '14:00')
    ]
    
    # Create slots based on the specified time ranges
    for start_str, end_str in time_ranges:
        start_time = datetime.strptime(f"{date_str} {start_str}", '%Y-%m-%d %H:%M')
        end_time = datetime.strptime(f"{date_str} {end_str}", '%Y-%m-%d %H:%M')
        
        slots.append({
            'start': start_time.isoformat(),
            'end': end_time.isoformat()
        })
    
    logger.info(f"Generated {len(slots)} meeting slots for {date_str}, with a lunch break from 11:50 to 12:50")
    
    return slots

def convert_name_to_url_format(name):
    """Convert a mentor name to URL format with lowercase and dashes instead of spaces"""
    # Remove any special characters and replace spaces with dashes
    url_name = name.lower().strip()
    # Replace multiple spaces with a single dash
    url_name = '-'.join([part for part in url_name.split() if part])
    return url_name

def create_schedule(records, companies, companies_with_emails):
    """Create a schedule of meetings between companies and mentors"""
    schedule = []
    
    # Group records by date and store full record info
    date_groups = {}
    mentor_details = {}  # Store mentor details for descriptions
    
    for record in records:
        fields = record['fields']
        if 'Date' in fields and 'Name' in fields:
            date = fields['Date']
            if date not in date_groups:
                date_groups[date] = []
            
            # Store full mentor details for description
            mentor_name = fields['Name']
            mentor_role = fields.get('Role', 'Mentor')  # Default to 'Mentor' if role not specified
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
        time_slots = generate_time_slots(date)
        num_companies = len(companies)
        num_mentors = len(mentors)
        
        logger.info(f"Scheduling for date {date}: {len(mentors)} mentors, {num_companies} companies")
        
        # Create a copy of companies list for this date to avoid modifying the original
        date_companies = companies.copy()
        
        # Track which mentor-company pairs have already met ON THIS DATE
        daily_meetings_held = set()
        
        # Track which companies each mentor has met today
        mentor_to_companies = {mentor: set() for mentor in mentors}
        
        # For each time slot
        for slot_index, slot in enumerate(time_slots):
            logger.info(f"Scheduling slot {slot_index+1}: {slot['start']} - {slot['end']}")
            
            # Create copy of mentors for this slot
            all_mentors_in_slot = mentors.copy()
            
            # If we have more mentors than companies, determine which mentor skips this slot
            if num_mentors > num_companies:
                # Determine which mentor to skip in this slot (rotate through all mentors)
                mentor_to_skip_index = slot_index % num_mentors
                mentor_to_skip = mentors[mentor_to_skip_index]
                logger.info(f"In slot {slot['start']}, {mentor_to_skip} will have an empty slot")
                
                # Create a BREAK event for this mentor
                meeting = {
                    'summary': f"{mentor_to_skip} <> BREAK",
                    'start_time': slot['start'],
                    'end_time': slot['end'],
                    'company': "BREAK",
                    'mentor': mentor_to_skip,
                    'description': f"Break time for {mentor_to_skip}",
                    'attendees': '',
                    'location': '',
                    'date': date
                }
                schedule.append(meeting)
                
                # Remove the mentor to skip from available mentors for this slot
                available_mentors = [m for m in all_mentors_in_slot if m != mentor_to_skip]
            else:
                # All mentors are available if we have enough or fewer mentors than companies
                available_mentors = all_mentors_in_slot.copy()
            
            # Available companies for this slot (make a copy to avoid modifying original)
            available_companies = date_companies.copy()
            
            # Temporary meetings for this slot
            temp_meetings = []
            
            # Match mentors with companies they haven't met yet
            for mentor in available_mentors[:]:  # Use a copy to allow removal during iteration
                # Check if there are any companies left that this mentor hasn't met
                unmet_companies = [c for c in available_companies if c not in mentor_to_companies[mentor]]
                
                if unmet_companies:
                    # Assign the first unmet company to this mentor
                    company = unmet_companies[0]
                    temp_meetings.append((mentor, company))
                    mentor_to_companies[mentor].add(company)
                    daily_meetings_held.add((mentor, company))
                    available_companies.remove(company)
                    available_mentors.remove(mentor)  # Remove this mentor from consideration for this slot
                else:
                    # No unmet companies available, give this mentor a break
                    meeting = {
                        'summary': f"{mentor} <> BREAK",
                        'start_time': slot['start'],
                        'end_time': slot['end'],
                        'company': "BREAK",
                        'mentor': mentor,
                        'description': f"Break time for {mentor} (all companies already met)",
                        'attendees': '',
                        'location': '',
                        'date': date
                    }
                    schedule.append(meeting)
                    available_mentors.remove(mentor)  # Remove this mentor from consideration for this slot
                    logger.info(f"{mentor} gets a BREAK in slot {slot_index+1} - already met all available companies")
            
            # Create the actual meeting entries for valid pairings
            for mentor, company in temp_meetings:
                # Create formatted description with mentor details
                details = mentor_details[mentor]
                description = f"{mentor}, {details['role']}, {details['company']}: {details['bio']}"
                
                # Get the attendees (founder emails) for this company
                attendees = companies_with_emails.get(company, '')
                
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
            
            # Rotate companies for next slot
            date_companies = date_companies[1:] + [date_companies[0]]
    
    # Add debug information about total meetings created
    logger.info(f"Created a total of {len(schedule)} meetings")
    
    # Count break events
    break_count = sum(1 for meeting in schedule if meeting['company'] == "BREAK")
    logger.info(f"Schedule includes {break_count} break events for mentors")
    
    # Check for duplicate meetings as a safety measure
    duplicate_check = {}
    for meeting in schedule:
        if meeting['company'] == "BREAK":
            continue  # Skip break events in duplicate checking
            
        date = meeting['date']
        mentor = meeting['mentor']
        company = meeting['company']
        key = (date, mentor, company)
        
        if key in duplicate_check:
            logger.warning(f"Duplicate detected: {mentor} <> {company} on {date}")
            # Print the time slots of the duplicates for debugging
            logger.warning(f"  Time 1: {duplicate_check[key]}, Time 2: {meeting['start_time']}")
        else:
            duplicate_check[key] = meeting['start_time']
    
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
        
        # Define companies (hardcoded list)
        companies = [
            'Alethica',
            'Ovida',
            'Parasol',
            'PrettyData',
            'Renn',
            'Tova',
            'Solim Health'
        ]
        
        # Define companies with their founder emails
        companies_with_emails = {
            'Alethica': 'faisal.ghaffar@alethica.com, aurelia.lefrapper@alethica.com',
            'Ovida': 'alex@ovida.io',
            'Renn': 'matan@getrenn.com, nleinov@gmail.com',
            'PrettyData': 'bww@prettydata.co',
            'Tova': 'alexa@tova.earth',
            'Solim Health': 'basnetabhaya@gmail.com, tonyelvis-steven@hotmail.com',
            'Parasol': 'Kasparharsaae@parasolplatforms.com, momirzan@parasolplatforms.com'
        }
        
        # Get company names to maintain the same order as before
        companies = list(companies_with_emails.keys())
        
        # Get all records
        records = get_airtable_records()
        logger.info(f"Found {len(records)} records in Airtable")
        
        # Debug: Print fields from first record
        if records:
            logger.info(f"Available fields in first record: {list(records[0]['fields'].keys())}")
        
        # Create schedule
        schedule = create_schedule(records, companies, companies_with_emails)
        
        # Convert to DataFrame and save to CSV
        df = pd.DataFrame(schedule)
        output_file = 'meeting_schedule.csv'
        
        # Check if file exists and remove it first to ensure clean write
        if os.path.exists(output_file):
            logger.info(f"Removing existing file: {output_file}")
            os.remove(output_file)
        
        # Write to CSV with mode='w' to ensure overwriting
        df.to_csv(output_file, index=False, mode='w')
        logger.info(f"Schedule has been exported to {output_file}")
        
        # Create backups directory if it doesn't exist
        backup_dir = 'backups'
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