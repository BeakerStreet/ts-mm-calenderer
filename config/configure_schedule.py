#!/usr/bin/env python3
"""
Configuration utility for meeting schedules.
Allows users to input meeting parameters and updates CSV headers with calculated meeting times.
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import argparse
import logging
import random

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
        sys.exit(1)

def generate_meeting_times(
    mtg_length, 
    num_meetings, 
    has_breaks, 
    break_length, 
    has_lunch, 
    lunch_length, 
    first_mtg_start, 
    last_mtg_end
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
        last_mtg_end (str): End time of last meeting (HH:MM)
        
    Returns:
        list: List of dictionaries with meeting info
    """
    # Parse time strings to datetime objects
    start_time = parse_time(first_mtg_start)
    end_time_limit = parse_time(last_mtg_end)
    
    # Set the date to today (we only care about time)
    today = datetime.today().date()
    start_time = datetime.combine(today, start_time.time())
    end_time_limit = datetime.combine(today, end_time_limit.time())
    
    meetings = []
    current_time = start_time
    meeting_count = 0
    
    while meeting_count < num_meetings and current_time < end_time_limit:
        meeting_end = current_time + timedelta(minutes=mtg_length)
        
        # Check if this meeting would exceed the end time limit
        if meeting_end > end_time_limit:
            logger.warning(f"Cannot fit {num_meetings} meetings with the given parameters.")
            break
        
        meetings.append({
            "start": current_time.strftime("%H:%M"),
            "end": meeting_end.strftime("%H:%M"),
            "header": f"{current_time.strftime('%H:%M')}-{meeting_end.strftime('%H:%M')}"
        })
        
        meeting_count += 1
        
        # Add break time if applicable
        if has_breaks:
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

def main():
    parser = argparse.ArgumentParser(description="Configure meeting schedule parameters")
    
    parser.add_argument("--mtg_length", type=int, help="Length of each meeting in minutes", default=15)
    parser.add_argument("--num_meetings", type=int, help="Number of meetings", default=8)
    parser.add_argument("--breaks", action="store_true", help="Include breaks between meetings")
    parser.add_argument("--break_length", type=int, help="Length of breaks in minutes", default=5)
    parser.add_argument("--lunch", action="store_true", help="Include a lunch break")
    parser.add_argument("--lunch_length", type=int, help="Length of lunch break in minutes", default=30)
    parser.add_argument("--first_mtg_start", type=str, help="Start time of first meeting (HH:MM)", default="09:30")
    parser.add_argument("--last_mtg_end", type=str, help="End time of last meeting (HH:MM)", default="13:40")
    parser.add_argument("--output", type=str, help="Output file path", default="config/meeting_config.csv")
    
    args = parser.parse_args()
    
    # Generate meeting times
    meetings = generate_meeting_times(
        args.mtg_length,
        args.num_meetings,
        args.breaks,
        args.break_length,
        args.lunch,
        args.lunch_length,
        args.first_mtg_start,
        args.last_mtg_end
    )
    
    # Update CSV with schedule and mentor slots
    update_csv_with_schedule(meetings, args.output)
    
    # Also output app.py configuration values for manual update
    logger.info("\nTo update app.py with these settings, use the following values:")
    logger.info(f"MEETING_DURATION = {args.mtg_length}")
    logger.info(f"FIRST_MTG_START = '{args.first_mtg_start}'")
    logger.info(f"LAST_MTG_END = '{args.last_mtg_end}'")
    logger.info(f"LUNCH = {args.lunch}")
    if args.lunch:
        lunch_start = parse_time(args.first_mtg_start)
        for i in range(args.num_meetings // 2):
            lunch_start = lunch_start + timedelta(minutes=args.mtg_length)
            if args.breaks and i < args.num_meetings // 2 - 1:
                lunch_start = lunch_start + timedelta(minutes=args.break_length)
        
        logger.info(f"LUNCH_START = '{lunch_start.strftime('%H:%M')}'")
        lunch_end = lunch_start + timedelta(minutes=args.lunch_length)
        logger.info(f"LUNCH_END = '{lunch_end.strftime('%H:%M')}'")
    
if __name__ == "__main__":
    main() 