# Calendar Event Creator

This application creates Google Calendar events using data from Airtable.

## Setup

1. Create a Google Cloud Project and enable the Google Calendar API
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials and download the client configuration file as `credentials.json`

2. Set up Airtable
   - Create an Airtable base with the following fields:
     - event_title (Single line text)
     - start_time (DateTime)
     - end_time (DateTime)
     - description (Long text)
     - location (Single line text)
     - attendees (Multiple line text - one email per line)

3. Environment Variables
   Create a `.env` file with:
   ```
   AIRTABLE_API_KEY=your_airtable_api_key
   AIRTABLE_BASE_ID=your_base_id
   AIRTABLE_TABLE_NAME=your_table_name
   ```

4. Installation
   ```bash
   pip install -r requirements.txt
   ```

5. Running the Application
   ```bash
   python app.py
   ```

The first time you run the application, it will open a browser window for Google OAuth authentication. 

## Generating Mentor Descriptions

To generate personalized markdown files with meeting schedules for each mentor:

```bash
python generate_mentor_descriptions.py [--date YYYY-MM-DD] [--no-master]
```

This script reads the `meeting_schedule.csv` file and creates markdown files in the `descriptions` directory. Each file contains:
- A personalized welcome message
- The mentor's meeting schedule for the day
- Company names and meeting times

You can specify a date to generate descriptions for a specific day only. If no date is provided, descriptions for all dates will be generated.

The script also creates a master file for each date (`All_Mentors_YYYY-MM-DD.md`) that contains the schedules for all mentors on that day, sorted alphabetically. Use the `--no-master` flag to skip creating these master files.

Example usage:
```bash
# Generate for a specific date
python generate_mentor_descriptions.py --date 2025-03-24

# Generate for all dates without creating master files
python generate_mentor_descriptions.py --no-master
``` 