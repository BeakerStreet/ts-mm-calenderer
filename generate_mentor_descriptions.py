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

def generate_mentor_descriptions(schedule_df, target_date=None, create_master=True):
    """Generate mentor descriptions for a specific date or all dates"""
    logger.info(f"Generating mentor descriptions for date: {target_date if target_date else 'all dates'}")
    
    # Create the output directory if it doesn't exist
    output_dir = 'descriptions'
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
    if create_master and master_data:
        create_master_files(master_data, output_dir)

def create_master_files(master_data, output_dir):
    """Create master files with all mentor schedules for each date"""
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

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate mentor meeting descriptions from schedule")
    parser.add_argument("--date", help="Generate descriptions for a specific date (YYYY-MM-DD format)")
    parser.add_argument("--no-master", action="store_true", help="Skip creation of master files")
    args = parser.parse_args()
    
    # Read the schedule
    schedule_df = read_meeting_schedule()
    
    # Generate descriptions
    generate_mentor_descriptions(schedule_df, args.date, not args.no_master)
    
    logger.info("Description generation complete!")

if __name__ == "__main__":
    main() 