import csv
import getpass
import smtplib
import os
from email.message import EmailMessage
from netmiko import ConnectHandler
from datetime import datetime
## APP PASSWORD zmwx obcm xwqe fzdc ###

# ===== USER INPUTS =====
router_ip = input("Enter the router IP address: ")
username = input("Enter your SSH username: ")
password = getpass.getpass("Enter your SSH password: ")

# Email credentials
smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "code.lab.072025@gmail.com"  # Replace with your Gmail address
receiver_email = "mark.dawkins@gmail.com"
#email_password = getpass.getpass("Enter the email password (App Password recommended): ")
email_password = "zmwx obcm xwqe fzdc"

# Timestamped filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename = f"ntp_report_{router_ip.replace('.', '_')}_{timestamp}.csv"

# ===== CONNECT TO DEVICE =====
device = {
    "device_type": "cisco_ios",
    "host": router_ip,
    "username": username,
    "password": password,
}

try:
    print(f"\nConnecting to {router_ip}...")
    connection = ConnectHandler(**device)

    print("Fetching NTP status...")
    ntp_status_raw = connection.send_command("show ntp status")

    print("Fetching NTP associations...")
    ntp_associations_raw = connection.send_command("show ntp associations")

    connection.disconnect()

except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

# ===== PARSE & SAVE TO CSV =====
print(f"Saving results to {csv_filename}...")

with open(csv_filename, mode="w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Router IP", "Timestamp", "NTP Status", "NTP Associations"])
    writer.writerow([router_ip, timestamp, ntp_status_raw, ntp_associations_raw])

# ===== EMAIL THE CSV =====
print(f"Sending email to {receiver_email}...")

try:
    msg = EmailMessage()
    msg["Subject"] = f"NTP Report for {router_ip} ({timestamp})"
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content("Attached is the NTP report in CSV format.")

    with open(csv_filename, "rb") as f:
        file_data = f.read()
        msg.add_attachment(file_data, maintype="text", subtype="csv", filename=csv_filename)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, email_password)
        server.send_message(msg)

    print("✅ Email sent successfully!")

except Exception as e:
    print(f"❌ Failed to send email: {e}")


