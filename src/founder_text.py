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

def generate_founder_descriptions(schedule_df, target_date=None):
    """Generate founder descriptions for a specific date or all dates"""
    logger.info(f"Generating founder descriptions for date: {target_date if target_date else 'all dates'}")
    
    # Create the output directory if it doesn't exist
    output_dir = 'output/descriptions/founders'
    os.makedirs(output_dir, exist_ok=True)
    
    # Filter the schedule for the target date if specified
    if target_date:
        schedule_df = schedule_df[schedule_df['date'] == target_date]
        if schedule_df.empty:
            logger.warning(f"No meetings found for date {target_date}")
            return
    
    # Group by company and date
    founder_groups = schedule_df.groupby(['company', 'date'])
    
    # Generate description for each company on each day
    for (company, date), group in founder_groups:
        # Filter out BREAK entries
        meetings = group[group['company'] != 'BREAK'].copy()
        
        if meetings.empty:
            logger.info(f"No actual meetings for {company} on {date}, skipping")
            continue
        
        # Add formatted time for easier reading
        meetings['formatted_start_time'] = meetings['start_time'].apply(format_time)
        
        # Create a safe filename based on company name
        safe_filename = company.replace(' ', '_').replace('/', '_').replace('\\', '_')
        filename = f"{safe_filename}_{date}.md"
        filepath = os.path.join(output_dir, filename)
        
        # Generate the markdown content
        with open(filepath, 'w') as f:
            # Write header
            f.write(f"# Welcome to Mentor Magic {company}!\n\n")
            
            # Format the date for display
            display_date = datetime.strptime(date, '%Y-%m-%d').strftime('%A, %B %d, %Y')
            f.write(f"## Your Schedule for {display_date}\n\n")
            
            # Write meeting schedule
            f.write("You're meeting these mentors today:\n\n")
            
            for _, meeting in meetings.sort_values('start_time').iterrows():
                f.write(f"- **{meeting['mentor']}** at {meeting['formatted_start_time']}\n")
            
            # Add the lookbook reminder
            f.write("\n\nAs a reminder you can view all of the companies information the lookbooks here: ")
            f.write("https://techstars.notion.site/Techstars-London-Spring-2025-Startup-Lookbooks-1acf180a125280479486d54da5dc87c0\n\n")
            
            # Add an extra message at the end
            f.write("Thank you for participating in Mentor Magic! We're excited to connect you with our amazing mentors.\n")
        
        logger.info(f"Created description for {company} on {date} at {filepath}")

def generate_all_founders_summary(schedule_df, target_date=None):
    """Generate a summary file containing all founder descriptions for a specific date"""
    logger.info(f"Generating all founders summary for date: {target_date if target_date else 'all dates'}")
    
    # Create the output directory if it doesn't exist
    output_dir = 'output/descriptions/founders'
    os.makedirs(output_dir, exist_ok=True)
    
    # Filter the schedule for the target date if specified
    if target_date:
        schedule_df = schedule_df[schedule_df['date'] == target_date]
        if schedule_df.empty:
            logger.warning(f"No meetings found for date {target_date}")
            return
    
    # Group by date
    date_groups = schedule_df.groupby('date')
    
    for date, group in date_groups:
        # Filter out BREAK entries
        meetings = group[group['company'] != 'BREAK'].copy()
        
        if meetings.empty:
            logger.info(f"No actual meetings found for date {date}, skipping")
            continue
        
        # Create the summary file
        filename = f"all_founders_{date}.md"
        filepath = os.path.join(output_dir, filename)
        
        # Generate the markdown content
        with open(filepath, 'w') as f:
            # Write header
            f.write(f"# All Founder Schedules for Mentor Magic\n\n")
            
            # Format the date for display
            display_date = datetime.strptime(date, '%Y-%m-%d').strftime('%A, %B %d, %Y')
            f.write(f"## {display_date}\n\n")
            
            # Group meetings by company
            company_groups = meetings.groupby('company')
            
            for company, company_meetings in company_groups:
                # Read the individual company file
                safe_filename = company.replace(' ', '_').replace('/', '_').replace('\\', '_')
                individual_file = os.path.join(output_dir, f"{safe_filename}_{date}.md")
                
                if os.path.exists(individual_file):
                    with open(individual_file, 'r') as company_file:
                        content = company_file.read()
                        # Keep the first line (Welcome header) and write the rest
                        content_lines = content.split('\n')
                        f.write(content_lines[0] + '\n\n')  # Write the welcome line
                        f.write('\n'.join(content_lines[1:]))  # Write the rest
                        f.write('\n\n')
                        f.write('---\n\n')  # Add a separator between companies
            
            # Add the lookbook reminder
            f.write("\n\nAs a reminder you can view all of the companies information the lookbooks here: ")
            f.write("https://techstars.notion.site/Techstars-London-Spring-2025-Startup-Lookbooks-1acf180a125280479486d54da5dc87c0\n\n")
            
            # Add an extra message at the end
            f.write("Thank you for participating in Mentor Magic! We're excited to connect you with our amazing mentors.\n")
        
        logger.info(f"Created all founders summary for {date} at {filepath}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate founder meeting descriptions from schedule")
    parser.add_argument("--date", help="Generate descriptions for a specific date (YYYY-MM-DD format)")
    args = parser.parse_args()
    
    # Read the schedule
    schedule_df = read_meeting_schedule()
    
    # Generate individual descriptions
    generate_founder_descriptions(schedule_df, args.date)
    
    # Generate all founders summary
    generate_all_founders_summary(schedule_df, args.date)
    
    logger.info("Description generation complete!")

if __name__ == "__main__":
    main() 