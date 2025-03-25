import os
import pickle
import logging
import pandas as pd
import time
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Google Calendar API setup
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_google_calendar_service():
    """Initialize and return Google Calendar service"""
    logger.info("Initializing Google Calendar service")
    creds = None
    
    # Define the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..'))
    
    # Path to token file
    token_path = os.path.join(project_root, 'token.pickle')
    
    # Path to credentials file
    credentials_path = os.path.join(project_root, 'credentials.json')
    
    if os.path.exists(token_path):
        logger.info(f"Found existing token file at {token_path}")
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            creds.refresh(Request())
        else:
            logger.info(f"No valid credentials found. Starting OAuth flow using {credentials_path}")
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        logger.info(f"Saving credentials to {token_path}")
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)

def get_or_create_calendar(service, calendar_name="Mentor Madness Detailed Invites"):
    """Get or create a calendar with the specified name and return its ID"""
    logger.info(f"Looking for calendar: {calendar_name}")
    
    # Try to find the calendar by name
    calendar_list = service.calendarList().list().execute()
    for calendar_entry in calendar_list.get('items', []):
        if calendar_entry.get('summary') == calendar_name:
            logger.info(f"Found existing calendar: {calendar_name} with ID: {calendar_entry['id']}")
            return calendar_entry['id']
    
    # Calendar not found, create a new one
    logger.info(f"Calendar '{calendar_name}' not found. Creating new calendar.")
    calendar = {
        'summary': calendar_name,
        'timeZone': 'UTC',
        'description': 'Calendar for Techstars London Mentor Madness detailed meeting invites'
    }
    
    created_calendar = service.calendars().insert(body=calendar).execute()
    calendar_id = created_calendar['id']
    logger.info(f"Successfully created new calendar with ID: {calendar_id}")
    return calendar_id

def create_calendar_event(service, event_data, calendar_id):
    """Create a single calendar event in the specified calendar"""
    logger.info(f"Creating calendar event: {event_data['summary']} in calendar ID: {calendar_id}")
    
    event = {
        'summary': event_data['summary'],
        'description': event_data['description'],
        'start': {
            'dateTime': event_data['start_time'],
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': event_data['end_time'],
            'timeZone': 'UTC',
        },
        'attendees': [],  # Will be populated when email field is used
        'reminders': {
            'useDefault': True
        },
    }
    
    # Add location if present
    if 'location' in event_data and event_data['location']:
        event['location'] = event_data['location']
    
    # Add attendees if present and is a string
    attendees_field = event_data.get('attendees', '')
    if attendees_field and isinstance(attendees_field, str):
        attendees = [{'email': email.strip()} for email in attendees_field.split(',') if email.strip()]
        event['attendees'] = attendees
    
    # Create the event
    created_event = service.events().insert(
        calendarId=calendar_id,
        body=event,
        sendUpdates='all'
    ).execute()
    
    logger.info(f"Successfully created event with ID: {created_event.get('id')}")
    return created_event.get('id')

def test_mode(df):
    """Modify the dataframe to clear all attendees for testing"""
    logger.info("Entering test mode - clearing all attendees")
    df['attendees'] = ''
    return df

def main():
    try:
        # Define paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '..'))
        
        # Read the schedule from CSV
        csv_file = os.path.join(project_root, 'output', 'meeting_schedule.csv')
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"Schedule file {csv_file} not found. Run app.py first to generate it.")
        
        df = pd.read_csv(csv_file)
        total_events = len(df)
        logger.info(f"Loaded {total_events} events from {csv_file}")
        
        # Check if test mode is enabled
        if len(sys.argv) > 1 and sys.argv[1] == '--test':
            df = test_mode(df)
            logger.info("Test mode enabled - no notifications will be sent")
        
        # Extract unique dates from the dataframe
        # Assuming the start_time is in ISO format like '2023-11-15T09:00:00'
        df['date'] = df['start_time'].apply(lambda x: x.split('T')[0])
        unique_dates = sorted(df['date'].unique())
        
        # Display available dates to the user
        print("\nAvailable dates for calendar events:")
        for i, date in enumerate(unique_dates):
            print(f"{i+1}. {date}")
        
        # Prompt user to select a date
        selection = input("\nEnter the number of the date for which you want to create events: ")
        try:
            date_index = int(selection) - 1
            if date_index < 0 or date_index >= len(unique_dates):
                raise ValueError("Invalid selection")
            selected_date = unique_dates[date_index]
        except (ValueError, IndexError):
            logger.error("Invalid date selection. Exiting.")
            return
        
        # Filter events for the selected date
        date_events = df[df['date'] == selected_date]
        num_date_events = len(date_events)
        logger.info(f"Found {num_date_events} events for date {selected_date}")
        
        if num_date_events == 0:
            logger.warning(f"No events found for date {selected_date}")
            return
        
        # Initialize Google Calendar service
        service = get_google_calendar_service()
        
        # Get or create the Mentor Madness calendar
        calendar_id = get_or_create_calendar(service)
        
        logger.info(f"Processing {num_date_events} events for {selected_date}")
        
        # Track successful and failed events
        created_events = []
        failed_events = []
        
        # Process events for the selected date
        for i, (_, event_data) in enumerate(date_events.iterrows()):
            try:
                # Create the event
                event_id = create_calendar_event(service, event_data, calendar_id)
                created_events.append((i, event_id, event_data['summary']))
                logger.info(f"Created event {i+1}/{num_date_events}: {event_data['summary']}")
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error creating event {i+1} ({event_data['summary']}): {str(e)}")
                failed_events.append((i, event_data['summary'], str(e)))
        
        # Summary
        logger.info(f"Calendar processing complete. Created {len(created_events)} events for {selected_date}.")
        
        if failed_events:
            logger.warning(f"{len(failed_events)} events failed to create:")
            for i, summary, error in failed_events:
                logger.warning(f"  - Event {i+1}: {summary}: {error}")
                
    except Exception as e:
        logger.error(f"Error creating calendar events: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main() 