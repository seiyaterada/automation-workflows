#!/bin/bash
# Runs the loom follow-up Claude routine.
# Schedule with cron or any external scheduler (n8n, Make, etc).
#
# Cron example (daily at 9am):
#   0 9 * * * /home/user/automation-workflows/routines/run_loom_followup.sh
#
# Logs are written to logs/loom_followup_YYYY-MM-DD.log

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/loom_followup_$(date +%Y-%m-%d).log"
ROUTINE="$PROJECT_DIR/routines/loom_followup.md"

mkdir -p "$LOG_DIR"

echo "========================================" >> "$LOG_FILE"
echo "Run started: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

cd "$PROJECT_DIR"

claude -p "$(cat "$ROUTINE")" >> "$LOG_FILE" 2>&1

echo "Run finished: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
