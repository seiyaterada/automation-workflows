#!/usr/bin/env python3
"""
Tests for pipeline.py

Run with:
    python -m pytest skills/loom_followup/test_pipeline.py -v
    python -m pytest skills/loom_followup/test_pipeline.py -v -k "reply"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call
import pytest

os.environ.setdefault("INSTANTLY_API_KEY", "test-key")
os.environ.setdefault("INTERESTED_LEADS_SHEET_ID", "test-sheet-id")

from pipeline import (
    parse_dt,
    is_due,
    has_replied,
    render_template,
    update_lead_after_send,
    FOLLOWUP_TEMPLATES,
    run,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()

def days_from_now(n):
    return (datetime.now(timezone.utc) + timedelta(days=n)).isoformat()

def make_lead(**overrides):
    base = {
        "lead_email": "test@example.com",
        "first_name": "Alex",
        "eaccount": "jordan@automlette.com",
        "sender_first_name": "Jordan",
        "status": "loom_sent",
        "loom_sent_at": days_ago(3),
        "loom_link": "https://loom.com/share/abc123",
        "loom_followup_count": 0,
        "loom_last_follow_up_at": "",
        "reply_to_uuid": "uuid-abc",
        "thread_id": "thread-abc",
        "campaign_id": "campaign-abc",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# parse_dt
# ---------------------------------------------------------------------------

class TestParseDt:
    def test_iso_with_z(self):
        dt = parse_dt("2026-04-15T03:05:07.000Z")
        assert dt is not None
        assert dt.year == 2026
        assert dt.tzinfo is not None

    def test_iso_with_offset(self):
        dt = parse_dt("2026-04-14T00:39:11.733-07:00")
        assert dt is not None

    def test_iso_no_microseconds(self):
        assert parse_dt("2026-04-15T03:05:07Z") is not None

    def test_mdy_format(self):
        dt = parse_dt("3/27/2026")
        assert dt is not None
        assert dt.month == 3

    def test_empty_string(self):
        assert parse_dt("") is None

    def test_whitespace(self):
        assert parse_dt("  ") is None

    def test_invalid_format(self):
        assert parse_dt("not-a-date") is None


# ---------------------------------------------------------------------------
# is_due
# ---------------------------------------------------------------------------

class TestIsDue:
    def test_fu1_not_due_sent_today(self):
        lead = make_lead(loom_followup_count=0, loom_sent_at=days_ago(0))
        assert is_due(lead) is False

    def test_fu1_not_due_sent_half_day_ago(self):
        ts = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
        lead = make_lead(loom_followup_count=0, loom_sent_at=ts)
        assert is_due(lead) is False

    def test_fu1_due_sent_1_day_ago(self):
        lead = make_lead(loom_followup_count=0, loom_sent_at=days_ago(1))
        assert is_due(lead) is True

    def test_fu1_due_sent_5_days_ago(self):
        lead = make_lead(loom_followup_count=0, loom_sent_at=days_ago(5))
        assert is_due(lead) is True

    def test_fu2_not_due_last_fu_1_day_ago(self):
        lead = make_lead(loom_followup_count=1, loom_last_follow_up_at=days_ago(1))
        assert is_due(lead) is False

    def test_fu2_due_last_fu_2_days_ago(self):
        lead = make_lead(loom_followup_count=1, loom_last_follow_up_at=days_ago(2))
        assert is_due(lead) is True

    def test_fu3_not_due_last_fu_2_days_ago(self):
        lead = make_lead(loom_followup_count=2, loom_last_follow_up_at=days_ago(2))
        assert is_due(lead) is False

    def test_fu3_due_last_fu_3_days_ago(self):
        lead = make_lead(loom_followup_count=2, loom_last_follow_up_at=days_ago(3))
        assert is_due(lead) is True

    def test_fu4_not_due_last_fu_3_days_ago(self):
        lead = make_lead(loom_followup_count=3, loom_last_follow_up_at=days_ago(3))
        assert is_due(lead) is False

    def test_fu4_due_last_fu_4_days_ago(self):
        lead = make_lead(loom_followup_count=3, loom_last_follow_up_at=days_ago(4))
        assert is_due(lead) is True

    def test_missing_loom_sent_at_returns_false(self):
        lead = make_lead(loom_followup_count=0, loom_sent_at="")
        assert is_due(lead) is False

    def test_fu2_fallback_when_no_last_followup_date(self):
        lead = make_lead(loom_followup_count=1, loom_sent_at=days_ago(4), loom_last_follow_up_at="")
        assert is_due(lead) is True

    def test_fu2_fallback_not_due(self):
        lead = make_lead(loom_followup_count=1, loom_sent_at=days_ago(2), loom_last_follow_up_at="")
        assert is_due(lead) is False

    def test_string_count_handled(self):
        lead = make_lead(loom_followup_count="1", loom_last_follow_up_at=days_ago(2))
        assert is_due(lead) is True


# ---------------------------------------------------------------------------
# has_replied
# ---------------------------------------------------------------------------

class TestHasReplied:
    def _mock_response(self, emails):
        resp = MagicMock()
        resp.json.return_value = {"items": emails}
        resp.raise_for_status = MagicMock()
        return resp

    @patch("pipeline.requests.get")
    def test_detects_reply_from_lead(self, mock_get):
        mock_get.return_value = self._mock_response([
            {"from_address": "test@example.com", "body": "Thanks"},
        ])
        assert has_replied("thread-123", "test@example.com") is True

    @patch("pipeline.requests.get")
    def test_no_reply_when_only_outbound(self, mock_get):
        mock_get.return_value = self._mock_response([
            {"from_address": "jordan@automlette.com"},
        ])
        assert has_replied("thread-123", "test@example.com") is False

    @patch("pipeline.requests.get")
    def test_no_reply_empty_thread(self, mock_get):
        mock_get.return_value = self._mock_response([])
        assert has_replied("thread-123", "test@example.com") is False

    @patch("pipeline.requests.get")
    def test_case_insensitive_email_match(self, mock_get):
        mock_get.return_value = self._mock_response([{"from_address": "TEST@EXAMPLE.COM"}])
        assert has_replied("thread-123", "test@example.com") is True

    @patch("pipeline.requests.get")
    def test_case_insensitive_lead_email(self, mock_get):
        mock_get.return_value = self._mock_response([{"from_address": "test@example.com"}])
        assert has_replied("thread-123", "TEST@EXAMPLE.COM") is True

    @patch("pipeline.requests.get")
    def test_api_error_returns_false_fail_open(self, mock_get):
        import requests as req
        mock_get.side_effect = req.RequestException("connection error")
        assert has_replied("thread-123", "test@example.com") is False

    @patch("pipeline.requests.get")
    def test_multiple_emails_reply_in_any(self, mock_get):
        mock_get.return_value = self._mock_response([
            {"from_address": "jordan@automlette.com"},
            {"from_address": "jordan@automlette.com"},
            {"from_address": "test@example.com"},
        ])
        assert has_replied("thread-123", "test@example.com") is True

    @patch("pipeline.requests.get")
    def test_from_field_fallback(self, mock_get):
        mock_get.return_value = self._mock_response([{"from": "test@example.com"}])
        assert has_replied("thread-123", "test@example.com") is True

    def test_empty_thread_id_returns_false(self):
        assert has_replied("", "test@example.com") is False


# ---------------------------------------------------------------------------
# render_template
# ---------------------------------------------------------------------------

class TestRenderTemplate:
    def test_fu1_renders_first_name(self):
        lead = make_lead(first_name="Sarah", sender_first_name="Jordan")
        _, body = render_template(FOLLOWUP_TEMPLATES[1], lead)
        assert "Sarah" in body
        assert "Jordan" in body

    def test_fu2_renders_correctly(self):
        lead = make_lead(first_name="Ray", sender_first_name="Jordan")
        _, body = render_template(FOLLOWUP_TEMPLATES[2], lead)
        assert "Ray" in body

    def test_fu3_renders_correctly(self):
        lead = make_lead(first_name="Elena", sender_first_name="James")
        _, body = render_template(FOLLOWUP_TEMPLATES[3], lead)
        assert "Elena" in body
        assert "summary" in body.lower()

    def test_fu4_breakup_copy(self):
        lead = make_lead(first_name="Matt", sender_first_name="Peter")
        _, body = render_template(FOLLOWUP_TEMPLATES[4], lead)
        assert "last" in body.lower()

    def test_sender_first_name_fallback_to_eaccount(self):
        lead = make_lead(sender_first_name="", eaccount="sarah@goautomlette.com")
        _, body = render_template(FOLLOWUP_TEMPLATES[1], lead)
        assert "sarah" in body

    def test_all_four_templates_exist(self):
        for i in range(1, 5):
            assert i in FOLLOWUP_TEMPLATES
            assert "body" in FOLLOWUP_TEMPLATES[i]

    def test_no_unrendered_placeholders(self):
        lead = make_lead(first_name="Alex", sender_first_name="Jordan")
        for i in range(1, 5):
            _, body = render_template(FOLLOWUP_TEMPLATES[i], lead)
            assert "{" not in body, f"Unrendered placeholder in FU#{i}: {body}"


# ---------------------------------------------------------------------------
# update_lead_after_send
# ---------------------------------------------------------------------------

class TestUpdateLeadAfterSend:
    def _make_sheet(self, headers, email="test@example.com"):
        sheet = MagicMock()
        sheet.col_values.return_value = ["lead_email", email]
        sheet.row_values.return_value = headers
        return sheet

    def test_dry_run_makes_no_calls(self):
        sheet = MagicMock()
        update_lead_after_send(sheet, make_lead(), 1, "new-uuid", "2026-04-19T00:00:00Z", dry_run=True)
        sheet.update_cell.assert_not_called()

    def test_increments_count(self):
        headers = ["lead_email", "loom_followup_count", "loom_last_follow_up_at", "reply_to_uuid", "status"]
        sheet = self._make_sheet(headers)
        update_lead_after_send(sheet, make_lead(), 2, "uuid", "2026-04-19T00:00:00Z", dry_run=False)
        sheet.update_cell.assert_any_call(2, headers.index("loom_followup_count") + 1, 2)

    def test_updates_last_followup_date(self):
        headers = ["lead_email", "loom_followup_count", "loom_last_follow_up_at", "reply_to_uuid", "status"]
        sheet = self._make_sheet(headers)
        sent_at = "2026-04-19T12:00:00Z"
        update_lead_after_send(sheet, make_lead(), 1, "uuid", sent_at, dry_run=False)
        sheet.update_cell.assert_any_call(2, headers.index("loom_last_follow_up_at") + 1, sent_at)

    def test_sets_status_lost_at_count_4(self):
        headers = ["lead_email", "loom_followup_count", "loom_last_follow_up_at", "reply_to_uuid", "status"]
        sheet = self._make_sheet(headers)
        update_lead_after_send(sheet, make_lead(), 4, "uuid", "2026-04-19T00:00:00Z", dry_run=False)
        sheet.update_cell.assert_any_call(2, headers.index("status") + 1, "lost")

    def test_does_not_set_status_before_count_4(self):
        headers = ["lead_email", "loom_followup_count", "loom_last_follow_up_at", "reply_to_uuid", "status"]
        sheet = self._make_sheet(headers)
        update_lead_after_send(sheet, make_lead(), 3, "uuid", "2026-04-19T00:00:00Z", dry_run=False)
        calls = [str(c) for c in sheet.update_cell.call_args_list]
        assert not any("lost" in c for c in calls)

    def test_skips_uuid_update_when_none(self):
        headers = ["lead_email", "loom_followup_count", "loom_last_follow_up_at", "reply_to_uuid", "status"]
        sheet = self._make_sheet(headers)
        update_lead_after_send(sheet, make_lead(), 1, None, "2026-04-19T00:00:00Z", dry_run=False)
        uuid_col = headers.index("reply_to_uuid") + 1
        assert not any(c == call(2, uuid_col, None) for c in sheet.update_cell.call_args_list)


# ---------------------------------------------------------------------------
# Full pipeline integration tests
# ---------------------------------------------------------------------------

class TestPipeline:
    def _make_mock_sheet(self, leads):
        sheet = MagicMock()
        sheet.get_all_records.return_value = leads
        emails = ["lead_email"] + [l["lead_email"] for l in leads]
        sheet.col_values.return_value = emails
        sheet.row_values.return_value = list(leads[0].keys()) if leads else []
        return sheet

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied", return_value=False)
    @patch("pipeline.send_reply", return_value="new-uuid")
    @patch("pipeline.update_lead_after_send")
    def test_skips_non_loom_sent_status(self, mock_update, mock_send, mock_replied, mock_sheet):
        mock_sheet.return_value = self._make_mock_sheet([make_lead(status="lost", loom_sent_at=days_ago(5))])
        run(dry_run=False)
        mock_send.assert_not_called()

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied", return_value=False)
    @patch("pipeline.send_reply", return_value="new-uuid")
    @patch("pipeline.update_lead_after_send")
    def test_skips_count_at_4(self, mock_update, mock_send, mock_replied, mock_sheet):
        mock_sheet.return_value = self._make_mock_sheet([make_lead(loom_followup_count=4, loom_sent_at=days_ago(10))])
        run(dry_run=False)
        mock_send.assert_not_called()

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied", return_value=False)
    @patch("pipeline.send_reply", return_value="new-uuid")
    @patch("pipeline.update_lead_after_send")
    def test_skips_when_not_yet_due(self, mock_update, mock_send, mock_replied, mock_sheet):
        mock_sheet.return_value = self._make_mock_sheet([make_lead(loom_followup_count=0, loom_sent_at=days_ago(0))])
        run(dry_run=False)
        mock_send.assert_not_called()

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied", return_value=True)
    @patch("pipeline.send_reply")
    @patch("pipeline.update_lead_after_send")
    def test_skips_and_does_not_send_when_replied(self, mock_update, mock_send, mock_replied, mock_sheet):
        """Critical: if lead has replied, NEVER send and NEVER update the sheet."""
        mock_sheet.return_value = self._make_mock_sheet([make_lead(loom_sent_at=days_ago(2))])
        run(dry_run=False)
        mock_send.assert_not_called()
        mock_update.assert_not_called()

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied", return_value=True)
    @patch("pipeline.send_reply")
    @patch("pipeline.update_lead_after_send")
    def test_multiple_replied_leads_none_sent(self, mock_update, mock_send, mock_replied, mock_sheet):
        leads = [
            make_lead(lead_email="a@x.com", loom_sent_at=days_ago(3)),
            make_lead(lead_email="b@x.com", loom_followup_count=2, loom_sent_at=days_ago(10)),
            make_lead(lead_email="c@x.com", loom_followup_count=3, loom_sent_at=days_ago(15)),
        ]
        mock_sheet.return_value = self._make_mock_sheet(leads)
        run(dry_run=False)
        mock_send.assert_not_called()
        mock_update.assert_not_called()

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied", return_value=False)
    @patch("pipeline.send_reply", return_value="new-uuid")
    @patch("pipeline.update_lead_after_send")
    def test_sends_fu1_for_count_0(self, mock_update, mock_send, mock_replied, mock_sheet):
        mock_sheet.return_value = self._make_mock_sheet([make_lead(loom_followup_count=0, loom_sent_at=days_ago(2))])
        run(dry_run=False)
        mock_send.assert_called_once()
        body = mock_send.call_args[0][2]
        assert "check in" in body.lower()

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied", return_value=False)
    @patch("pipeline.send_reply", return_value="new-uuid")
    @patch("pipeline.update_lead_after_send")
    def test_sends_fu3_for_count_2(self, mock_update, mock_send, mock_replied, mock_sheet):
        mock_sheet.return_value = self._make_mock_sheet([make_lead(loom_followup_count=2, loom_last_follow_up_at=days_ago(4))])
        run(dry_run=False)
        body = mock_send.call_args[0][2]
        assert "summary" in body.lower()

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied", return_value=False)
    @patch("pipeline.send_reply", return_value="new-uuid")
    @patch("pipeline.update_lead_after_send")
    def test_sends_fu4_breakup_for_count_3(self, mock_update, mock_send, mock_replied, mock_sheet):
        mock_sheet.return_value = self._make_mock_sheet([make_lead(loom_followup_count=3, loom_last_follow_up_at=days_ago(5))])
        run(dry_run=False)
        body = mock_send.call_args[0][2]
        assert "last" in body.lower()

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied", return_value=False)
    @patch("pipeline.send_reply", return_value="new-uuid")
    @patch("pipeline.update_lead_after_send")
    def test_calls_update_after_successful_send(self, mock_update, mock_send, mock_replied, mock_sheet):
        mock_sheet.return_value = self._make_mock_sheet([make_lead(loom_sent_at=days_ago(2))])
        run(dry_run=False)
        mock_update.assert_called_once()
        assert mock_update.call_args[0][2] == 1  # new_count

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied", return_value=False)
    @patch("pipeline.send_reply", return_value=None)
    @patch("pipeline.update_lead_after_send")
    def test_does_not_update_sheet_on_send_failure(self, mock_update, mock_send, mock_replied, mock_sheet):
        """If send fails, sheet must NOT be updated so it retries next run."""
        mock_sheet.return_value = self._make_mock_sheet([make_lead(loom_sent_at=days_ago(2))])
        run(dry_run=False)
        mock_update.assert_not_called()

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied", return_value=False)
    @patch("pipeline.send_reply", return_value="new-uuid")
    @patch("pipeline.update_lead_after_send")
    def test_mixed_leads_only_eligible_sent(self, mock_update, mock_send, mock_replied, mock_sheet):
        leads = [
            make_lead(lead_email="eligible@x.com", loom_sent_at=days_ago(2)),
            make_lead(lead_email="not_due@x.com", loom_sent_at=days_ago(0)),
            make_lead(lead_email="lost@x.com", status="lost", loom_sent_at=days_ago(5)),
            make_lead(lead_email="maxed@x.com", loom_followup_count=4, loom_sent_at=days_ago(20)),
        ]
        mock_sheet.return_value = self._make_mock_sheet(leads)
        run(dry_run=False)
        assert mock_send.call_count == 1
        assert mock_send.call_args[0][0]["lead_email"] == "eligible@x.com"

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied")
    @patch("pipeline.send_reply", return_value="new-uuid")
    @patch("pipeline.update_lead_after_send")
    def test_reply_check_called_with_correct_args(self, mock_update, mock_send, mock_replied, mock_sheet):
        mock_replied.return_value = False
        lead = make_lead(lead_email="specific@example.com", thread_id="specific-thread", loom_sent_at=days_ago(2))
        mock_sheet.return_value = self._make_mock_sheet([lead])
        run(dry_run=False)
        mock_replied.assert_called_once_with("specific-thread", "specific@example.com")

    @patch("pipeline.get_sheet")
    @patch("pipeline.has_replied", return_value=False)
    @patch("pipeline.send_reply", return_value="new-uuid")
    @patch("pipeline.update_lead_after_send")
    def test_dry_run_passes_flag_to_send(self, mock_update, mock_send, mock_replied, mock_sheet):
        mock_sheet.return_value = self._make_mock_sheet([make_lead(loom_sent_at=days_ago(2))])
        run(dry_run=True)
        mock_send.assert_called_once()
        assert mock_send.call_args[0][3] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
