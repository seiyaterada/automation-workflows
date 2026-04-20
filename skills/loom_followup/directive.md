# Directive: Loom Follow-Up Automation — Instantly + Interested Leads Sheet

## Purpose

Automatically send follow-up emails to leads whose status is `loom_sent` in the
"Interested Leads" Google Sheet. Tracks follow-up count, enforces spacing between
sends, skips leads who have already replied, and marks the sequence `lost` once
all 4 follow-ups are exhausted.

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| Google Sheet ID | `.env` → `INTERESTED_LEADS_SHEET_ID` | "Interested Leads" sheet |
| Instantly API key | `.env` → `INSTANTLY_API_KEY` | From Instantly account settings |

---

## Google Sheet Schema

| Column | Type | Description |
|---|---|---|
| `lead_email` | string | Lead's email address |
| `first_name` | string | Lead's first name (personalization) |
| `eaccount` | string | Sending mailbox (e.g. jordan@automlettenow.com) |
| `sender_first_name` | string | Sender's first name (personalization) |
| `status` | string | Workflow stage — trigger value: `loom_sent` |
| `loom_sent_at` | ISO datetime | When the loom was sent — timing anchor |
| `loom_link` | URL | Loom video URL |
| `loom_followup_count` | integer | How many follow-ups sent so far (0–4) |
| `loom_last_follow_up_at` | ISO datetime | Updated after each send |
| `reply_to_uuid` | string | Instantly message UUID — for reply-in-thread |
| `thread_id` | string | Instantly thread ID |
| `campaign_id` | string | Instantly campaign ID |

---

## Trigger Conditions

A lead is eligible for a follow-up if ALL of the following are true:
1. `status` == `loom_sent`
2. `loom_followup_count` < 4
3. Enough time has passed since the last send (see Timing)
4. The lead has NOT replied in the Instantly thread

---

## Timing Logic

| `loom_followup_count` | Days to wait | Anchor |
|---|---|---|
| 0 | 1 day | `loom_sent_at` |
| 1 | 2 days | `loom_last_follow_up_at` |
| 2 | 3 days | `loom_last_follow_up_at` |
| 3 | 4 days | `loom_last_follow_up_at` |

Formula: `days_to_wait = loom_followup_count + 1`

---

## Follow-Up Sequence

| Current count | Email sent | Set count to | At count 4 |
|---|---|---|---|
| 0 | Follow-up #1 | 1 | — |
| 1 | Follow-up #2 | 2 | — |
| 2 | Follow-up #3 | 3 | — |
| 3 | Follow-up #4 | 4 | Set `status` = `lost` |

---

## Email Copy

Replies are sent in-thread — Instantly inherits `Re: {original subject}` automatically.

Variables: `{first_name}`, `{sender_first_name}`, `{loom_link}`

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
*(Offers a summary as an alternative to lower the engagement barrier)*
```
Hi {first_name},

Would it be easier if I sent over a quick summary of what's in the video instead? Happy to break it down in a few bullet points if that saves you some time.

Just let me know either way.

Thanks,
{sender_first_name}
```

### Follow-up #4
*(Breakup email — signals last touch, high reply rate)*
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
- Auth: `X-API-Key: {INSTANTLY_API_KEY}`

| Action | Endpoint |
|---|---|
| Check for replies | `GET /emails?thread_id={thread_id}` — filter `from_address` == lead email |
| Send reply in thread | `POST /emails/reply` — body: `reply_to_uuid`, `eaccount`, `to_address`, `body` |

After each send, update `reply_to_uuid` in the sheet to the UUID returned by
Instantly so the next follow-up chains correctly.

---

## Execution Script

`skills/loom_followup/pipeline.py`

```bash
python skills/loom_followup/pipeline.py           # live
python skills/loom_followup/pipeline.py --dry-run  # preview
```

---

## Execution Flow

```
1. Load all rows from "Interested Leads" sheet
2. Filter: status == loom_sent AND loom_followup_count < 4
3. For each eligible lead:
   a. Timing check — is it due?
   b. Reply check — has lead replied in Instantly? If yes: skip entirely
   c. Render follow-up template with lead's variables
   d. Send via Instantly reply-in-thread
      → On error: log, skip, do NOT increment count
   e. Update sheet: increment count, set loom_last_follow_up_at, update reply_to_uuid
      → If new count == 4: set status = lost
4. Print summary
```

---

## Edge Cases

| Scenario | Behaviour |
|---|---|
| Lead replied | Skip — no send, no sheet update, no status change |
| Missing `loom_sent_at` | Skip and log warning |
| Instantly API send error | Log error, skip — do NOT update count |
| `loom_last_follow_up_at` empty for count > 0 | Fallback to `loom_sent_at` + cumulative days |
| `sender_first_name` blank | Fallback to prefix before `@` in `eaccount` |

---

## Environment Variables

```
INTERESTED_LEADS_SHEET_ID=<sheet_id>
INSTANTLY_API_KEY=<key>
```
