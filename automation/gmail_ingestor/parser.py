"""
automation/gmail_ingestor/parser.py

Parses Amazon Relay trip booking emails to extract structured trip data.

Subject pattern:  "Load Board - Trip <TRIP_ID> booked"
Body:             Plain-text email with labelled fields (varies by Amazon template).

Public API:
  parse_trip_email(subject, body, message_id, received_at) -> TripEmailData
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

log = logging.getLogger("gmail_ingestor.parser")

# Regex for Amazon trip IDs (e.g. T-114MKFP5V or 114MKFP5V)
TRIP_ID_RE = re.compile(r'\b(?:T-)?([A-Z0-9]{8,12})\b')

# Subject must contain one of these to be considered a trip booking
BOOKING_SUBJECT_KEYWORDS = ["load board", "trip", "booked", "booking"]


@dataclass
class TripEmailData:
    message_id:       str
    subject:          str
    received_at:      datetime | None

    # Parsed fields
    trip_id:          str           = ""
    estimated_payout: float | None  = None
    origin:           str           = ""
    destination:      str           = ""
    pickup_dt:        str           = ""
    dropoff_dt:       str           = ""
    driver:           str           = ""
    rate:             str           = ""
    miles:            str           = ""
    raw_snippet:      str           = ""    # first 600 chars of body for debugging

    # Parse quality
    parse_confidence: str           = "high"   # 'high' | 'partial' | 'failed'
    parse_notes:      list[str]     = field(default_factory=list)


def is_trip_booking_email(subject: str) -> bool:
    """Return True if this subject line looks like a trip booking notification."""
    s = subject.lower()
    return any(kw in s for kw in BOOKING_SUBJECT_KEYWORDS)


def parse_trip_email(
    subject:     str,
    body:        str,
    message_id:  str,
    received_at: datetime | None,
) -> TripEmailData:
    """
    Parse a trip booking email into structured data.

    Strategy:
      1. Extract trip ID from subject (most reliable) then body.
      2. Extract estimated payout from body (highest priority field).
      3. Extract origin / destination.
      4. Extract pickup / dropoff date-times.
      5. Extract driver name, rate, miles if present.

    Sets parse_confidence:
      'high'    — trip_id and estimated_payout both found
      'partial' — one or more fields missing but trip_id found
      'failed'  — trip_id not found
    """
    data = TripEmailData(
        message_id  = message_id,
        subject     = subject,
        received_at = received_at,
        raw_snippet = body[:600],
    )

    # ── Trip ID ───────────────────────────────────────────────────────────────
    data.trip_id = _extract_trip_id(subject, body)
    if not data.trip_id:
        data.parse_confidence = "failed"
        data.parse_notes.append("trip_id not found in subject or body")
        log.warning("parse_trip_email: trip_id not found | msg=%s subject=%r", message_id, subject)
        return data

    # ── Estimated payout ──────────────────────────────────────────────────────
    data.estimated_payout = _extract_payout(body)
    if data.estimated_payout is None:
        data.parse_notes.append("estimated_payout not found")
        log.debug("parse_trip_email: payout not found | trip=%s", data.trip_id)

    # ── Origin / destination ──────────────────────────────────────────────────
    data.origin, data.destination = _extract_origin_destination(body)

    # ── Pickup / dropoff times ────────────────────────────────────────────────
    data.pickup_dt, data.dropoff_dt = _extract_datetimes(body)

    # ── Driver ────────────────────────────────────────────────────────────────
    data.driver = _extract_field(body, [r"driver[:\s]+([A-Za-z ]+)", r"assigned to[:\s]+([A-Za-z ]+)"])

    # ── Rate / miles ──────────────────────────────────────────────────────────
    data.rate  = _extract_field(body, [r"rate[:\s]+(\$?[\d,\.]+(?:/mi(?:le)?)?)", r"pay[:\s]+(\$?[\d,\.]+)"])
    data.miles = _extract_field(body, [r"(\d[\d,\.]*)\s*miles?", r"distance[:\s]+([\d,\.]+)"])

    # ── Confidence ────────────────────────────────────────────────────────────
    if data.estimated_payout is not None:
        data.parse_confidence = "high"
    else:
        data.parse_confidence = "partial"

    log.info(
        "Parsed trip email | trip=%s payout=%s origin=%r dest=%r confidence=%s",
        data.trip_id, data.estimated_payout, data.origin, data.destination, data.parse_confidence,
    )
    return data


# ── Field extractors ──────────────────────────────────────────────────────────

def _extract_trip_id(subject: str, body: str) -> str:
    """
    Extract trip ID from subject line first (most reliable), then body.
    Subject pattern:  "Load Board - Trip 114MKFP5V booked"
    Also handles:     "Trip T-114MKFP5V has been booked"
    """
    # Try subject first — pull the longest alphanumeric token that follows "Trip"
    subject_match = re.search(
        r'[Tt]rip\s+(?:ID\s*[:=]?\s*)?(?:T-)?([A-Z0-9]{6,12})',
        subject, re.IGNORECASE
    )
    if subject_match:
        return subject_match.group(1).upper()

    # Try common body patterns
    body_patterns = [
        r'[Tt]rip\s+ID\s*[:=]?\s*(?:T-)?([A-Z0-9]{6,12})',
        r'[Tt]rip\s*#?\s*(?:T-)?([A-Z0-9]{6,12})',
        r'\bID[:\s]+(?:T-)?([A-Z0-9]{6,12})',
    ]
    for pattern in body_patterns:
        m = re.search(pattern, body, re.IGNORECASE)
        if m:
            return m.group(1).upper()

    # Fallback: find any token matching the Amazon trip ID format (7-10 uppercase alphanumeric)
    # in subject or body — look for ones adjacent to "trip" word
    for text in (subject, body[:1000]):
        m = re.search(r'\b([A-Z0-9]{7,10})\b', text)
        if m:
            candidate = m.group(1)
            # Sanity: not purely numeric, not common words
            if not candidate.isdigit() and not candidate.isalpha():
                return candidate

    return ""


def _extract_payout(body: str) -> float | None:
    """
    Extract estimated payout dollar amount.

    Tries patterns in order of confidence:
      "Estimated Cost: $123.45"
      "Payout: $123.45"
      "Pay: $123.45"
      "$123.45" near payout-adjacent keywords
    """
    high_confidence_patterns = [
        r'[Ee]stimated\s+(?:[Cc]ost|[Pp]ay(?:out)?|[Rr]evenue)\s*[:=]?\s*\$?\s*([\d,]+\.?\d*)',
        r'[Pp]ayout\s*[:=]?\s*\$?\s*([\d,]+\.?\d*)',
        r'[Pp]ay\s*[:=]?\s*\$?\s*([\d,]+\.?\d*)',
        r'[Ee]arning[s]?\s*[:=]?\s*\$?\s*([\d,]+\.?\d*)',
        r'[Cc]ost\s*[:=]?\s*\$?\s*([\d,]+\.?\d*)',
        r'[Aa]mount\s*[:=]?\s*\$?\s*([\d,]+\.?\d*)',
        r'[Rr]ate\s*[:=]?\s*\$?\s*([\d,]+\.?\d*)',
        r'\$\s*([\d,]+\.\d{2})',   # bare dollar amount with cents
    ]
    for pattern in high_confidence_patterns:
        m = re.search(pattern, body)
        if m:
            raw = m.group(1).replace(",", "")
            try:
                val = float(raw)
                if 10 < val < 100_000:   # sanity bounds
                    return val
            except ValueError:
                continue
    return None


def _extract_origin_destination(body: str) -> tuple[str, str]:
    """Extract origin and destination from email body."""
    origin = ""
    destination = ""

    # Patterns: "From: City, ST" / "Origin: City, ST" / "Pickup: City"
    orig_m = re.search(
        r'(?:[Ff]rom|[Oo]rigin|[Pp]ick[\s-]?up\s*(?:[Ll]ocation)?)\s*[:=]?\s*([A-Za-z ,\.]+?)(?:\n|,\s*[A-Z]{2}|\|)',
        body
    )
    if orig_m:
        origin = orig_m.group(1).strip().rstrip(",")

    # Patterns: "To: City, ST" / "Destination: City" / "Delivery: City"
    dest_m = re.search(
        r'(?:[Tt]o|[Dd]estination|[Dd]elivery\s*(?:[Ll]ocation)?|[Dd]rop[\s-]?off)\s*[:=]?\s*([A-Za-z ,\.]+?)(?:\n|,\s*[A-Z]{2}|\|)',
        body
    )
    if dest_m:
        destination = dest_m.group(1).strip().rstrip(",")

    return origin[:200], destination[:200]


def _extract_datetimes(body: str) -> tuple[str, str]:
    """Extract pickup and dropoff datetime strings."""
    pickup  = ""
    dropoff = ""

    # Common patterns: "Pickup: Mon, Apr 7 at 8:00 AM"
    pu_m = re.search(
        r'(?:[Pp]ick[\s-]?up|[Ss]tart|[Dd]eparture)\s*(?:[Dd]ate)?[:\s]+([^\n]{5,50})',
        body
    )
    if pu_m:
        pickup = pu_m.group(1).strip()[:100]

    do_m = re.search(
        r'(?:[Dd]rop[\s-]?off|[Dd]elivery|[Aa]rrival|[Ee]nd)\s*(?:[Dd]ate)?[:\s]+([^\n]{5,50})',
        body
    )
    if do_m:
        dropoff = do_m.group(1).strip()[:100]

    return pickup, dropoff


def _extract_field(body: str, patterns: list[str]) -> str:
    """Try a list of patterns, return first match cleaned up."""
    for pattern in patterns:
        m = re.search(pattern, body, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:200]
    return ""
