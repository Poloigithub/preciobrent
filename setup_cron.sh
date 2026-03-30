#!/usr/bin/env bash
# setup_cron.sh – installs a cron job that runs brent_price.py update every day at 07:00
# Run once:  bash setup_cron.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3)"
LOG="$SCRIPT_DIR/brent_update.log"

CRON_LINE="0 7 * * * cd \"$SCRIPT_DIR\" && $PYTHON brent_price.py update >> \"$LOG\" 2>&1"

# Check if the cron entry already exists to avoid duplicates
if crontab -l 2>/dev/null | grep -qF "brent_price.py update"; then
    echo "Cron job already exists. No changes made."
else
    # Append to existing crontab (or create one if empty)
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "Cron job installed:"
    echo "  $CRON_LINE"
fi

echo ""
echo "Current crontab:"
crontab -l
