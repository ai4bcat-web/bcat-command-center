"""
Sales Service Orchestrator
Coordinates all sales workspace operations across Instantly, Apollo, Apify, GCal,
messaging, and recommendation services.
"""

import json, logging, os
from datetime import datetime, timezone
log = logging.getLogger(__name__)

_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'sales')

WORKSPACES = ['bcat_sales', 'bcat_recruitment', 'best_care_sales']

# ── Public API ─────────────────────────────────────────────────────────────────

def get_workspace_summary(workspace_id: str) -> dict:
    """Return high-level KPIs for the workspace overview card."""
    try:
        import sales_data as _sd
        return _sd.get_overview(workspace_id)
    except Exception as e:
        return {'error': str(e)}


def get_all_workspaces_summary() -> dict:
    try:
        import sales_data as _sd
        return _sd.get_workspaces_summary()
    except Exception as e:
        return {'error': str(e)}


# ── Email outreach ─────────────────────────────────────────────────────────────

def sync_instantly(workspace_id: str) -> dict:
    try:
        from services import instantly_service as _inst
        return _inst.sync(workspace_id)
    except ImportError:
        return {'ok': False, 'error': 'instantly_service not available', 'synced_at': None}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'synced_at': None}


def get_email_campaigns(workspace_id: str) -> dict:
    """Return email campaigns from Instantly cache or mock."""
    try:
        from services import instantly_service as _inst
        real_campaigns = _inst.get_campaigns(workspace_id)
        if real_campaigns:
            analytics = _inst.get_analytics(workspace_id)
            return {'ok': True, 'source': 'instantly', 'campaigns': real_campaigns, 'analytics': analytics}
    except Exception:
        pass
    try:
        import sales_data as _sd
        return {'ok': True, 'source': 'mock', 'campaigns': _sd.get_email_campaigns(workspace_id)}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'campaigns': []}


def enroll_leads_to_campaign(workspace_id: str, campaign_id: str, emails: list) -> dict:
    try:
        from services import instantly_service as _inst
        return _inst.enroll_leads(campaign_id, emails)
    except Exception as e:
        return {'ok': False, 'error': str(e)}


# ── Lead management ────────────────────────────────────────────────────────────

def sync_apollo(workspace_id: str, titles: list = None, industries: list = None,
                locations: list = None, company_sizes: list = None) -> dict:
    try:
        from services import apollo_service as _apo
        return _apo.search_contacts(workspace_id, titles=titles, industries=industries,
                                     locations=locations, company_sizes=company_sizes)
    except Exception as e:
        return {'ok': False, 'error': str(e), 'contacts': []}


def get_leads(workspace_id: str) -> dict:
    """Return leads from Apollo cache or mock."""
    try:
        from services import apollo_service as _apo
        real_leads = _apo.get_sync_status(workspace_id)
        if real_leads.get('leads_cached', 0) > 0:
            from data.sales import _read_cache
            data = _read_cache(workspace_id, 'apollo_leads')
            return {'ok': True, 'source': 'apollo', 'leads': data.get('contacts', [])}
    except Exception:
        pass
    try:
        import sales_data as _sd
        return {'ok': True, 'source': 'mock', 'leads': _sd.get_leads(workspace_id)}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'leads': []}


def enrich_lead(email: str) -> dict:
    try:
        from services import apollo_service as _apo
        return _apo.enrich_contact(email)
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def get_lead_lists(workspace_id: str) -> dict:
    try:
        import sales_data as _sd
        return {'ok': True, 'lists': _sd.get_lead_lists(workspace_id)}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'lists': []}


# ── LinkedIn / Apify ───────────────────────────────────────────────────────────

def scrape_linkedin(workspace_id: str, search_url: str, max_items: int = 200) -> dict:
    try:
        from services import apify_service as _apify
        return _apify.scrape_linkedin_contacts(workspace_id, search_url, max_items)
    except Exception as e:
        return {'ok': False, 'error': str(e), 'items': []}


def scrape_google_maps(workspace_id: str, query: str, location: str, max_items: int = 100) -> dict:
    try:
        from services import apify_service as _apify
        return _apify.scrape_google_maps(workspace_id, query, location, max_items)
    except Exception as e:
        return {'ok': False, 'error': str(e), 'items': []}


def get_linkedin_campaigns(workspace_id: str) -> dict:
    try:
        import sales_data as _sd
        return {'ok': True, 'campaigns': _sd.get_linkedin_campaigns(workspace_id)}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'campaigns': []}


def get_scraped_leads(workspace_id: str, source: str = None) -> dict:
    try:
        from services import apify_service as _apify
        leads = _apify.get_scraped_leads(workspace_id, source)
        return {'ok': True, 'leads': leads}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'leads': []}


# ── Meetings ───────────────────────────────────────────────────────────────────

def sync_calendar(workspace_id: str) -> dict:
    try:
        from services import gcal_service as _gcal
        return _gcal.sync(workspace_id)
    except Exception as e:
        return {'ok': False, 'error': str(e), 'synced_at': None}


def get_meetings(workspace_id: str) -> dict:
    """Return meetings from GCal cache or mock."""
    gcal_ok = False
    try:
        from services import gcal_service as _gcal
        status = _gcal.get_sync_status(workspace_id)
        if status.get('events_cached', 0) > 0:
            summary = _gcal.get_meetings_summary(workspace_id)
            return {'ok': True, 'source': 'gcal', **summary}
        gcal_ok = status.get('configured', False)
    except Exception:
        pass

    try:
        import sales_data as _sd
        meetings = _sd.get_meetings(workspace_id)
        return {'ok': True, 'source': 'mock', 'meetings': meetings,
                'gcal_configured': gcal_ok}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'meetings': []}


def get_upcoming_meetings(workspace_id: str, days: int = 7) -> dict:
    try:
        from services import gcal_service as _gcal
        events = _gcal.get_upcoming(workspace_id, days)
        return {'ok': True, 'source': 'gcal', 'meetings': events}
    except Exception:
        pass
    try:
        import sales_data as _sd
        all_meetings = _sd.get_meetings(workspace_id)
        return {'ok': True, 'source': 'mock', 'meetings': all_meetings[:5]}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'meetings': []}


# ── Messaging ─────────────────────────────────────────────────────────────────

def generate_message(workspace_id: str, style: str, channel: str, goal: str, variables: dict) -> dict:
    try:
        from services import messaging_service as _msg
        return _msg.generate_message(workspace_id, style, channel, goal, variables)
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def bulk_generate_messages(workspace_id: str, style: str, channel: str, goal: str,
                            leads: list, common_vars: dict = None) -> dict:
    try:
        from services import messaging_service as _msg
        results = _msg.bulk_generate(workspace_id, style, channel, goal, leads, common_vars)
        return {'ok': True, 'count': len(results), 'messages': results}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'messages': []}


def get_message_templates(workspace_id: str) -> dict:
    """Return template catalog for UI browser."""
    try:
        from services import messaging_service as _msg
        styles    = _msg.get_styles(workspace_id)
        catalog   = _msg.get_all_templates(workspace_id)
        mock_templates = []
        try:
            import sales_data as _sd
            mock_templates = _sd.get_message_templates(workspace_id)
        except Exception:
            pass
        return {'ok': True, 'styles': styles, 'catalog': catalog,
                'saved_templates': mock_templates}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


# ── Daily results ──────────────────────────────────────────────────────────────

def get_daily_results(workspace_id: str, days: int = 30) -> dict:
    try:
        import sales_data as _sd
        all_days = _sd.get_daily_results(workspace_id)
        return {'ok': True, 'days': all_days[-days:]}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'days': []}


# ── Recommendations ────────────────────────────────────────────────────────────

def generate_recommendations(workspace_id: str) -> dict:
    try:
        from services import sales_recommendation_service as _srec
        return _srec.generate(workspace_id)
    except Exception as e:
        return {'ok': False, 'error': str(e), 'recommendations': []}


def get_recommendations(workspace_id: str) -> dict:
    try:
        from services import sales_recommendation_service as _srec
        recs = _srec.get_recommendations(workspace_id)
        if recs:
            return {'ok': True, 'source': 'generated', 'recommendations': recs}
    except Exception:
        pass
    try:
        import sales_data as _sd
        return {'ok': True, 'source': 'mock', 'recommendations': _sd.get_recommendations(workspace_id)}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'recommendations': []}


def implement_recommendation(workspace_id: str, rec_id: str, notes: str = '') -> dict:
    try:
        from services import sales_recommendation_service as _srec
        return _srec.mark_implemented(workspace_id, rec_id, notes)
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def dismiss_recommendation(workspace_id: str, rec_id: str) -> dict:
    try:
        from services import sales_recommendation_service as _srec
        return _srec.mark_dismissed(workspace_id, rec_id)
    except Exception as e:
        return {'ok': False, 'error': str(e)}


# ── Activity log ───────────────────────────────────────────────────────────────

def get_activity_log(workspace_id: str) -> dict:
    try:
        import sales_data as _sd
        return {'ok': True, 'activity': _sd.get_activity_log(workspace_id)}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'activity': []}


# ── Sync status ────────────────────────────────────────────────────────────────

def get_sync_status(workspace_id: str) -> dict:
    status = {'workspace_id': workspace_id}

    try:
        from services import instantly_service as _inst
        status['instantly'] = _inst.get_sync_status(workspace_id)
    except Exception:
        status['instantly'] = {'configured': False, 'error': 'not available'}

    try:
        from services import apollo_service as _apo
        status['apollo'] = _apo.get_sync_status(workspace_id)
    except Exception:
        status['apollo'] = {'configured': False, 'error': 'not available'}

    try:
        from services import apify_service as _apify
        status['apify'] = _apify.get_sync_status(workspace_id)
    except Exception:
        status['apify'] = {'configured': False, 'error': 'not available'}

    try:
        from services import gcal_service as _gcal
        status['gcal'] = _gcal.get_sync_status(workspace_id)
    except Exception:
        status['gcal'] = {'configured': False, 'error': 'not available'}

    return status


def sync_all(workspace_id: str) -> dict:
    """Run all available syncs for a workspace."""
    results = {}
    results['instantly'] = sync_instantly(workspace_id)
    results['calendar']  = sync_calendar(workspace_id)
    # Apollo and Apify require parameters so not auto-synced
    return {'ok': True, 'workspace_id': workspace_id, 'results': results,
            'synced_at': datetime.now(timezone.utc).isoformat()}
