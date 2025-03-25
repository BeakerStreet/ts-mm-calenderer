#!/usr/bin/env python3
"""
Configuration utility for meeting schedules.
Allows users to input meeting parameters and updates CSV headers with calculated meeting times.
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_time(time_str):
    """Parse time string in HH:MM format to datetime object"""
    try:
        return datetime.strptime(time_str, "%H:%M")
    except ValueError:
        logger.error(f"Invalid time format: {time_str}. Please use HH:MM format.")
        return None

def generate_meeting_times(
    mtg_length, 
    num_meetings, 
    has_breaks, 
    break_length, 
    has_lunch, 
    lunch_length, 
    first_mtg_start
):
    """
    Generate meeting start and end times based on parameters
    
    Args:
        mtg_length (int): Length of each meeting in minutes
        num_meetings (int): Number of meetings
        has_breaks (bool): Whether to include breaks between meetings
        break_length (int): Length of breaks in minutes (if has_breaks)
        has_lunch (bool): Whether to include a lunch break
        lunch_length (int): Length of lunch break in minutes (if has_lunch)
        first_mtg_start (str): Start time of first meeting (HH:MM)
        
    Returns:
        list: List of dictionaries with meeting info
    """
    # Parse time strings to datetime objects
    start_time = parse_time(first_mtg_start)
    
    if start_time is None:
        return []
    
    # Set the date to today (we only care about time)
    today = datetime.today().date()
    start_time = datetime.combine(today, start_time.time())
    
    meetings = []
    current_time = start_time
    meeting_count = 0
    
    while meeting_count < num_meetings:
        meeting_end = current_time + timedelta(minutes=mtg_length)
        
        meetings.append({
            "start": current_time.strftime("%H:%M"),
            "end": meeting_end.strftime("%H:%M"),
            "header": f"{current_time.strftime('%H:%M')}-{meeting_end.strftime('%H:%M')}"
        })
        
        meeting_count += 1
        
        # Add break time if applicable
        if has_breaks and meeting_count < num_meetings:
            current_time = meeting_end + timedelta(minutes=break_length)
        else:
            current_time = meeting_end
        
        # Add lunch break if applicable and we've reached half the meetings
        if has_lunch and meeting_count == num_meetings // 2:
            logger.info(f"Adding lunch break of {lunch_length} minutes")
            current_time = current_time + timedelta(minutes=lunch_length)
    
    return meetings

def load_sample_mentors(num_needed):
    """Load sample mentor names as mentor1, mentor2, etc."""
    mentors = []
    for i in range(1, num_needed + 1):
        mentors.append(f"mentor{i}")
    return mentors

def update_csv_with_schedule(meetings, output_file):
    """Update the CSV with meeting times and sample mentor slots"""
    try:
        # Generate column headers
        columns = ["mentor"]
        columns.extend([m["header"] for m in meetings])
        
        # Load mentors (same number as meetings)
        num_mentors = len(meetings)
        mentors = load_sample_mentors(num_mentors)
        
        # Create DataFrame with mentors and empty slots
        data = []
        for mentor in mentors:
            # Create a row for each mentor with empty slots
            row = [mentor] + ["" for _ in range(len(meetings))]
            data.append(row)
            
        # Create DataFrame
        df = pd.DataFrame(data, columns=columns)
        
        # Make sure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Write to CSV
        df.to_csv(output_file, index=False)
        logger.info(f"Successfully created meeting schedule configuration at {output_file}")
        
        # Print confirmation details
        logger.info("\nSchedule Details:")
        for i, m in enumerate(meetings, 1):
            logger.info(f"Meeting {i}: {m['start']} - {m['end']}")
        
        logger.info(f"\nSample mentors added: {len(mentors)}")
        for mentor in mentors:
            logger.info(f"- {mentor}")
        
    except Exception as e:
        logger.error(f"Error updating CSV: {str(e)}")
        sys.exit(1)

def get_integer_input(prompt, default=None, min_value=1, max_value=None):
    """Get integer input from user with validation"""
    default_str = f" [{default}]" if default is not None else ""
    
    while True:
        try:
            value = input(f"{prompt}{default_str}: ").strip()
            if value == "" and default is not None:
                return default
            
            value = int(value)
            if value < min_value:
                print(f"Value must be at least {min_value}. Please try again.")
                continue
                
            if max_value is not None and value > max_value:
                print(f"Value must be at most {max_value}. Please try again.")
                continue
                
            return value
        except ValueError:
            print("Please enter a valid integer.")

def get_time_input(prompt, default=None):
    """Get time input from user with validation"""
    default_str = f" [{default}]" if default is not None else ""
    
    while True:
        time_str = input(f"{prompt}{default_str}: ").strip()
        if time_str == "" and default is not None:
            return default
            
        try:
            # Validate time format
            datetime.strptime(time_str, "%H:%M")
            return time_str
        except ValueError:
            print("Invalid time format. Please use HH:MM format (e.g., 09:30).")

def get_yes_no_input(prompt, default=None):
    """Get yes/no input from user"""
    default_str = ""
    if default is not None:
        default_str = " [Y/n]" if default else " [y/N]"
    
    while True:
        response = input(f"{prompt}{default_str}: ").strip().lower()
        if response == "" and default is not None:
            return default
            
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        else:
            print("Please enter 'y' or 'n'.")

def main():
    print("\n=== Mentor Meeting Schedule Configuration ===\n")
    
    # Get user inputs
    mtg_length = get_integer_input("Meeting length in minutes", default=15, min_value=5)
    num_meetings = get_integer_input("Number of meetings", default=8, min_value=1)
    
    has_breaks = get_yes_no_input("Include breaks between meetings", default=True)
    break_length = 0
    if has_breaks:
        break_length = get_integer_input("Break length in minutes", default=5, min_value=1)
    
    has_lunch = get_yes_no_input("Include a lunch break", default=False)
    lunch_length = 0
    if has_lunch:
        lunch_length = get_integer_input("Lunch break length in minutes", default=30, min_value=10)
    
    first_mtg_start = get_time_input("Start time of first meeting (HH:MM)", default="09:30")
    
    # Provide default output file path with option to change it
    default_output = "config/meeting_config.csv"
    custom_output = get_yes_no_input(f"Use default output path ({default_output})", default=True)
    output_file = default_output
    if not custom_output:
        output_file = input("Enter output file path: ").strip() or default_output
    
    # Generate meeting times
    meetings = generate_meeting_times(
        mtg_length,
        num_meetings,
        has_breaks,
        break_length,
        has_lunch,
        lunch_length,
        first_mtg_start
    )
    
    if not meetings:
        logger.error("Failed to generate meeting schedule. Please check your inputs.")
        return
    
    # Update CSV with schedule and mentor slots
    update_csv_with_schedule(meetings, output_file)
    
    # Display final schedule summary
    print("\nSchedule configuration completed successfully.")
    print(f"Meeting schedule has been saved to: {output_file}")
    last_meeting = meetings[-1]
    print(f"Schedule runs from {first_mtg_start} to {last_meeting['end']}")
    print(f"Total meetings: {num_meetings}")

if __name__ == "__main__":
    main() 