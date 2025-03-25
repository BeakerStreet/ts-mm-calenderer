# Techstars Mentor Magic Calenderer

A tool for scheduling Mentor Magic meetings and generating calendar events, mentor descriptions, and daily summaries.

## Overview

This application helps schedule Mentor Magic sessions by:
1. Loading mentor data from Airtable
2. Generating meeting schedules
3. Creating personalized mentor descriptions
4. Producing daily meeting summaries
5. Adding events to Google Calendar

## Setup

### Prerequisites

- Python 3.7+
- Airtable account with mentor data
- Google Calendar API credentials

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/BeakerStreet/ts-mm-calenderer.git
   cd ts-mm-calenderer
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Create a `.env` file in the project root:
     ```
     AIRTABLE_API_KEY=your_api_key
     AIRTABLE_BASE_ID=your_base_id
     AIRTABLE_MENTOR_TABLE=your_mentors_table_name
     ```

5. Add Google Calendar credentials:
   - Create a Google Cloud project and enable Calendar API
   - Download the credentials.json file and place it in the project root

## Usage

### 1. Refresh Mentor Data

Pull the latest mentor data from Airtable:

```
python config/refresh_mentors.py
```

Filter by date:
```
python config/refresh_mentors.py --date 2025-03-26
```

### 2. Generate Meeting Schedule

Create a meeting schedule for a specific date:

```
python src/app.py --date 2025-03-26
```

This will:
- Generate a meeting schedule in `output/meeting_schedule.csv`
- Create mentor descriptions in `output/descriptions/`
- Create daily meeting summaries in `output/daily_summaries/`

### 3. Add Events to Google Calendar

Add meetings to Google Calendar:

```
python src/add_to_gcal.py --date 2025-03-26
```

Run in test mode (no attendees added to calendar events):
```
python src/add_to_gcal.py --date 2025-03-26 --test
```

Note: By default, calendar events will not send notifications to attendees.

## Output Files

- `output/meeting_schedule.csv`: Complete meeting schedule
- `output/descriptions/`: Mentor-specific meeting schedules in markdown format
- `output/daily_summaries/`: Daily meeting summaries in CSV format
- `output/backups/`: Timestamped backups of meeting schedules

## Directory Structure

```
ts-mm-calenderer/
├── config/               # Configuration files
│   ├── companies.csv     # List of participating companies
│   ├── meeting_config.csv # Meeting time slots configuration
│   ├── mentors.csv       # Mentor data (from Airtable)
│   └── refresh_mentors.py # Script to update mentors from Airtable
├── output/               # Generated files
│   ├── backups/          # Schedule backups
│   ├── descriptions/     # Mentor descriptions
│   ├── daily_summaries/  # Daily meeting summaries
│   └── meeting_schedule.csv # Main schedule file
└── src/                 # Application source code
    ├── app.py           # Main application script
    ├── add_to_gcal.py   # Calendar integration
    ├── day_summary.py   # Generate daily summaries
    └── mentor_text.py   # Generate mentor descriptions
```

## Customization

- Edit `config/companies.csv` to update the list of companies
- Edit `config/meeting_config.csv` to change meeting time slots
- Use `config/configure_schedule.py` to customize meeting configurations

## Generate Mentor Descriptions Only

If you already have a meeting schedule and only want to generate mentor descriptions:

```
python src/mentor_text.py --date 2025-03-26
```

Each mentor will receive a personalized markdown file with their meeting schedule. The descriptions include:
- Welcome message with mentor name
- Date and schedule of meetings
- Company names and meeting times
- Lookbook information link
- Thank you message

## Generate Daily Summaries Only

If you want to generate daily summaries (CSV tables showing all meetings for a day):

```
python src/day_summary.py --date 2025-03-26
```

This creates a CSV file with:
- Rows for each mentor
- Columns for each time slot
- Company names in the cells where meetings are scheduled 