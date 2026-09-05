#!/bin/bash
set -euo pipefail

# Add cron job to run deploy.sh every 5 minutes
CRON_LINE="*/5 * * * * /root/BEAR/dashboard/deploy.sh >> /root/BEAR/dashboard/deploy.log 2>&1"

# Remove existing entry if present, then add
(crontab -l 2>/dev/null | grep -v "dashboard/deploy.sh" ; echo "$CRON_LINE") | crontab -

echo "Cron installed: deploy.sh every 5 minutes"
echo "Current crontab:"
crontab -l
