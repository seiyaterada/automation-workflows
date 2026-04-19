Run the loom follow-up email automation against the Interested Leads Google Sheet.

## What this does

Finds all leads with `status = loom_sent` and `loom_followup_count < 4` that are due for their next follow-up, checks Instantly for replies, and sends the appropriate follow-up email in-thread. Updates the sheet after each send.

## Steps

1. Check that `.env` exists and contains `INSTANTLY_API_KEY` and `INTERESTED_LEADS_SHEET_ID`. If either is missing, tell the user and stop.

2. Ask the user: **"Run in dry-run mode (preview only) or live mode (actually sends emails)?"**
   - If dry-run: run `python execution/email_followup_pipeline.py --dry-run`
   - If live: run `python execution/email_followup_pipeline.py`

3. Show the output to the user clearly, highlighting:
   - How many emails were sent
   - Which leads were skipped because they replied (list their emails)
   - Which leads were skipped because not yet due
   - Any errors

4. If there were any errors, read the error message, diagnose the cause, and tell the user what went wrong and how to fix it. Common issues:
   - `INSTANTLY_API_KEY` invalid → check key in Instantly Settings → API Keys
   - `credentials.json` missing → needs Google service account setup
   - Instantly API field name mismatch → run `python execution/debug_instantly_thread.py --thread-id <id> --lead-email <email>` with a known-replied lead to inspect the raw response, then update `has_replied()` in `execution/email_followup_pipeline.py`

5. After a successful live run, summarise what happened and remind the user to run this daily (or set up a cron job).
