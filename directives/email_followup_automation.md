# Email Follow-Up Automation — Instantly + Interested Leads Sheet

## Purpose

Automatically send follow-up emails to leads whose status is `loom_sent` in the
"Interested Leads" Google Sheet. Tracks follow-up count, enforces spacing between
sends, skips leads who have already replied, and marks the sequence `lost` once
all 4 follow-ups are exhausted.

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| Google Sheet ID | `.env` → `INTERESTED_LEADS_SHEET_ID` | `1vGDbI6TBnmZyvoumLPpXtltyCTdplXUfeylWhrjS2q4` |
| Instantly API key | `.env` → `INSTANTLY_API_KEY` | From Instantly account settings |

---

## Google Sheet Schema

Sheet: "Interested Leads" — confirmed column names:

| Column | Type | Description |
|---|---|---|
| `lead_email` | string | Lead's email address |
| `first_name` | string | Lead's first name (personalization) |
| `eaccount` | string | Sending mailbox (e.g. jordan@automlettenow.com) |
| `sender_first_name` | string | Sender's first name (personalization) |
| `status` | string | Workflow stage — trigger value: `loom_sent` |
| `loom_sent_at` | ISO datetime | When the loom was sent — used as timing anchor |
| `loom_link` | URL | Loom video URL |
| `loom_followup_count` | integer | How many follow-ups sent so far (0–4) |
| `loom_last_followup_at` | ISO datetime | **Add this column** — updated after each send |
| `reply_to_uuid` | string | Instantly message UUID — used for reply-in-thread |
| `thread_id` | string | Instantly thread ID |
| `campaign_id` | string | Instantly campaign ID |

> **Action required:** Add `loom_last_followup_at` column to the sheet. The script
> updates this after each send to anchor the next follow-up's timing.

---

## Trigger Conditions

A lead is eligible for a follow-up if ALL of the following are true:
1. `status` == `loom_sent`
2. `loom_followup_count` < 4
3. Enough time has passed since the last send (see Timing below)
4. The lead has NOT replied to the thread in Instantly

---

## Timing Logic

Follow-up spacing increments by 1 day each round:

| `loom_followup_count` | Days to wait after previous send | Anchor for wait |
|---|---|---|
| 0 (no FU sent yet) | 1 day | `loom_sent_at` |
| 1 | 2 days | `loom_last_followup_at` |
| 2 | 3 days | `loom_last_followup_at` |
| 3 | 4 days | `loom_last_followup_at` |

Formula: `days_to_wait = loom_followup_count + 1`

The script checks whether `today >= anchor_date + days_to_wait`. If not yet due,
the lead is skipped until the next run.

---

## Follow-Up Sequence Logic

| Current `loom_followup_count` | Email sent | After success: set count to | After count reaches 4 |
|---|---|---|---|
| 0 | Follow-up #1 | 1 | — |
| 1 | Follow-up #2 | 2 | — |
| 2 | Follow-up #3 | 3 | — |
| 3 | Follow-up #4 | 4 | Set `status` = `lost` |

---

## Email Copy

Replies are sent in-thread so Instantly inherits `Re: {original subject}` automatically — no subject needed in templates.

Template variables:
- `{first_name}` — lead's first name
- `{sender_first_name}` — sender's first name (from `sender_first_name` column, falls back to mailbox prefix)
- `{loom_link}` — Loom video URL (available if needed)

### Follow-up #1
```
Hi {first_name},

Wanted to check in if you had a chance to watch the video. Let me know if you have any questions.

Thanks,
{sender_first_name}
```

### Follow-up #2
```
Hi {first_name},

Just wanted to see if you were able to make a bit of time to watch the video that I recorded you. Would love to know what you think.

Thanks,
{sender_first_name}
```

### Follow-up #3
*(Offers an alternative — a summary — to lower the barrier to engagement)*
```
Hi {first_name},

Would it be easier if I sent over a quick summary of what's in the video instead? Happy to break it down in a few bullet points if that saves you some time.

Just let me know either way.

Thanks,
{sender_first_name}
```

### Follow-up #4
*(Breakup email — creates urgency by signalling it's the last touch. High response rate.)*
```
Hi {first_name},

I don't want to keep filling up your inbox if the timing isn't right — this will be my last follow-up.

If you ever want to revisit the video or chat about what we put together for you, feel free to reach out anytime.

Wishing you all the best,
{sender_first_name}
```

---

## Instantly API

- Base URL: `https://api.instantly.ai/api/v2`
- Auth header: `X-API-Key: {INSTANTLY_API_KEY}`

**Key endpoints:**

| Action | Endpoint | Notes |
|---|---|---|
| Check thread for replies | `GET /emails?thread_id={thread_id}` | Filter `from_address` == lead's email to detect reply |
| Send reply in thread | `POST /emails/reply` | Body: `reply_to_uuid`, `eaccount`, `to_address`, `body` |

Reply-in-thread uses `reply_to_uuid` (the Instantly message UUID of the last sent
email in the thread) and `eaccount` (the exact mailbox used originally). After
each successful send, update `reply_to_uuid` in the sheet to the UUID returned
by the API so the next follow-up chains correctly.

---

## Execution Script

`execution/email_followup_pipeline.py`

Run manually or via cron (recommended: daily). Usage:
```bash
python execution/email_followup_pipeline.py
python execution/email_followup_pipeline.py --dry-run   # preview without sending
```

---

## Execution Flow

```
1. Load all rows from "Interested Leads" sheet
2. Filter: status == loom_sent AND loom_followup_count < 4
3. For each eligible lead:
   a. Check timing — is it due? (today >= anchor + days_to_wait)
      → If not: skip
   b. Check Instantly for replies in thread (GET /emails?thread_id=...)
      → If lead replied: skip (do not change status — let human decide)
   c. Render follow-up email template #{count+1} with lead's variables
   d. Send via Instantly reply-in-thread (POST /emails/reply)
      → On API error: log and skip — do NOT increment count
   e. Update sheet row:
      - loom_followup_count += 1
      - loom_last_followup_at = now
      - reply_to_uuid = UUID returned by Instantly API
      - If new count == 4: status = lost
4. Print summary: leads processed, emails sent, skipped, errors
```

---

## Edge Cases

| Scenario | Behavior |
|---|---|
| Lead replied to thread | Skip entirely — do not send, do not change count or status |
| Missing `loom_sent_at` | Skip and log warning |
| Missing `loom_link` | Skip and log warning |
| Instantly API error on send | Log error, skip — do NOT update count (retries next run) |
| Sheet update fails after email sent | Log the discrepancy; count will be off by 1 — manual fix |
| `loom_last_followup_at` missing for count > 0 | Fall back to `loom_sent_at` + cumulative days |
| `sender_first_name` blank | Fall back to first word before `@` in `eaccount` |

---

## Environment Variables Required

```
INTERESTED_LEADS_SHEET_ID=1vGDbI6TBnmZyvoumLPpXtltyCTdplXUfeylWhrjS2q4
INSTANTLY_API_KEY=<your_instantly_api_key>
```

---

## Open Questions

1. **Reply subject line** — Instantly should inherit `Re: {original subject}` automatically for in-thread replies. Verify this is the case when testing.
