"""
Google Calendar Service
Pulls meeting bookings, tracks outcomes, and shows pipeline-to-calendar visibility.

Uses the same OAuth2 credentials.json as the Gmail service.
Requires CALENDAR scope to be added (see .env.example for setup notes).

Required env vars:
  GOOGLE_CALENDAR_ID   — calendar ID to watch (default: primary)
  SALES_CALENDAR_TAG   — optional tag/keyword to filter sales meetings

Google Calendar API docs:
  https://developers.google.com/calendar/api/v3/reference
"""

import json, logging, os
from datetime import datetime, timedelta, timezone
log = logging.getLogger(__name__)

_CACHE_DIR  = os.path.join(os.path.dirname(__file__), '..', 'data', 'sales')
_CREDS_PATH = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
_TOKEN_PATH = os.path.join(os.path.dirname(__file__), '..', 'gcal_token.json')

SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
]

def _calendar_id(): return os.getenv('GOOGLE_CALENDAR_ID', 'primary')
def _is_configured(): return os.path.exists(_CREDS_PATH)

# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_creds():
    """Load or refresh OAuth2 credentials for Calendar."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    if os.path.exists(_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(_TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(_CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(_TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
    return creds

def _get_service():
    from googleapiclient.discovery import build
    return build('calendar', 'v3', credentials=_get_creds())

# ── Public API ────────────────────────────────────────────────────────────────

def sync(workspace_id: str, days_back: int = 30, days_forward: int = 14) -> dict:
    """Pull events from Google Calendar and write to cache."""
    if not _is_configured():
        return {'ok': False, 'error': 'credentials.json not found. Run Gmail auth flow first.', 'synced_at': None}
    try:
        service  = _get_service()
        now      = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=days_back)).isoformat()
        time_max = (now + timedelta(days=days_forward)).isoformat()

        events_result = service.events().list(
            calendarId=_calendar_id(),
            timeMin=time_min, timeMax=time_max,
            singleEvents=True, orderBy='startTime',
            maxResults=250,
        ).execute()

        events = [_normalize_event(e) for e in events_result.get('items', [])]
        payload = {
            'synced_at':    now.isoformat(),
            'workspace_id': workspace_id,
            'calendar_id':  _calendar_id(),
            'events':       events,
        }
        _write_cache(workspace_id, 'gcal', payload)
        return {'ok': True, 'events': len(events), 'synced_at': payload['synced_at']}
    except ImportError:
        return {'ok': False, 'error': 'google-api-python-client not installed', 'synced_at': None}
    except Exception as e:
        log.exception('Google Calendar sync failed')
        return {'ok': False, 'error': str(e), 'synced_at': None}

def _normalize_event(event: dict) -> dict:
    start = event.get('start', {})
    end   = event.get('end', {})
    return {
        'id':          event.get('id', ''),
        'title':       event.get('summary', ''),
        'description': event.get('description', ''),
        'start':       start.get('dateTime') or start.get('date', ''),
        'end':         end.get('dateTime')   or end.get('date', ''),
        'attendees':   [a.get('email') for a in event.get('attendees', [])],
        'organizer':   event.get('organizer', {}).get('email', ''),
        'status':      event.get('status', ''),
        'link':        event.get('hangoutLink') or event.get('htmlLink', ''),
        'location':    event.get('location', ''),
    }

def get_events(workspace_id: str) -> list:
    return _read_cache(workspace_id, 'gcal').get('events', [])

def get_upcoming(workspace_id: str, days: int = 7) -> list:
    now    = datetime.now(timezone.utc)
    cutoff = (now + timedelta(days=days)).isoformat()
    return [
        e for e in get_events(workspace_id)
        if e['start'] >= now.isoformat() and e['start'] <= cutoff
    ]

def get_meetings_summary(workspace_id: str) -> dict:
    events = get_events(workspace_id)
    now    = datetime.now(timezone.utc).isoformat()
    today  = datetime.now(timezone.utc).date().isoformat()
    week_start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    month_start = datetime.now(timezone.utc).replace(day=1).isoformat()

    return {
        'total':          len(events),
        'upcoming':       sum(1 for e in events if e['start'] > now),
        'today':          sum(1 for e in events if e['start'].startswith(today)),
        'this_week':      sum(1 for e in events if week_start <= e['start'] <= now),
        'this_month':     sum(1 for e in events if month_start <= e['start'] <= now),
        'events':         events,
    }

def get_sync_status(workspace_id: str) -> dict:
    data = _read_cache(workspace_id, 'gcal')
    return {'configured': _is_configured(), 'synced_at': data.get('synced_at'),
            'events_cached': len(data.get('events', []))}

# ── Cache ─────────────────────────────────────────────────────────────────────
def _cache_path(ws, name): return os.path.abspath(os.path.join(_CACHE_DIR, ws, f'{name}.json'))
def _read_cache(ws, name):
    p = _cache_path(ws, name)
    if not os.path.exists(p): return {}
    try:
        with open(p) as f: return json.load(f)
    except Exception: return {}
def _write_cache(ws, name, data):
    p = _cache_path(ws, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f: json.dump(data, f, indent=2)
