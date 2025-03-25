import os
import logging
import requests
import pandas as pd
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys
import argparse
import subprocess
from generate_mentor_descriptions import generate_mentor_descriptions
from generate_daily_summaries import generate_daily_summaries

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
    
    # Use quoting options to handle comma-separated emails within fields
    df = pd.read_csv(companies_file, quoting=csv.QUOTE_ALL)
    
    # Fill NaN values in founder_emails with empty string
    df['founder_emails'] = df['founder_emails'].fillna('').astype(str)
    
    # Convert DataFrame to dictionary format
    companies = {}
    for _, row in df.iterrows():
        companies[row['company_name']] = {
            'emails': row['founder_emails']
        }
    
    # Log the loaded companies for debugging
    logger.info(f"Loaded {len(companies)} companies from config")
    for company, data in companies.items():
        emails = data['emails']
        if ',' in emails:
            logger.info(f"Company '{company}' has multiple emails: {emails}")
    
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
            # Get company in round-robin fashion
            company_index = (slot_index + mentor_index) % num_companies
            company = company_list[company_index]
            
            # Create formatted description with mentor details
            details = mentor_details[mentor]
            description = f"{mentor}, {details['role']}, {details['company']}: {details['bio']}"
            
            # Get the attendees (founder emails) for this company
            try:
                # Parse comma-separated emails
                attendees_str = companies[company]["emails"]
                # Ensure we're working with a string
                if not isinstance(attendees_str, str):
                    attendees_str = str(attendees_str)
                    logger.warning(f"Converted non-string email value to string for company: {company}")
                
                attendees = [email.strip() for email in attendees_str.split(',') if email.strip()]
            except Exception as e:
                logger.error(f"Error processing emails for company {company}: {str(e)}")
                # Provide an empty list as fallback
                attendees = []
            
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

def run_generate_descriptions(schedule_df, target_date):
    """Generate mentor descriptions from schedule"""
    logger.info(f"Generating mentor descriptions for date: {target_date}")
    
    # Ensure the descriptions output directory exists
    descriptions_dir = OUTPUT_PATHS['descriptions']
    if not os.path.exists(descriptions_dir):
        os.makedirs(descriptions_dir)
        logger.info(f"Created descriptions directory: {descriptions_dir}")
    
    # Create a copy of the generate_mentor_descriptions function with correct output directory
    def patched_generate_descriptions(schedule_df, target_date):
        """Custom implementation that saves to the correct output directory"""
        logger.info(f"Generating mentor descriptions for date: {target_date if target_date else 'all dates'}")
        
        # Use the correct output directory
        output_dir = descriptions_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Filter the schedule for the target date if specified
        if target_date:
            schedule_df = schedule_df[schedule_df['date'] == target_date]
            if schedule_df.empty:
                logger.warning(f"No meetings found for date {target_date}")
                return
        
        # Dictionary to store information for master file, keyed by date
        master_data = {}
        
        # Group by mentor and date
        mentor_groups = schedule_df.groupby(['mentor', 'date'])
        
        # Generate description for each mentor on each day
        for (mentor, date), group in mentor_groups:
            # Filter out BREAK entries if any exist
            if 'company' in group.columns:
                meetings = group[group['company'] != 'BREAK'].copy()
            else:
                meetings = group.copy()
            
            if meetings.empty:
                logger.info(f"No actual meetings for {mentor} on {date}, skipping")
                continue
            
            # Add formatted time for easier reading
            meetings['formatted_start_time'] = meetings['start_time'].apply(
                lambda t: datetime.fromisoformat(t).strftime('%H:%M') if isinstance(t, str) else pd.to_datetime(t).strftime('%H:%M')
            )
            
            # Create a safe filename based on mentor name
            safe_filename = mentor.replace(' ', '_').replace('/', '_').replace('\\', '_')
            filename = f"{safe_filename}_{date}.md"
            filepath = os.path.join(output_dir, filename)
            
            # Generate the markdown content
            with open(filepath, 'w') as f:
                # Write header
                f.write(f"# Welcome to Mentor Magic {mentor}!\n\n")
                
                # Format the date for display
                display_date = datetime.strptime(date, '%Y-%m-%d').strftime('%A, %B %d, %Y')
                f.write(f"## Your Schedule for {display_date}\n\n")
                
                # Write meeting schedule
                f.write("You're meeting these companies today:\n\n")
                
                for _, meeting in meetings.sort_values('start_time').iterrows():
                    f.write(f"- **{meeting['company']}** at {meeting['formatted_start_time']}\n")
                
                # Add an extra message at the end
                f.write("\n\nThank you for participating in Mentor Magic! Your expertise and guidance are invaluable to our companies.\n")
            
            logger.info(f"Created description for {mentor} on {date} at {filepath}")
            
            # Store data for master file
            if date not in master_data:
                master_data[date] = []
            
            master_data[date].append({
                'mentor': mentor,
                'meetings': meetings.sort_values('start_time').to_dict('records')
            })
        
        # Create master files for each date
        for date, mentors in master_data.items():
            # Create master file for this date
            master_filename = f"All_Mentors_{date}.md"
            master_filepath = os.path.join(output_dir, master_filename)
            
            with open(master_filepath, 'w') as f:
                # Format the date for display
                display_date = datetime.strptime(date, '%Y-%m-%d').strftime('%A, %B %d, %Y')
                f.write(f"# Mentor Magic Schedule - {display_date}\n\n")
                
                # Sort mentors alphabetically
                mentors.sort(key=lambda x: x['mentor'])
                
                # Write each mentor's schedule
                for mentor_data in mentors:
                    mentor = mentor_data['mentor']
                    meetings = mentor_data['meetings']
                    
                    f.write(f"## {mentor}\n\n")
                    
                    if not meetings:
                        f.write("No scheduled meetings for today.\n\n")
                        continue
                    
                    for meeting in meetings:
                        f.write(f"- **{meeting['company']}** at {meeting['formatted_start_time']}\n")
                    
                    f.write("\n")
            
            logger.info(f"Created master schedule for {date} at {master_filepath}")
    
    # Get the path to the meeting schedule CSV
    schedule_path = OUTPUT_PATHS['schedule']
    logger.info(f"Using schedule file: {schedule_path}")
    
    # Change working directory to ensure outputs go to the right place
    original_dir = os.getcwd()
    os.chdir(PROJECT_ROOT)
    
    try:
        # Read the CSV directly
        schedule_df = pd.read_csv(schedule_path)
        
        # Use the patched version to ensure correct output directory
        patched_generate_descriptions(schedule_df, target_date)
        
        logger.info(f"Successfully generated mentor descriptions for {target_date}")
    except Exception as e:
        logger.error(f"Error generating mentor descriptions: {str(e)}")
    finally:
        # Change back to original directory
        os.chdir(original_dir)

def run_generate_summaries(schedule_df, target_date):
    """Generate daily summaries from schedule"""
    logger.info(f"Generating daily summaries for date: {target_date}")
    
    # Ensure the summaries output directory exists
    summaries_dir = OUTPUT_PATHS['summaries']
    if not os.path.exists(summaries_dir):
        os.makedirs(summaries_dir)
        logger.info(f"Created summaries directory: {summaries_dir}")
    
    # Create daily_summaries directory if it doesn't exist (needed by generate_daily_summaries)
    daily_summaries_dir = os.path.join(PROJECT_ROOT, 'daily_summaries')
    if not os.path.exists(daily_summaries_dir):
        os.makedirs(daily_summaries_dir)
        logger.info(f"Created daily_summaries directory: {daily_summaries_dir}")
    
    # Get the path to the meeting schedule CSV
    schedule_path = OUTPUT_PATHS['schedule']
    logger.info(f"Using schedule file: {schedule_path}")
    
    # Change working directory to ensure outputs go to the right place
    original_dir = os.getcwd()
    os.chdir(PROJECT_ROOT)
    
    try:
        # Read the CSV directly
        schedule_df = pd.read_csv(schedule_path)
        
        # Filter for the target date if specified
        if target_date and target_date != 'all dates':
            schedule_df = schedule_df[schedule_df['date'] == target_date]
        
        # Convert start_time to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(schedule_df['start_time']):
            schedule_df['start_time'] = pd.to_datetime(schedule_df['start_time'])
        
        # Get unique dates
        dates = schedule_df['date'].unique()
        
        for date in dates:
            logger.info(f"Generating daily summary for date: {date}")
            day_schedule = schedule_df[schedule_df['date'] == date].copy()
            
            # Get time slots for each mentor
            time_slots = day_schedule.groupby('mentor').apply(
                lambda x: pd.Series(x['company'].values, index=x['start_time'].dt.strftime('%H:%M').values)
            ).reset_index()
            
            # Sort columns by time
            time_slots = time_slots.reindex(columns=['mentor'] + sorted(time_slots.columns[1:]))
            
            # Save to both locations
            os.makedirs(daily_summaries_dir, exist_ok=True)
            output_file = os.path.join(daily_summaries_dir, f'meeting_summary_{date}.csv')
            time_slots.to_csv(output_file, index=False)
            
            # Also save to output/summaries
            summary_file = os.path.join(summaries_dir, f'meeting_summary_{date}.csv')
            time_slots.to_csv(summary_file, index=False)
            
            logger.info(f"Created daily summary for {date} at {output_file}")
            logger.info(f"Also saved to {summary_file}")
        
        logger.info(f"Successfully generated daily summaries for {target_date}")
    except Exception as e:
        logger.error(f"Error generating daily summaries: {str(e)}")
    finally:
        # Change back to original directory
        os.chdir(original_dir)

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
        
        # Convert attendees lists to comma-separated strings to avoid brackets in CSV
        if 'attendees' in df.columns:
            df['attendees'] = df['attendees'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
            logger.info("Converted attendees lists to comma-separated strings")
        
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
        
        # Automatically generate descriptions and summaries
        run_generate_descriptions(df, target_date)
        run_generate_summaries(df, target_date)
        
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main() 