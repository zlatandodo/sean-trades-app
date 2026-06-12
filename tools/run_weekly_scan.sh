#!/bin/bash
# Weekly Sean Trades Scanner Runner
# Scheduled: Every Sunday at 18:00
#
# To install cron job:
#   crontab -e
#   Add: 0 18 * * 0 /Users/dodomac/Desktop/dodosean/tools/run_weekly_scan.sh

PROJECT_DIR="/Users/dodomac/Desktop/dodosean"
LOG_FILE="$PROJECT_DIR/.tmp/scanner.log"
RESULTS_DIR="$PROJECT_DIR/.tmp"

mkdir -p "$RESULTS_DIR"

echo "=====================================" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting weekly scan" >> "$LOG_FILE"

cd "$PROJECT_DIR" && python3 tools/scanner_sean_trades.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Scan completed successfully" >> "$LOG_FILE"
    # Get today's results file
    RESULTS_FILE=$(ls -t "$RESULTS_DIR"/scan_results_*.csv 2>/dev/null | head -1)
    if [ -n "$RESULTS_FILE" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Results saved to: $RESULTS_FILE" >> "$LOG_FILE"
        # Count A+ and A setups
        A_PLUS=$(tail -n +2 "$RESULTS_FILE" | awk -F',' '$2=="A+"' | wc -l | tr -d ' ')
        A=$(tail -n +2 "$RESULTS_FILE" | awk -F',' '$2=="A"' | wc -l | tr -d ' ')
        echo "$(date '+%Y-%m-%d %H:%M:%S') - A+ setups: $A_PLUS | A setups: $A" >> "$LOG_FILE"
    fi
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: Scan failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

echo "=====================================" >> "$LOG_FILE"
