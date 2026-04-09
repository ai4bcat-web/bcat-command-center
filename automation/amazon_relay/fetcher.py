"""
automation/amazon_relay/fetcher.py

Playwright-based login and CSV download for Amazon Relay.

Environment variables (all read from .env via python-dotenv):
  AMAZON_RELAY_EMAIL       — login email (required)
  AMAZON_RELAY_PASSWORD    — login password (required)
  RELAY_PROFILE_PATH       — persistent Chromium profile directory (optional)
                             default: automation/amazon_relay/.browser_profile/
                             The profile stores cookies, localStorage, and browser
                             fingerprint so Amazon recognises the same "user" on
                             every run and rarely forces re-authentication.
  RELAY_DOWNLOAD_PATH      — where to save downloaded CSV (optional)
                             default: automation/amazon_relay/downloads/
  RELAY_HEADLESS           — "false" to watch the browser (default: "true")

First-time setup:
  Run once in headed mode to log in and save the profile:
    RELAY_HEADLESS=false python automation/amazon_relay/run_once.py
  All subsequent runs will reuse the saved profile and skip the login page.

Usage:
  from automation.amazon_relay.fetcher import fetch_relay_csv
  result = asyncio.run(fetch_relay_csv())
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ── path setup ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ── local imports ─────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
import relay_selectors as SEL

# ── logging ───────────────────────────────────────────────────────────────
log = logging.getLogger("amazon_relay.fetcher")

# ── config from env ───────────────────────────────────────────────────────
RELAY_EMAIL    = os.getenv("AMAZON_RELAY_EMAIL", "")
RELAY_PASSWORD = os.getenv("AMAZON_RELAY_PASSWORD", "")

_HERE          = Path(__file__).resolve().parent
PROFILE_PATH   = Path(os.getenv("RELAY_PROFILE_PATH",
                       str(_HERE / ".browser_profile")))
DOWNLOAD_PATH  = Path(os.getenv("RELAY_DOWNLOAD_PATH",
                       str(_HERE / "downloads")))
HEADLESS       = os.getenv("RELAY_HEADLESS", "true").lower() != "false"

MAX_RETRIES    = 3


# ── helpers ───────────────────────────────────────────────────────────────

def _screenshot_path(label: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    p  = DOWNLOAD_PATH / f"debug_{label}_{ts}.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


async def _safe_screenshot(page, label: str) -> None:
    try:
        await page.screenshot(path=_screenshot_path(label), full_page=True)
        log.warning(f"Screenshot saved: debug_{label}_*.png in {DOWNLOAD_PATH}")
    except Exception as e:
        log.debug(f"Could not save screenshot: {e}")


async def _wait_for_any(page, selectors_str: str, timeout_ms: int):
    """Try each comma-separated selector; return the first that resolves."""
    for sel in [s.strip() for s in selectors_str.split(",") if s.strip()]:
        try:
            el = await page.wait_for_selector(sel, timeout=timeout_ms // len(selectors_str.split(",")))
            if el:
                return el
        except PlaywrightTimeout:
            continue
    raise PlaywrightTimeout(f"None of the selectors found within {timeout_ms}ms: {selectors_str}")


# ── login flow ────────────────────────────────────────────────────────────

async def _is_logged_in(page) -> bool:
    """Returns True if the current page looks like an authenticated Relay page."""
    url  = page.url
    html = await page.content()
    return (
        "relay.amazon.com" in url
        and "ap_email" not in html        # login form not present
        and "ap_password" not in html
        and "sign-in" not in url.lower()
    )


async def _needs_human_intervention(page) -> bool:
    """Returns True if the page is showing a CAPTCHA, MFA, or any other human challenge."""
    try:
        html = await page.content()
        url  = page.url.lower()
        return any([
            "solve this puzzle"   in html.lower(),
            "verify your identity" in html.lower(),
            "otpCode"             in html,
            "auth-mfa"            in html,
            "mfa"                 in url,
            "verification"        in url,
            "captcha"             in url,
            "challenge"           in url,
        ])
    except Exception:
        return False


async def _handle_human_challenge(page) -> None:
    """
    Pauses and waits for the user to solve a CAPTCHA, MFA, or other challenge.

    The browser MUST be visible: run with RELAY_HEADLESS=false.
    Once the challenge is solved the automation continues automatically.
    The session is then saved so future runs will not hit this page.

    Raises RuntimeError if the challenge is not cleared within 3 minutes.
    """
    if HEADLESS:
        await _safe_screenshot(page, "captcha_or_mfa_blocked")
        raise RuntimeError(
            "Amazon is showing a CAPTCHA or MFA challenge — cannot solve in headless mode.\n"
            "Run once in headed mode to solve it manually, then the session will be saved:\n"
            "  RELAY_HEADLESS=false python automation/amazon_relay/run_once.py"
        )

    log.warning(
        "⚠  Human challenge detected (CAPTCHA / MFA / verification).\n"
        "   Solve it in the browser window now.\n"
        f"  Waiting up to {SEL.MFA_WAIT_TIMEOUT_MS // 1000}s for you to complete it …"
    )

    # Poll until the challenge page is gone
    deadline_ms = SEL.MFA_WAIT_TIMEOUT_MS
    poll_ms     = 3_000
    elapsed     = 0
    while elapsed < deadline_ms:
        await page.wait_for_timeout(poll_ms)
        elapsed += poll_ms
        if not await _needs_human_intervention(page):
            log.info("Challenge cleared — continuing.")
            return

    await _safe_screenshot(page, "challenge_timeout")
    raise RuntimeError(
        f"Challenge not completed within {SEL.MFA_WAIT_TIMEOUT_MS // 1000}s."
    )


async def _login(page) -> None:
    """Perform full Amazon SSO login."""
    if not RELAY_EMAIL or not RELAY_PASSWORD:
        raise RuntimeError(
            "AMAZON_RELAY_EMAIL and AMAZON_RELAY_PASSWORD must be set in .env"
        )

    log.info("Starting login flow …")
    await page.goto(SEL.RELAY_LOGIN_URL, wait_until="domcontentloaded",
                    timeout=SEL.NAV_TIMEOUT_MS)
    # Wait for JS to render the nav
    await page.wait_for_timeout(3_000)

    # ── Step 0: navigate to Amazon SSO sign-in page ───────────────────────
    # relay.amazon.com shows a marketing page first. The "Sign in" link in
    # the top nav points to amazon.com/ap/signin with a return_to redirect.
    # We extract the href directly (avoiding the invisible duplicate in the
    # mobile nav that Playwright picks up first) and navigate to it.
    page_html = await page.content()
    if "ap_email" not in page_html and "ap_password" not in page_html:
        try:
            # Get the href from the VISIBLE Sign in link (last match = desktop nav)
            sign_in_url = await page.evaluate("""() => {
                const links = [...document.querySelectorAll('a')];
                const visible = links.filter(a =>
                    a.innerText.trim() === 'Sign in' && a.offsetParent !== null
                );
                return visible.length ? visible[visible.length - 1].href : null;
            }""")
            if sign_in_url:
                await page.goto(sign_in_url, wait_until="domcontentloaded",
                                timeout=SEL.NAV_TIMEOUT_MS)
                log.info("Navigated to Amazon SSO sign-in page.")
            else:
                log.info("Sign in link not found on landing page — may already be on login form.")
        except Exception as e:
            log.info(f"Could not navigate to sign-in page: {e}")

    # ── Step 1: email ──────────────────────────────────────────────────────
    try:
        email_input = await page.wait_for_selector(
            SEL.LOGIN_EMAIL_INPUT, timeout=SEL.ELEMENT_TIMEOUT_MS
        )
        await email_input.fill(RELAY_EMAIL)
        await page.click(SEL.LOGIN_EMAIL_SUBMIT)
        log.info("Email submitted.")
    except PlaywrightTimeout:
        await _safe_screenshot(page, "login_email_not_found")
        raise RuntimeError("Login page email field not found — Amazon may have changed the UI.")

    # ── Step 2: password ───────────────────────────────────────────────────
    try:
        pw_input = await page.wait_for_selector(
            SEL.LOGIN_PASSWORD_INPUT, timeout=SEL.ELEMENT_TIMEOUT_MS
        )
        await pw_input.fill(RELAY_PASSWORD)
        await page.click(SEL.LOGIN_PASSWORD_SUBMIT)
        log.info("Password submitted.")
    except PlaywrightTimeout:
        await _safe_screenshot(page, "login_password_not_found")
        raise RuntimeError("Password field not found after email step.")

    # ── Step 3: CAPTCHA / MFA / verification (any human challenge) ───────
    await page.wait_for_load_state("domcontentloaded")
    if await _needs_human_intervention(page):
        await _handle_human_challenge(page)

    # ── Step 4: confirm we're logged in ───────────────────────────────────
    await page.wait_for_timeout(2_000)
    if not await _is_logged_in(page):
        await _safe_screenshot(page, "login_failed")
        raise RuntimeError(
            "Login did not succeed.\n"
            "Most likely cause: Amazon showed a CAPTCHA or MFA challenge.\n"
            "Fix: run with RELAY_HEADLESS=false to solve it manually:\n"
            "  RELAY_HEADLESS=false python automation/amazon_relay/run_once.py\n"
            "The session will be saved and future runs will be unattended."
        )

    log.info("Login successful.")


# ── session management ────────────────────────────────────────────────────
# Two session strategies depending on environment:
#
#   Local (no DATABASE_URL):
#     Uses Playwright's persistent context with a filesystem profile directory.
#     Stores cookies, localStorage, and browser fingerprint on disk.
#     Run once headed to log in; all subsequent runs reuse the saved profile.
#
#   Railway (DATABASE_URL set):
#     Uses a regular browser context + cookies loaded from the relay_sessions
#     PostgreSQL table.  After each successful login the cookies are saved back
#     to the DB so they survive container restarts and redeploys.
#
# No code change is needed to switch modes — the presence of DATABASE_URL
# selects the strategy automatically.

import json as _json

_DB_SESSION = bool(os.getenv("DATABASE_URL", "").strip())


def _load_cookies_from_db() -> list:
    """Load saved cookies from relay_sessions table. Returns [] if unavailable."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from models import RelaySession
        from dashboard import app as _app
        with _app.app_context():
            row = RelaySession.query.order_by(RelaySession.saved_at.desc()).first()
            if row and row.cookies_json:
                cookies = _json.loads(row.cookies_json)
                log.info(f"Loaded {len(cookies)} cookies from DB (saved {row.saved_at})")
                return cookies
    except Exception as e:
        log.debug(f"Could not load cookies from DB: {e}")
    return []


def _save_cookies_to_db(cookies: list, status: str = "ok", error: str = "") -> None:
    """Persist browser cookies to relay_sessions table."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from models import RelaySession
        from extensions import db as _db
        from dashboard import app as _app
        from datetime import datetime as _dt
        with _app.app_context():
            row = RelaySession.query.first()
            if not row:
                row = RelaySession()
                _db.session.add(row)
            row.cookies_json = _json.dumps(cookies)
            row.saved_at     = _dt.utcnow()
            row.last_status  = status
            row.last_error   = error[:500] if error else ""
            _db.session.commit()
            log.info(f"Saved {len(cookies)} cookies to DB (status={status})")
    except Exception as e:
        log.debug(f"Could not save cookies to DB: {e}")


# ── navigation + download ─────────────────────────────────────────────────

async def _dismiss_interstitials(page) -> None:
    """
    Dismiss any modal / banner that may be blocking navigation.

    Confirmed interstitials on relay.amazon.com:
      • "Give Feedback" widget — appears on first post-login page load;
        dismissed by clicking its Cancel button.
    """
    try:
        await page.click(SEL.FEEDBACK_MODAL_DISMISS, timeout=3_000)
        log.info("Dismissed feedback modal.")
        await page.wait_for_timeout(500)
    except PlaywrightTimeout:
        pass   # modal not present — that's fine


async def _log_page_controls(page) -> None:
    """Dump all visible interactive elements to logs — helps diagnose selector issues."""
    try:
        controls = await page.evaluate("""() => {
            return [...document.querySelectorAll(
                'button, input, select, [role="button"], [role="combobox"], [role="option"]'
            )]
            .filter(el => el.offsetParent !== null)
            .slice(0, 60)
            .map(el => ({
                tag:         el.tagName,
                text:        (el.innerText || el.value || '').trim().slice(0, 60),
                type:        el.type || '',
                placeholder: el.placeholder || '',
                ariaLabel:   el.getAttribute('aria-label') || '',
                name:        el.name || '',
                id:          el.id || '',
            }));
        }""")
        log.info("Visible page controls (%d total):", len(controls))
        for c in controls:
            log.info("  %s", c)
    except Exception as e:
        log.debug("Could not dump page controls: %s", e)


async def _apply_date_filter(page, window_start: str, window_end: str) -> bool:
    """
    Try to set the History tab date range to window_start–window_end.

    Attempts multiple strategies; returns True if any succeeded.
    Never raises — a failure just means the default date range is used.

    Date format expected: 'YYYY-MM-DD'
    """
    try:
        s = datetime.strptime(window_start, '%Y-%m-%d')
        e = datetime.strptime(window_end,   '%Y-%m-%d')
    except ValueError:
        log.warning("Invalid window dates for date filter: %s – %s", window_start, window_end)
        return False

    # Amazon Relay shows dates as MM/DD/YYYY in its UI inputs
    start_str = s.strftime('%-m/%-d/%Y')  # e.g. 4/5/2026
    end_str   = e.strftime('%-m/%-d/%Y')  # e.g. 4/8/2026

    log.info("Applying date filter: %s – %s", window_start, window_end)

    # ── Strategy 1: "This week" quick-select ──────────────────────────────
    # Amazon Relay may offer a "This week" preset that selects the current
    # Sunday–Saturday window automatically.
    try:
        el = await page.query_selector(SEL.DATE_THIS_WEEK)
        if el and await el.is_visible():
            await el.click()
            await page.wait_for_timeout(2_000)
            log.info("Date filter: clicked 'This week' preset.")
            return True
    except Exception as exc:
        log.debug("Strategy 1 (This week): %s", exc)

    # ── Strategy 2: Open date-range picker then fill start/end inputs ─────
    try:
        trigger = await page.query_selector(SEL.DATE_FILTER_BUTTON)
        if trigger and await trigger.is_visible():
            await trigger.click()
            await page.wait_for_timeout(1_000)
            log.info("Date filter: opened date picker via trigger button.")
    except Exception as exc:
        log.debug("Strategy 2 trigger: %s", exc)

    try:
        start_el = await page.query_selector(SEL.DATE_START_INPUT)
        end_el   = await page.query_selector(SEL.DATE_END_INPUT)
        if start_el and end_el:
            await start_el.triple_click()
            await start_el.type(start_str)
            await end_el.triple_click()
            await end_el.type(end_str)
            await page.wait_for_timeout(500)
            log.info("Date filter: filled start=%s end=%s", start_str, end_str)

            # Click Apply/Search if present
            try:
                apply_btn = await page.query_selector(SEL.DATE_APPLY_BUTTON)
                if apply_btn and await apply_btn.is_visible():
                    await apply_btn.click()
                    await page.wait_for_timeout(2_000)
                    log.info("Date filter: clicked Apply.")
            except Exception as exc:
                log.debug("Strategy 2 apply: %s", exc)

            return True
    except Exception as exc:
        log.debug("Strategy 2 (fill inputs): %s", exc)

    log.warning(
        "Could not apply date filter — exporting whatever Amazon Relay shows by default. "
        "Check the 'Visible page controls' log lines above to find the right selectors."
    )
    return False


async def _navigate_to_trips_history(
    page,
    already_on_tours: bool = False,
    window_start: str = '',
    window_end:   str = '',
) -> None:
    """
    Navigate to the Trips → History tab on Amazon Relay.

    Confirmed navigation path (live DOM inspection 2026-03-24):
      1. GET https://relay.amazon.com/tours/  → redirects to /tours/upcoming
      2. Dismiss "Give Feedback" modal if present (Cancel button)
      3. Click the History <button> tab  → URL becomes /tours/history
      4. Wait for Export button to confirm history view loaded
      5. Apply date range filter (window_start – window_end) if provided

    NOTE: /trips 404s. The real path is /tours/.
    """
    if not already_on_tours:
        log.info(f"Navigating to {SEL.RELAY_TRIPS_URL} …")
        await page.goto(SEL.RELAY_TRIPS_URL, wait_until="domcontentloaded",
                        timeout=SEL.NAV_TIMEOUT_MS)
        await page.wait_for_timeout(4_000)   # let SPA finish rendering

    log.info(f"Post-navigation URL: {page.url}  title: {await page.title()!r}")

    # Verify we landed on the tours section
    if SEL.TRIPS_HISTORY_URL_PART not in page.url:
        await _safe_screenshot(page, "tours_nav_failed")
        raise RuntimeError(
            f"Expected URL containing '{SEL.TRIPS_HISTORY_URL_PART}' but got: {page.url}\n"
            "The /tours/ URL may have changed — update RELAY_TRIPS_URL in relay_selectors.py."
        )

    # Dismiss any interstitial before clicking tabs
    await _dismiss_interstitials(page)

    # Click the History tab (it's a <button>, not an <a>)
    log.info("Clicking History tab …")
    try:
        await page.click(SEL.NAV_HISTORY_TAB, timeout=SEL.ELEMENT_TIMEOUT_MS)
        await page.wait_for_timeout(3_000)
        log.info(f"After History click URL: {page.url}")
    except PlaywrightTimeout:
        await _safe_screenshot(page, "history_tab_not_found")
        # Dump visible buttons for diagnosis
        btns = await page.evaluate(
            "() => [...document.querySelectorAll('button')].filter(b => b.offsetParent).map(b => b.innerText.trim())"
        )
        raise RuntimeError(
            f"History tab button not found. Visible buttons: {btns}\n"
            "Update NAV_HISTORY_TAB in relay_selectors.py."
        )

    # Confirm the history view loaded by waiting for the Export button
    log.info("Waiting for history view to be ready …")
    try:
        await _wait_for_any(page, SEL.HISTORY_PAGE_READY, SEL.ELEMENT_TIMEOUT_MS)
        log.info(f"History page ready. URL: {page.url}")
    except PlaywrightTimeout:
        await _safe_screenshot(page, "history_page_not_ready")
        raise RuntimeError(
            "History page did not finish loading within timeout. "
            "Update HISTORY_PAGE_READY in relay_selectors.py."
        )

    # Always dump visible controls — helps diagnose date filter selectors
    await _log_page_controls(page)

    # Apply date range filter if window dates were provided
    if window_start and window_end:
        await _apply_date_filter(page, window_start, window_end)
        # Wait for the page to reload results after filter change
        await page.wait_for_timeout(3_000)


async def _trigger_csv_download(page) -> Path:
    """
    Click the Export button on the Trips → History view and capture the download.

    Confirmed behaviour (live inspection 2026-03-24):
      Export is a single <button> that triggers an immediate file download —
      no modal, no format chooser, no confirm dialog.
    """
    import shutil
    DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)

    # Confirm Export button is present and not disabled before starting the watcher
    try:
        export_btn = await page.wait_for_selector(
            SEL.EXPORT_BUTTON, state="visible", timeout=SEL.ELEMENT_TIMEOUT_MS
        )
    except PlaywrightTimeout:
        await _safe_screenshot(page, "export_button_not_found")
        raise RuntimeError(
            "Export button not found on the History page. "
            "Update EXPORT_BUTTON in relay_selectors.py."
        )

    log.info("Export button found — starting download watcher …")

    async with page.expect_download(timeout=SEL.DOWNLOAD_TIMEOUT_MS) as dl_info:
        await export_btn.click()
        log.info("Export clicked.")

    download  = await dl_info.value
    date_str  = datetime.now().strftime("%Y-%m-%d")
    dest_name = f"amazon-relay-{date_str}.csv"
    dest_path = DOWNLOAD_PATH / dest_name
    await download.save_as(str(dest_path))

    # Keep a stable latest-copy for the ingestion pipeline
    latest_path = DOWNLOAD_PATH / "amazon-relay-latest.csv"
    shutil.copy2(dest_path, latest_path)

    size = dest_path.stat().st_size
    log.info(f"Download saved: {dest_path.name}  ({size:,} bytes)")
    if size < 100:
        raise RuntimeError(f"Downloaded file is suspiciously small ({size} bytes) — export may have failed.")
    return dest_path


# ── public entry point ────────────────────────────────────────────────────

async def fetch_relay_csv(
    window_start: str = '',
    window_end:   str = '',
) -> Path:
    """
    Full fetch flow with retry logic.

    Args:
        window_start: YYYY-MM-DD start of the reporting window (e.g. '2026-04-05').
                      When provided, the fetcher tries to apply this date range in
                      the History tab filter before clicking Export.
        window_end:   YYYY-MM-DD end of the reporting window (e.g. '2026-04-08').

    Strategy is selected automatically:
      - DATABASE_URL set  → DB-backed cookies (Railway)
      - No DATABASE_URL   → persistent filesystem profile (local)

    Returns the path to the downloaded CSV file.
    Raises RuntimeError if all retries fail.
    """
    last_error: Exception | None = None

    if _DB_SESSION:
        log.info("Session strategy: DATABASE (cookies stored in PostgreSQL)")
    else:
        PROFILE_PATH.mkdir(parents=True, exist_ok=True)
        profile_is_new = not any(PROFILE_PATH.iterdir())
        log.info(
            f"Session strategy: FILESYSTEM profile at {PROFILE_PATH}"
            + (" (new — first-time login required)" if profile_is_new else " (reusing)")
        )

    for attempt in range(1, MAX_RETRIES + 1):
        log.info(f"=== Amazon Relay fetch — attempt {attempt}/{MAX_RETRIES} ===")
        try:
            async with async_playwright() as pw:
                if not _DB_SESSION:
                    # ── Local: persistent profile keeps full browser fingerprint ──
                    context = await pw.chromium.launch_persistent_context(
                        user_data_dir=str(PROFILE_PATH),
                        headless=HEADLESS,
                        accept_downloads=True,
                        viewport={"width": 1280, "height": 900},
                    )
                    page = await context.new_page()
                else:
                    # ── Railway: regular context + DB cookies ──────────────────
                    browser = await pw.chromium.launch(
                        headless=HEADLESS,
                        args=["--no-sandbox", "--disable-setuid-sandbox",
                              "--disable-dev-shm-usage"],
                    )
                    saved_cookies = _load_cookies_from_db()
                    context = await browser.new_context(
                        accept_downloads=True,
                        viewport={"width": 1280, "height": 900},
                    )
                    if saved_cookies:
                        await context.add_cookies(saved_cookies)
                        log.info(f"Injected {len(saved_cookies)} saved cookies.")
                    page = await context.new_page()

                # ── Check session by navigating to an auth-required page ─────
                # Go directly to /tours/ — if Amazon redirects to sign-in the
                # session is invalid and we must do a full login.
                # Never check the base URL (marketing page — never requires auth).
                log.info("Checking session via /tours/ …")
                await page.goto(SEL.RELAY_TRIPS_URL, wait_until="domcontentloaded",
                                timeout=SEL.NAV_TIMEOUT_MS)
                await page.wait_for_timeout(3_000)

                if "sign-in" in page.url.lower() or "ap/signin" in page.url.lower():
                    log.info("Redirected to sign-in — session invalid, performing full login …")
                    await _login(page)
                    fresh = await context.cookies()
                    _save_cookies_to_db(fresh, status="ok")
                    # After login we land on homepage — need full /tours/ navigation
                    await _navigate_to_trips_history(
                        page, already_on_tours=False,
                        window_start=window_start, window_end=window_end,
                    )
                else:
                    log.info(f"Session valid — already on {page.url}")
                    # Already on /tours/ from session check — skip re-navigation
                    await _navigate_to_trips_history(
                        page, already_on_tours=True,
                        window_start=window_start, window_end=window_end,
                    )
                csv_path = await _trigger_csv_download(page)

                # Save fresh cookies after every successful run (both strategies)
                fresh = await context.cookies()
                _save_cookies_to_db(fresh, status="ok")

                await context.close()
                log.info(f"Fetch completed successfully: {csv_path}")
                return csv_path

        except RuntimeError as e:
            # Detect CAPTCHA — do not retry, save failure status
            err_str = str(e)
            if "CAPTCHA" in err_str or "MFA" in err_str or "challenge" in err_str.lower():
                if _DB_SESSION:
                    _save_cookies_to_db([], status="captcha", error=err_str)
                raise   # propagate immediately — no retry on CAPTCHA

            last_error = e
            log.error(f"Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                wait_s = 30 * attempt
                log.info(f"Retrying in {wait_s}s …")
                await asyncio.sleep(wait_s)

        except Exception as e:
            last_error = e
            log.error(f"Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                wait_s = 30 * attempt
                log.info(f"Retrying in {wait_s}s …")
                await asyncio.sleep(wait_s)

    raise RuntimeError(
        f"All {MAX_RETRIES} fetch attempts failed. Last error: {last_error}"
    )
