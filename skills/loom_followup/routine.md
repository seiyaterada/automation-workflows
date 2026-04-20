You are running the daily loom follow-up automation. This is a non-interactive scheduled run — do not ask questions, just execute.

## Your job

Run the loom follow-up pipeline by executing:

```bash
python skills/loom_followup/pipeline.py
```

from the project root.

## On success

Report a clean summary:
- Date and time of run
- How many emails were sent (list each lead email + which follow-up # was sent)
- How many leads were skipped because they replied (list their emails)
- How many leads were skipped because not yet due
- How many errors occurred

## On any error or unexpected output

1. Read the full error message and stack trace
2. Read `skills/loom_followup/directive.md` for context on intended behaviour
3. If it is a fixable code bug (not a missing credential or API key): fix `skills/loom_followup/pipeline.py`, then re-run
4. If it requires human action (missing `.env` key, expired credentials, Instantly API field name changed), stop and report exactly what needs to be fixed and how

## Non-negotiable rules

- Never send emails to leads whose thread shows a reply from the lead — the pipeline handles this, but if you see any sign this check was skipped, abort and flag it
- Never increment `loom_followup_count` or update the sheet unless the send was confirmed successful
- If uncertain about anything, abort and report — do not guess
