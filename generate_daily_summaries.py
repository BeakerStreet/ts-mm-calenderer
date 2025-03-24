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

def read_meeting_schedule(csv_path='meeting_schedule.csv'):
    """Read meeting schedule from CSV file"""
    logger.info(f"Reading meeting schedule from {csv_path}")
    return pd.read_csv(csv_path)

def format_time(time_str):
    """Format time string from ISO format to human-readable format (HH:MM)"""
    return datetime.fromisoformat(time_str).strftime('%H:%M')

def generate_daily_summaries(schedule_df, target_date=None):
    """Generate daily meeting summary tables in CSV format"""
    logger.info(f"Generating daily summaries for date: {target_date if target_date else 'all dates'}")
    
    # Create the output directory if it doesn't exist
    output_dir = 'daily_summaries'
    os.makedirs(output_dir, exist_ok=True)
    
    # Filter the schedule for the target date if specified
    if target_date:
        schedule_df = schedule_df[schedule_df['date'] == target_date]
        if schedule_df.empty:
            logger.warning(f"No meetings found for date {target_date}")
            return
    
    # Group by date
    date_groups = schedule_df.groupby('date')
    
    for date, day_schedule in date_groups:
        # Get unique mentors for this day
        mentors = sorted(day_schedule['mentor'].unique())
        
        # Create a pivot table with mentors as index and time slots as columns
        pivot_df = pd.pivot_table(
            day_schedule,
            values='company',
            index='mentor',
            columns=day_schedule.groupby('mentor').cumcount() + 1,
            aggfunc='first'
        )
        
        # Get the start times for each meeting slot
        time_slots = day_schedule.groupby('mentor').apply(
            lambda x: x.sort_values('start_time')['start_time'].apply(format_time).tolist()
        ).iloc[0]  # All mentors have the same time slots
        
        # Rename columns to use start times
        pivot_df.columns = time_slots
        
        # Sort by mentor name
        pivot_df = pivot_df.sort_index()
        
        # Create output filename
        output_file = os.path.join(output_dir, f'meeting_summary_{date}.csv')
        
        # Save to CSV
        pivot_df.to_csv(output_file)
        logger.info(f"Created daily summary for {date} at {output_file}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate daily meeting summary tables from schedule")
    parser.add_argument("--date", help="Generate summary for a specific date (YYYY-MM-DD format)")
    args = parser.parse_args()
    
    # Read the schedule
    schedule_df = read_meeting_schedule()
    
    # Generate summaries
    generate_daily_summaries(schedule_df, args.date)
    
    logger.info("Daily summary generation complete!")

if __name__ == "__main__":
    main() 