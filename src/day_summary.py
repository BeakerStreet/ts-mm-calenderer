import os
import logging
import pandas as pd
from datetime import datetime
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def read_meeting_schedule(csv_path='output/meeting_schedule.csv'):
    """Read meeting schedule from CSV file"""
    logger.info(f"Reading meeting schedule from {csv_path}")
    return pd.read_csv(csv_path)

def format_time(time_str):
    """Format time string from ISO format to human-readable format (HH:MM)"""
    return datetime.fromisoformat(time_str).strftime('%H:%M')

def generate_daily_summaries(date_str=None):
    """Generate daily summaries for the meeting schedule."""
    logger.info("Reading meeting schedule from meeting_schedule.csv")
    df = pd.read_csv('output/meeting_schedule.csv')
    
    if date_str and date_str != 'all dates':
        df = df[df['date'] == date_str]
    
    # Convert start_time to datetime
    df['start_time'] = pd.to_datetime(df['start_time'])
    
    # Get unique dates
    dates = df['date'].unique()
    
    # Create the output directory if it doesn't exist
    output_dir = 'output/daily_summaries'
    os.makedirs(output_dir, exist_ok=True)
    
    for date in dates:
        logger.info(f"Generating daily summary for date: {date}")
        day_schedule = df[df['date'] == date].copy()
        
        # Get time slots for each mentor
        time_slots = day_schedule.groupby('mentor').apply(
            lambda x: pd.Series(x['company'].values, index=x['start_time'].dt.strftime('%H:%M').values)
        ).reset_index()
        
        # Sort columns by time
        time_slots = time_slots.reindex(columns=['mentor'] + sorted(time_slots.columns[1:]))
        
        # Save to CSV
        output_file = os.path.join(output_dir, f'meeting_summary_{date}.csv')
        time_slots.to_csv(output_file, index=False)
        logger.info(f"Created daily summary for {date} at {output_file}")
    
    logger.info("Daily summary generation complete!")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate daily meeting summary tables from schedule")
    parser.add_argument("--date", help="Generate summary for a specific date (YYYY-MM-DD format)")
    args = parser.parse_args()
    
    # Read the schedule
    schedule_df = read_meeting_schedule()
    
    # Generate summaries
    generate_daily_summaries(args.date)
    
    logger.info("Daily summary generation complete!")

if __name__ == "__main__":
    main() 