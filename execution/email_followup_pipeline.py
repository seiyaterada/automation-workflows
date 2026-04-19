#!/usr/bin/env python3
"""
Loom follow-up automation pipeline.

Reads "Interested Leads" sheet, finds leads due for a follow-up, checks Instantly
for replies, sends the next follow-up email in-thread, and updates the sheet.

Usage:
    python execution/email_followup_pipeline.py
    python execution/email_followup_pipeline.py --dry-run
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import gspread
import requests
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

SHEET_ID = os.getenv("INTERESTED_LEADS_SHEET_ID", "1vGDbI6TBnmZyvoumLPpXtltyCTdplXUfeylWhrjS2q4")
INSTANTLY_API_KEY = os.getenv("INSTANTLY_API_KEY")
INSTANTLY_BASE = "https://api.instantly.ai/api/v2"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# ---------------------------------------------------------------------------
# Email templates
# Replies are sent in-thread so Instantly handles the subject automatically.
# Leave subject as empty string to let Instantly inherit Re: {original subject}.
# Variables: {first_name}, {sender_first_name}, {loom_link}
# ---------------------------------------------------------------------------

FOLLOWUP_TEMPLATES = {
    1: {
        "subject": "",
        "body": (
            "Hi {first_name},\n\n"
            "Wanted to check in if you had a chance to watch the video. "
            "Let me know if you have any questions.\n\n"
            "Thanks,\n"
            "{sender_first_name}"
        ),
    },
    2: {
        "subject": "",
        "body": (
            "Hi {first_name},\n\n"
            "Just wanted to see if you were able to make a bit of time to watch "
            "the video that I recorded you. Would love to know what you think.\n\n"
            "Thanks,\n"
            "{sender_first_name}"
        ),
    },
    3: {
        "subject": "",
        "body": (
            "Hi {first_name},\n\n"
            "Would it be easier if I sent over a quick summary of what's in the "
            "video instead? Happy to break it down in a few bullet points if that "
            "saves you some time.\n\n"
            "Just let me know either way.\n\n"
            "Thanks,\n"
            "{sender_first_name}"
        ),
    },
    4: {
        "subject": "",
        "body": (
            "Hi {first_name},\n\n"
            "I don't want to keep filling up your inbox if the timing isn't right "
            "— this will be my last follow-up.\n\n"
            "If you ever want to revisit the video or chat about what we put "
            "together for you, feel free to reach out anytime.\n\n"
            "Wishing you all the best,\n"
            "{sender_first_name}"
        ),
    },
}


# ---------------------------------------------------------------------------
# Google Sheets helpers
# ---------------------------------------------------------------------------

def get_sheet():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)
    return spreadsheet.sheet1


def get_all_leads(sheet) -> list[dict]:
    return sheet.get_all_records()


def get_row_index(sheet, lead_email: str) -> Optional[int]:
    """Return 1-based row index for the given lead email (row 1 = header)."""
    emails = sheet.col_values(1)  # lead_email is column A
    try:
        return emails.index(lead_email) + 1  # +1 because list is 0-indexed
    except ValueError:
        return None


def update_lead_after_send(sheet, lead: dict, new_count: int, new_uuid: str, sent_at: str, dry_run: bool):
    """Increment follow-up count, set last followup timestamp, update reply_to_uuid.
    If new_count == 4, set status to lost.
    """
    if dry_run:
        return

    row_idx = get_row_index(sheet, lead["lead_email"])
    if row_idx is None:
        print(f"  [ERROR] Could not find row for {lead['lead_email']} to update")
        return

    headers = sheet.row_values(1)

    def col(name):
        return headers.index(name) + 1  # 1-based

    sheet.update_cell(row_idx, col("loom_followup_count"), new_count)
    sheet.update_cell(row_idx, col("loom_last_followup_at"), sent_at)
    if new_uuid:
        sheet.update_cell(row_idx, col("reply_to_uuid"), new_uuid)
    if new_count >= 4:
        sheet.update_cell(row_idx, col("status"), "lost")


# ---------------------------------------------------------------------------
# Timing logic
# ---------------------------------------------------------------------------

def parse_dt(value: str) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%SZ", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def is_due(lead: dict) -> bool:
    """Check whether today is on or past the next follow-up send date."""
    count = int(lead.get("loom_followup_count") or 0)
    days_to_wait = count + 1  # FU#1: 1 day, FU#2: 2 days, FU#3: 3 days, FU#4: 4 days

    if count == 0:
        anchor = parse_dt(str(lead.get("loom_sent_at", "")))
    else:
        anchor = parse_dt(str(lead.get("loom_last_followup_at", "")))
        if anchor is None:
            # Fallback: compute from loom_sent_at + cumulative days (1+2+...+count)
            anchor = parse_dt(str(lead.get("loom_sent_at", "")))
            if anchor:
                cumulative = sum(range(1, count + 1))
                anchor = anchor + timedelta(days=cumulative)

    if anchor is None:
        return False

    due = anchor + timedelta(days=days_to_wait)
    now = datetime.now(timezone.utc)
    return now >= due


# ---------------------------------------------------------------------------
# Instantly API helpers
# ---------------------------------------------------------------------------

def instantly_headers() -> dict:
    return {"X-API-Key": INSTANTLY_API_KEY, "Content-Type": "application/json"}


def has_replied(thread_id: str, lead_email: str) -> bool:
    """Check if the lead has sent any email in this thread."""
    try:
        resp = requests.get(
            f"{INSTANTLY_BASE}/emails",
            headers=instantly_headers(),
            params={"thread_id": thread_id, "limit": 50},
            timeout=10,
        )
        resp.raise_for_status()
        emails = resp.json().get("items", [])
        for email in emails:
            from_addr = email.get("from_address", "") or email.get("from", "")
            if from_addr.lower().strip() == lead_email.lower().strip():
                return True
    except requests.RequestException as e:
        print(f"  [WARN] Could not check replies for thread {thread_id}: {e}")
        # Fail open — assume no reply so we don't silently drop follow-ups
    return False


def send_reply(lead: dict, subject: str, body: str, dry_run: bool) -> Optional[str]:
    """Send a reply-in-thread via Instantly. Returns the new email UUID on success."""
    payload = {
        "reply_to_uuid": lead["reply_to_uuid"],
        "eaccount": lead["eaccount"],
        "to_address": lead["lead_email"],
        "subject": subject,
        "body": body,
    }

    if dry_run:
        print(f"  [DRY RUN] Would send to {lead['lead_email']} via {lead['eaccount']}")
        print(f"  Subject: {subject}")
        print(f"  Body preview: {body[:120]}...")
        return "dry-run-uuid"

    try:
        resp = requests.post(
            f"{INSTANTLY_BASE}/emails/reply",
            headers=instantly_headers(),
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        # Instantly returns the new email UUID — field name may vary; check both
        return data.get("uuid") or data.get("id") or data.get("email_id")
    except requests.RequestException as e:
        print(f"  [ERROR] Instantly send failed for {lead['lead_email']}: {e}")
        return None


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def render_template(template: dict, lead: dict) -> tuple[str, str]:
    sender_first = lead.get("sender_first_name") or lead.get("eaccount", "").split("@")[0]
    variables = {
        "first_name": lead.get("first_name", ""),
        "sender_first_name": sender_first,
        "loom_link": lead.get("loom_link", ""),
    }
    subject = template["subject"].format(**variables)
    body = template["body"].format(**variables)
    return subject, body


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(dry_run: bool = False):
    if not INSTANTLY_API_KEY:
        sys.exit("[ERROR] INSTANTLY_API_KEY not set in .env")

    print(f"{'[DRY RUN] ' if dry_run else ''}Starting loom follow-up pipeline...")

    sheet = get_sheet()
    leads = get_all_leads(sheet)

    eligible = [
        lead for lead in leads
        if str(lead.get("status", "")).strip() == "loom_sent"
        and int(lead.get("loom_followup_count") or 0) < 4
    ]

    print(f"Found {len(eligible)} leads with status=loom_sent and followup_count<4")

    sent = 0
    skipped_timing = 0
    skipped_replied = 0
    errors = 0

    for lead in eligible:
        email = lead["lead_email"]
        count = int(lead.get("loom_followup_count") or 0)
        next_fu = count + 1

        print(f"\n→ {email} (FU count: {count}, next: #{next_fu})")

        # 1. Timing check
        if not is_due(lead):
            print(f"  Not due yet — skipping")
            skipped_timing += 1
            continue

        # 2. Reply check
        thread_id = str(lead.get("thread_id", "")).strip()
        if thread_id and has_replied(thread_id, email):
            print(f"  Lead has replied — skipping (manual review)")
            skipped_replied += 1
            continue

        # 3. Render template
        template = FOLLOWUP_TEMPLATES.get(next_fu)
        if not template:
            print(f"  [ERROR] No template for follow-up #{next_fu}")
            errors += 1
            continue

        subject, body = render_template(template, lead)

        # 4. Send
        new_uuid = send_reply(lead, subject, body, dry_run)
        if new_uuid is None:
            errors += 1
            continue

        # 5. Update sheet
        new_count = count + 1
        sent_at = datetime.now(timezone.utc).isoformat()
        update_lead_after_send(sheet, lead, new_count, new_uuid, sent_at, dry_run)

        status_update = " → status set to lost" if new_count >= 4 else ""
        print(f"  Sent FU #{next_fu}, count now {new_count}{status_update}")
        sent += 1

        # Brief pause between sends to avoid rate limiting
        if not dry_run:
            time.sleep(1)

    print(f"\n{'='*50}")
    print(f"Done. Sent: {sent} | Skipped (timing): {skipped_timing} | "
          f"Skipped (replied): {skipped_replied} | Errors: {errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Loom follow-up email pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
