#!/usr/bin/env python3
"""
Utility for refreshing mentors.csv from Airtable data.
Fetches mentor data from Airtable and updates the mentors.csv file.
"""

import os
import sys
import pandas as pd
import requests
from datetime import datetime
import logging
import argparse
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Path configurations
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CONFIG_DIR, '..'))
MENTORS_CSV_PATH = os.path.join(CONFIG_DIR, 'mentors.csv')

# Load environment variables - search for .env in different possible locations
env_paths = [
    os.path.join(CONFIG_DIR, '.env'),  # config/.env
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

# Airtable setup
AIRTABLE_TOKEN = os.getenv('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_ID = 'tbllbtrlfcmReNxQR'  # Mentors table ID

def get_airtable_records():
    """Fetch all mentor records from Airtable"""
    if not AIRTABLE_TOKEN or not AIRTABLE_BASE_ID:
        logger.error("Missing Airtable credentials. Please set AIRTABLE_TOKEN and AIRTABLE_BASE_ID in .env file.")
        sys.exit(1)
    
    # Extract just the base ID - it might contain other parts separated by /
    base_id = AIRTABLE_BASE_ID.split('/')[0] if '/' in AIRTABLE_BASE_ID else AIRTABLE_BASE_ID
        
    url = f"https://api.airtable.com/v0/{base_id}/{AIRTABLE_TABLE_ID}"
    headers = {
        'Authorization': f'Bearer {AIRTABLE_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    logger.info(f"Fetching mentor data from Airtable (Base ID: {base_id}, Table ID: {AIRTABLE_TABLE_ID})")
    logger.info(f"Using Token: {AIRTABLE_TOKEN[:10]}...")  # Only show first 10 chars for security
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        records = response.json()['records']
        logger.info(f"Successfully fetched {len(records)} mentor records from Airtable (will filter for 'Booked - March 2025' status)")
        return records
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Airtable: {str(e)}")
        sys.exit(1)

def convert_records_to_dataframe(records, filter_date=None):
    """Convert Airtable records to DataFrame format for CSV
    
    Args:
        records (list): Records from Airtable API
        filter_date (str, optional): If specified, only include mentors available on this date
    """
    mentors_data = []
    date_fields = ["Date"] # The field name for dates in Airtable
    
    for record in records:
        fields = record['fields']
        
        # Skip records without name
        if 'Name' not in fields:
            continue
            
        # Skip mentors without "Booked - March 2025" status
        mentor_status = fields.get('Status', '')
        if mentor_status != "Booked - March 2025":
            continue
            
        # Extract dates if available
        dates = []
        for date_field in date_fields:
            if date_field in fields:
                dates.append(fields[date_field])
        
        # If filter_date is specified, only include mentors available on that date
        if filter_date and dates:
            if filter_date not in dates:
                continue
        
        # Create mentor entry
        mentor = {
            'name': fields.get('Name', ''),
            'role': fields.get('Role', ''),
            'company': fields.get('Company', ''),
            'bio': fields.get('Bio', ''),
            'dates': ','.join(dates) if dates else ''
        }
        
        mentors_data.append(mentor)
    
    # Create DataFrame
    df = pd.DataFrame(mentors_data)
    
    if filter_date:
        logger.info(f"Filtered to {len(df)} booked mentors available on date: {filter_date}")
    else:
        logger.info(f"Converted {len(df)} booked mentor records to DataFrame")
    
    return df

def update_mentors_csv(df, output_path=None):
    """Update mentors.csv with new data"""
    if output_path is None:
        output_path = MENTORS_CSV_PATH
        
    # Create backup of existing file if it exists
    if os.path.exists(output_path):
        backup_dir = os.path.join(os.path.dirname(output_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'mentors_{timestamp}.csv')
        
        try:
            # Read existing file and save as backup
            existing_df = pd.read_csv(output_path)
            existing_df.to_csv(backup_path, index=False)
            logger.info(f"Created backup of existing mentors.csv at {backup_path}")
        except Exception as e:
            logger.warning(f"Could not create backup: {str(e)}")
    
    # Write new data to CSV
    df.to_csv(output_path, index=False)
    logger.info(f"Successfully updated mentors data at {output_path}")
    logger.info(f"Total booked mentors: {len(df)}")
    
    # Log dates available
    if 'dates' in df.columns:
        all_dates = set()
        for dates_str in df['dates'].dropna():
            dates = dates_str.split(',')
            all_dates.update(dates)
        logger.info(f"Available dates for booked mentors: {sorted(list(all_dates))}")

def main():
    parser = argparse.ArgumentParser(description='Refresh mentors.csv with data from Airtable')
    parser.add_argument('--output', type=str, help='Output file path (default: config/mentors.csv)')
    parser.add_argument('--date', type=str, help='Filter mentors to those available on this date (YYYY-MM-DD)')
    args = parser.parse_args()
    
    output_path = args.output if args.output else MENTORS_CSV_PATH
    filter_date = args.date
    
    logger.info("Only mentors with 'Booked - March 2025' status will be included")
    
    if filter_date:
        logger.info(f"Filtering booked mentors to those available on: {filter_date}")
    
    try:
        records = get_airtable_records()
        df = convert_records_to_dataframe(records, filter_date)
        update_mentors_csv(df, output_path)
    except Exception as e:
        logger.error(f"Error during refresh: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 