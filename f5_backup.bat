#!/bin/bash

# Get the network route to IP 10.219.64.17, take first line only, and extract gateway IP and interface
# Format: gateway_ip - interface_name
ip route get 10.X.X.X | head -n1 | awk '{print $3" - "$5}'

# Download backup.py script from LibreNMS server and save to /shared/ directory
curl -o /shared/backup.py https://librenms.sys1.com/f5/backup.py

# Make the backup script executable
chmod +x /shared/backup.py

# Display current crontab and save a backup copy to /shared/crontab.backup
crontab -l | tee /shared/crontab.backup 

# Comment out any existing backup script entries in crontab and add new backup schedule
# Runs backup.py at 1:30 AM on Monday, Thursday, Saturday (cron days: 1,4,6 where 0=Sunday)
# All output is redirected to /dev/null to prevent email notifications
(crontab -l | sed -e '/backup.[sh|py]/s/^#*/#/' 2>/dev/null; echo "30 1 * * 1,4,6 /shared/backup.py >/dev/null 2>&1") | crontab -

# Display the current crontab to verify the new entry was added
crontab -l

# Additional backup line (if needed) - same as above but ensures proper commenting of existing entries
(crontab -l | sed -e '/backup.[sh|py]/ s/^#*/#/' 2>/dev/null; echo "30 1 * * 1,4,6 /shared/backup.py >/dev/null 2>&1") | crontab -



#### NOTES #############

# What the Script Does:
# Network diagnostics: Checks route to a specific IP

# Download backup utility: Fetches a Python backup script from a LibreNMS server

# Set up automation: Configures cron to run the backup script at 1:30 AM on Mondays, Thursdays, and Saturdays

# Safety measures: Backs up existing crontab and comments out any conflicting backup entries

# The corrected cron schedule 30 1 * * 1,4,6 means:

# Minute: 30

# Hour: 1 (1 AM)

# Day of month: * (every day)

# Month: * (every month)

# Day of week: 1,4,6 (Monday, Thursday, Saturday)

