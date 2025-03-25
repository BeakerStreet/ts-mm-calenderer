"""
Configuration file for meeting-related constants and settings.
"""

# Meeting duration in minutes
MEETING_DURATION = 15

# Meeting slots configuration
MEETING_SLOTS = {
    'morning': {
        'start_time': '09:30',
        'end_time': '11:55',
        'break_duration': 5,  # minutes between meetings
    },
    'afternoon': {
        'start_time': '12:15',
        'end_time': '13:40',
        'break_duration': 5,  # minutes between meetings
    }
}

# Companies and their founder emails
COMPANIES = {
    'Alethica': {
        'emails': 'faisal.ghaffar@alethica.com, aurelia.lefrapper@alethica.com'
    },
    'Ovida': {
        'emails': 'alex@ovida.io'
    },
    'Renn': {
        'emails': 'matan@getrenn.com, nleinov@gmail.com'
    },
    'PrettyData': {
        'emails': 'bww@prettydata.co'
    },
    'Tova': {
        'emails': 'alexa@tova.earth'
    },
    'Solim Health': {
        'emails': 'basnetabhaya@gmail.com, tonyelvis-steven@hotmail.com'
    },
    'Parasol': {
        'emails': 'Kasparharsaae@parasolplatforms.com, momirzan@parasolplatforms.com'
    }
}

# Airtable configuration
AIRTABLE_CONFIG = {
    'base_id': None,  # Will be loaded from environment
    'table_id': 'tbllbtrlfcmReNxQR',
    'token': None,  # Will be loaded from environment
}

# Output paths
OUTPUT_PATHS = {
    'descriptions': 'output/descriptions',
    'summaries': 'output/summaries',
    'backups': 'output/backups',
    'schedule': 'output/meeting_schedule.csv'
} 