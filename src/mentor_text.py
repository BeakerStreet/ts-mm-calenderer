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

def generate_mentor_descriptions(schedule_df, target_date=None, create_master=False):
    """Generate mentor descriptions for a specific date or all dates"""
    logger.info(f"Generating mentor descriptions for date: {target_date if target_date else 'all dates'}")
    
    # Create the output directory if it doesn't exist
    output_dir = 'output/descriptions/mentors'
    os.makedirs(output_dir, exist_ok=True)
    
    # Filter the schedule for the target date if specified
    if target_date:
        schedule_df = schedule_df[schedule_df['date'] == target_date]
        if schedule_df.empty:
            logger.warning(f"No meetings found for date {target_date}")
            return
    
    # Group by mentor and date
    mentor_groups = schedule_df.groupby(['mentor', 'date'])
    
    # Generate description for each mentor on each day
    for (mentor, date), group in mentor_groups:
        # Filter out BREAK entries
        meetings = group[group['company'] != 'BREAK'].copy()
        
        if meetings.empty:
            logger.info(f"No actual meetings for {mentor} on {date}, skipping")
            continue
        
        # Add formatted time for easier reading
        meetings['formatted_start_time'] = meetings['start_time'].apply(format_time)
        
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
            
            # Add the lookbook reminder
            f.write("\n\nAs a reminder you can view all of the companies information the lookbooks here: ")
            f.write("https://techstars.notion.site/Techstars-London-Spring-2025-Startup-Lookbooks-1acf180a125280479486d54da5dc87c0\n\n")
            
            # Add an extra message at the end
            f.write("Thank you for participating in Mentor Magic! Your expertise and guidance are invaluable to our companies.\n")
        
        logger.info(f"Created description for {mentor} on {date} at {filepath}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate mentor meeting descriptions from schedule")
    parser.add_argument("--date", help="Generate descriptions for a specific date (YYYY-MM-DD format)")
    parser.add_argument("--no-master", action="store_true", help="Skip creation of master files")
    args = parser.parse_args()
    
    # Read the schedule
    schedule_df = read_meeting_schedule()
    
    # Generate descriptions (always skipping master file creation)
    generate_mentor_descriptions(schedule_df, args.date, False)
    
    logger.info("Description generation complete!")

if __name__ == "__main__":
    main() 