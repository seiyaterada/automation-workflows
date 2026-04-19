#!/usr/bin/env python3
"""
Debug tool — inspect what Instantly returns for a real thread.

Use this BEFORE the first live run to verify:
  1. The /emails endpoint accepts thread_id as a filter
  2. The field name for the sender address (from_address vs from vs other)
  3. Whether a replied lead shows up correctly

Usage:
    python execution/debug_instantly_thread.py --thread-id <thread_id> --lead-email <email>

Example (use a thread from the sheet where you KNOW they replied):
    python execution/debug_instantly_thread.py \
        --thread-id "ad-wvnBrTo-Xa2IcOxTr9KSD3b" \
        --lead-email "alexander@quriasolutions.com"
"""

import argparse
import json
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

INSTANTLY_API_KEY = os.getenv("INSTANTLY_API_KEY")
INSTANTLY_BASE = "https://api.instantly.ai/api/v2"


def check_thread(thread_id: str, lead_email: str):
    if not INSTANTLY_API_KEY:
        sys.exit("[ERROR] INSTANTLY_API_KEY not set in .env")

    headers = {"X-API-Key": INSTANTLY_API_KEY, "Content-Type": "application/json"}

    print(f"\nQuerying Instantly for thread: {thread_id}")
    print(f"Looking for replies from: {lead_email}\n")

    resp = requests.get(
        f"{INSTANTLY_BASE}/emails",
        headers=headers,
        params={"thread_id": thread_id, "limit": 50},
        timeout=10,
    )

    print(f"Status code: {resp.status_code}")

    try:
        data = resp.json()
    except Exception:
        print(f"Raw response: {resp.text}")
        return

    print(f"\nFull response:\n{json.dumps(data, indent=2)}\n")

    emails = data.get("items", [])
    print(f"Total emails in thread: {len(emails)}")

    if emails:
        print(f"\nFields available on first email: {list(emails[0].keys())}")

    replied = False
    for i, email in enumerate(emails):
        from_addr = email.get("from_address", "") or email.get("from", "")
        direction = email.get("type") or email.get("direction") or email.get("email_type") or "unknown"
        print(f"\nEmail #{i+1}: from={from_addr!r}, type/direction={direction!r}")
        if from_addr.lower().strip() == lead_email.lower().strip():
            replied = True
            print(f"  ^^^ REPLY FROM LEAD DETECTED")

    print(f"\n{'='*50}")
    print(f"has_replied result for {lead_email}: {replied}")

    if not replied:
        print("\nNOTE: If you expected a reply here, the field name may be different.")
        print("Check the 'Fields available' output above and update has_replied() accordingly.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug Instantly thread reply detection")
    parser.add_argument("--thread-id", required=True, help="Thread ID from the sheet")
    parser.add_argument("--lead-email", required=True, help="Lead email to check for reply")
    args = parser.parse_args()
    check_thread(args.thread_id, args.lead_email)
