# Email Follow-Up Automation — Instantly + Interested Leads Sheet

## Purpose

Automatically send follow-up emails to leads in the "Interested Leads" Google Sheet whose status is `Loom Sent`. Tracks how many follow-ups have been sent per lead and increments after each send. Sends up to 4 follow-ups per lead via Instantly.

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| Google Sheet ID | `.env` → `INTERESTED_LEADS_SHEET_ID` | "Interested Leads" sheet |
| Instantly API key | `.env` → `INSTANTLY_API_KEY` | From Instantly account settings |
| Sending account email | `.env` → `INSTANTLY_FROM_EMAIL` | The mailbox to send from in Instantly |
| Follow-up copy | This directive (Section: Email Copy) | 4 templates, TBD — user will provide |

---

## Google Sheet Schema

Expected columns in "Interested Leads" sheet (confirm with user if different):

| Column | Description |
|---|---|
| `First Name` | Lead's first name (used in email personalization) |
| `Last Name` | Lead's last name |
| `Email` | Lead's email address |
| `Company` | Lead's company name |
| `Status` | Current lead status (trigger: `Loom Sent`) |
| `Follow Up Count` | Integer 0–4. How many follow-ups have been sent. |
| `Last Follow Up Date` | Date of most recent follow-up send |
| `Loom URL` | URL of the Loom video sent to them |
| `Notes` | Any relevant context |

> **TODO:** Confirm exact column names with user once we have sheet access.

---

## Trigger Condition

Run this automation when:
- `Status` = `Loom Sent`
- `Follow Up Count` < 4

A lead is eligible for a follow-up email. Each run checks all rows and sends the *next* follow-up for each eligible lead.

---

## Follow-Up Sequence Logic

| Follow Up Count (current) | Email to send | After sending, set count to |
|---|---|---|
| 0 | Follow-up #1 | 1 |
| 1 | Follow-up #2 | 2 |
| 2 | Follow-up #3 | 3 |
| 3 | Follow-up #4 | 4 |
| 4 | No more emails | — (optionally update status to `Sequence Complete`) |

**Timing between follow-ups:** TBD — user to specify (e.g., 2 days, 3 days between each).

---

## Email Copy

> **TODO: User will provide copy for all 4 follow-ups.**

Templates should use these variables for personalization:
- `{{first_name}}` — lead's first name
- `{{company}}` — lead's company
- `{{loom_url}}` — Loom video URL

### Follow-up #1 Subject:
`[PLACEHOLDER]`

### Follow-up #1 Body:
```
[PLACEHOLDER — user to provide]
```

### Follow-up #2 Subject:
`[PLACEHOLDER]`

### Follow-up #2 Body:
```
[PLACEHOLDER — user to provide]
```

### Follow-up #3 Subject:
`[PLACEHOLDER]`

### Follow-up #3 Body:
```
[PLACEHOLDER — user to provide]
```

### Follow-up #4 Subject:
`[PLACEHOLDER]`

### Follow-up #4 Body:
```
[PLACEHOLDER — user to provide]
```

---

## Execution Scripts

| Script | Purpose |
|---|---|
| `execution/read_interested_leads.py` | Read leads from Google Sheet, filter eligible rows |
| `execution/send_instantly_email.py` | Send a single email via Instantly API |
| `execution/update_lead_followup.py` | Update `Follow Up Count` and `Last Follow Up Date` in sheet |
| `execution/email_followup_pipeline.py` | Main pipeline — orchestrates the above three |

> All scripts are to be created. Check `execution/` before writing; reuse any existing Google Sheets helpers.

---

## Execution Flow

```
1. Read all rows from "Interested Leads" sheet
2. Filter: Status == "Loom Sent" AND Follow Up Count < 4
3. For each eligible lead:
   a. Determine which follow-up to send (based on Follow Up Count)
   b. Render email template with lead's personalization variables
   c. Send email via Instantly API (reply-in-thread if possible)
   d. Update sheet: increment Follow Up Count, set Last Follow Up Date = today
4. Log results: how many emails sent, any failures
```

---

## Instantly API Notes

- Base URL: `https://api.instantly.ai/api/v1`
- Auth: `Authorization: Bearer <INSTANTLY_API_KEY>` header
- Relevant endpoint: `POST /emails/send` — send a single email from a connected mailbox
- To send as a reply in the original thread, include the original `reply_to_message_id` if available in the sheet
- Rate limits: check Instantly docs; add delay between sends if needed

> **TODO:** Confirm whether the sheet stores the original Instantly email thread ID for reply-in-thread functionality.

---

## Output / Side Effects

- Emails sent via Instantly from the configured mailbox
- Google Sheet updated: `Follow Up Count` incremented, `Last Follow Up Date` set
- Console log of results (leads processed, emails sent, errors)

---

## Edge Cases

- Lead already at Follow Up Count = 4 → skip, do not send
- Missing email address → skip and log warning
- Instantly API error → log error, do NOT increment counter (so it retries next run)
- Sheet update fails after email sent → log discrepancy; manual fix needed

---

## Environment Variables Required

Add to `.env`:
```
INTERESTED_LEADS_SHEET_ID=<google_sheet_id>
INSTANTLY_API_KEY=<your_instantly_api_key>
INSTANTLY_FROM_EMAIL=<sending_mailbox@yourdomain.com>
```

---

## Open Questions (to resolve with user)

1. What are the exact column names in the "Interested Leads" sheet?
2. What is the desired delay between follow-ups (days)?
3. Should follow-ups be sent as replies in the original email thread, or new emails?
4. What status should be set when all 4 follow-ups are exhausted?
5. Should this run on a schedule (cron) or manually triggered?
6. What copy should the 4 follow-up emails contain?
