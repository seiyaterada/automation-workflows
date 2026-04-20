#!/bin/bash
# Runs the loom follow-up Claude routine.
# Schedule with cron or any external scheduler (n8n, Make, etc).
#
# Cron example (daily at 9am):
#   0 9 * * * /path/to/project/skills/loom_followup/run_routine.sh
#
# Logs are written to logs/loom_followup_YYYY-MM-DD.log in the project root.

set -e

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SKILL_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/loom_followup_$(date +%Y-%m-%d).log"
ROUTINE="$SKILL_DIR/routine.md"

mkdir -p "$LOG_DIR"

echo "========================================" >> "$LOG_FILE"
echo "Run started: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

cd "$PROJECT_DIR"

claude -p "$(cat "$ROUTINE")" >> "$LOG_FILE" 2>&1

echo "Run finished: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
