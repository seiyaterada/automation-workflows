# Skill: Loom Follow-Up Automation

Automatically sends up to 4 follow-up emails to leads in the "Interested Leads"
Google Sheet whose status is `loom_sent`. Replies in-thread via Instantly, checks
for replies before sending, and marks leads `lost` after the sequence completes.

## Files

```
skills/loom_followup/
  README.md             — this file
  directive.md          — full SOP and reference
  pipeline.py           — main execution script
  test_pipeline.py      — test suite (57 tests)
  debug_thread.py       — inspect Instantly API response for a thread
  routine.md            — headless Claude routine prompt (for claude -p)
  run_routine.sh        — shell wrapper for cron/n8n scheduling
  slash_command.md      — copy to .claude/commands/loom-followup.md
```

## Setup

### 1. Environment variables

Add to your `.env`:
```
INTERESTED_LEADS_SHEET_ID=1vGDbI6TBnmZyvoumLPpXtltyCTdplXUfeylWhrjS2q4
INSTANTLY_API_KEY=<your_instantly_api_key>
```

### 2. Google Sheet columns required

The "Interested Leads" sheet must have these columns (exact names):

| Column | Notes |
|---|---|
| `lead_email` | Lead's email |
| `first_name` | Lead's first name |
| `eaccount` | Sending mailbox used in Instantly |
| `sender_first_name` | Sender's first name for email sign-off |
| `status` | Trigger value: `loom_sent` |
| `loom_sent_at` | ISO datetime — when the loom was sent |
| `loom_link` | Loom video URL |
| `loom_followup_count` | Integer 0–4 |
| `loom_last_follow_up_at` | Updated after each send — add this column |
| `reply_to_uuid` | Instantly message UUID for reply-in-thread |
| `thread_id` | Instantly thread ID |
| `campaign_id` | Instantly campaign ID |

### 3. Google credentials

Place `credentials.json` (service account) in the project root.

### 4. Wire up the slash command

```bash
mkdir -p .claude/commands
cp skills/loom_followup/slash_command.md .claude/commands/loom-followup.md
```

Then type `/loom-followup` in any Claude Code session to run interactively.

### 5. Schedule (optional)

```bash
chmod +x skills/loom_followup/run_routine.sh

# Cron — daily at 9am
crontab -e
# Add: 0 9 * * * /path/to/your/project/skills/loom_followup/run_routine.sh
```

## Usage

```bash
# Dry run — preview without sending
python skills/loom_followup/pipeline.py --dry-run

# Live run
python skills/loom_followup/pipeline.py

# Run tests
python -m pytest skills/loom_followup/test_pipeline.py -v

# Debug Instantly API field names for a thread
python skills/loom_followup/debug_thread.py \
  --thread-id "<thread_id_from_sheet>" \
  --lead-email "<lead_email>"
```

## Follow-up sequence

| Follow-up | Wait after previous | Copy summary |
|---|---|---|
| #1 | 1 day after loom sent | Check-in on the video |
| #2 | 2 days after FU#1 | Ask if they had time to watch |
| #3 | 3 days after FU#2 | Offer a written summary instead |
| #4 | 4 days after FU#3 | Breakup email — last touch |

After FU#4 is sent, `status` is set to `lost`.
