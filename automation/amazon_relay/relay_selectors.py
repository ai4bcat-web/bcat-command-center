"""
automation/amazon_relay/selectors.py

All Playwright selectors in one place.  If Amazon changes the UI, update here only.

Selector priority used throughout:
  1. Stable ARIA role / label  (most resilient to HTML changes)
  2. Known id/name attributes  (Amazon SSO ids are very stable)
  3. Text-content match        (readable, survives class renames)
  4. CSS selector              (last resort)

How to re-inspect if selectors break:
  1. Run the fetcher in headed mode: RELAY_HEADLESS=false
  2. A screenshot is saved to downloads/ on every failure
  3. Open relay.amazon.com manually, open DevTools, inspect the element
  4. Update the relevant constant below and re-run
"""

# ── Amazon Relay homepage (marketing landing page shown before login) ─────
# relay.amazon.com shows a public page first; must click Sign in to reach the form.
HOMEPAGE_SIGNIN_BUTTON  = (
    "a:has-text('Sign in'), "
    "button:has-text('Sign in'), "
    "a[href*='signin'], "
    "a[href*='login'], "
    "nav a:has-text('Sign'), "
    "[data-testid*='signin'], "
    "[data-csa-c-content-id*='sign']"
)

# ── Amazon SSO login page ──────────────────────────────────────────────────
# These ids are shared across all Amazon properties and are very stable.
LOGIN_EMAIL_INPUT       = "#ap_email"
LOGIN_EMAIL_SUBMIT      = "#continue"          # "Continue" button after email
LOGIN_PASSWORD_INPUT    = "#ap_password"
LOGIN_PASSWORD_SUBMIT   = "#signInSubmit"      # "Sign in" button

# MFA / OTP page — Amazon uses these for authenticator-app or SMS codes
MFA_OTP_INPUT           = "#auth-mfa-otpcode"
MFA_OTP_SUBMIT          = "#auth-signin-button"
# Fallback text match if the id ever changes
MFA_OTP_INPUT_FALLBACK  = "input[name='otpCode'], input[type='tel'], input[autocomplete='one-time-code']"

# ── Post-login interstitials ──────────────────────────────────────────────
# A "Give Feedback" modal appears on the first page load after login.
# Dismiss it by clicking Cancel before attempting any navigation.
# Multiple close targets tried in order; first match wins.
FEEDBACK_MODAL_DISMISS  = "button:has-text('Cancel')"   # inside the feedback form widget

# ── Amazon Relay navigation (confirmed via live DOM inspection) ───────────
#
# Trips → /tours/upcoming   (NOT /trips — that 404s)
# History tab → button with text "History" inside the tours page
# Navigating to /tours/ redirects to /tours/upcoming; clicking History
# tab updates the URL to /tours/history.

RELAY_TRIPS_URL         = "https://relay.amazon.com/tours/"   # redirects to /tours/upcoming
TRIPS_HISTORY_URL_PART  = "/tours"          # URL substring confirming we're on the trips section
TRIPS_HISTORY_PAGE_URL  = "/tours/history"  # exact path after clicking the History tab

# The History tab is a <button>, not an <a> tag.
NAV_HISTORY_TAB         = "button:has-text('History')"

# ── Date range filter on History tab ─────────────────────────────────────
# Amazon Relay History shows a date range picker above the trip table.
# Selectors are tried in order; first match wins.
#
# If these break, run with RELAY_HEADLESS=false — the fetcher logs all
# visible buttons/inputs/selects to help identify the right selectors.
DATE_FILTER_BUTTON      = (
    "button:has-text('Date range'), "
    "button:has-text('Filter by date'), "
    "button:has-text('Week'), "
    "[aria-label*='date range' i], "
    "[aria-label*='filter' i]"
)
DATE_START_INPUT        = (
    "input[aria-label*='start' i], "
    "input[placeholder*='start' i], "
    "input[name*='start' i], "
    "input[aria-label*='from' i], "
    "input[placeholder*='from' i], "
    "input[type='date']:first-of-type"
)
DATE_END_INPUT          = (
    "input[aria-label*='end' i], "
    "input[placeholder*='end' i], "
    "input[name*='end' i], "
    "input[aria-label*='to' i], "
    "input[placeholder*='to' i], "
    "input[type='date']:last-of-type"
)
DATE_APPLY_BUTTON       = (
    "button:has-text('Apply'), "
    "button:has-text('Search'), "
    "button:has-text('Update'), "
    "button:has-text('Go')"
)
DATE_THIS_WEEK          = (
    "button:has-text('This week'), "
    "li:has-text('This week'), "
    "option:has-text('This week'), "
    "[aria-label*='this week' i]"
)

# ── Export control (confirmed as a direct-download <button>) ─────────────
# Clicking Export on /tours/history triggers an immediate file download —
# no modal or format-chooser appears.
EXPORT_BUTTON           = "button:has-text('Export')"

# ── Page-ready signal for history view ───────────────────────────────────
# After clicking History and waiting, at least one of these will be present.
HISTORY_PAGE_READY      = (
    "button:has-text('Export'), "      # Export button visible
    "button:has-text('History'), "     # History tab rendered
    "text=No trip to show, "           # empty-state message (valid — page loaded)
    "text=Trip ID"                     # column header in results table
)

# ── URLs ──────────────────────────────────────────────────────────────────
RELAY_BASE_URL          = "https://relay.amazon.com"
RELAY_LOGIN_URL         = "https://relay.amazon.com"   # root redirects to login if unauthenticated

# ── Timeouts (milliseconds) ───────────────────────────────────────────────
NAV_TIMEOUT_MS          = 30_000    # page navigation
ELEMENT_TIMEOUT_MS      = 15_000    # waiting for a selector
DOWNLOAD_TIMEOUT_MS     = 60_000    # waiting for file download to complete
MFA_WAIT_TIMEOUT_MS     = 180_000   # 3 min for human to solve CAPTCHA / MFA
