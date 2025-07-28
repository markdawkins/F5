import getpass
import smtplib
from email.message import EmailMessage
from netmiko import ConnectHandler
from datetime import datetime
from openpyxl import Workbook

# ===== ROUTERS TO CHECK =====
router_ips = [
    "192.168.1.159",
    "192.168.1.166",
    "192.168.1.164",
    "192.168.1.156"
]

# ===== CREDENTIAL PROMPTS =====
username = input("Enter your SSH username: ")
password = getpass.getpass("Enter your SSH password: ")
sender_email = "code.lab.072025@gmail.com"  # Replace with your Gmail address
receiver_email = "mark.dawkins@gmail.com"
email_password = ("email_password_goes_here")

# ===== OUTPUT FILE =====
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
excel_filename = f"ntp_report_all_{timestamp}.xlsx"

# ===== CREATE WORKBOOK =====
wb = Workbook()
ws = wb.active
ws.title = "NTP Report"

# ===== HEADERS =====
headers = ["Router IP", "Timestamp", "NTP Status Line", "Assoc Address", "Ref Clock", "Stratum", "When", "Poll", "Reach", "Delay", "Offset", "Disp"]
ws.append(headers)

# ===== BEGIN PROCESSING =====
for router_ip in router_ips:
    print(f"\nConnecting to {router_ip}...")
    device = {
        "device_type": "cisco_ios",
        "host": router_ip,
        "username": username,
        "password": password,
    }

    try:
        connection = ConnectHandler(**device)

        ntp_status = connection.send_command("show ntp status")
        ntp_assoc = connection.send_command("show ntp associations")

        timestamp_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        assoc_lines = ntp_assoc.strip().splitlines()
        for line in assoc_lines:
            if line.startswith("  ") or line.startswith("*") or line.startswith("~"):
                fields = line.split()
                if len(fields) >= 9:
                    assoc_address = fields[0].lstrip("*~")
                    ref_clock = fields[1]
                    stratum = fields[2]
                    when = fields[3]
                    poll = fields[4]
                    reach = fields[5]
                    delay = fields[6]
                    offset = fields[7]
                    disp = fields[8]

                    ws.append([
                        router_ip, timestamp_now, ntp_status,
                        assoc_address, ref_clock, stratum, when, poll, reach, delay, offset, disp
                    ])

        connection.disconnect()

    except Exception as e:
        print(f"Failed to connect to {router_ip}: {e}")

# ===== SAVE EXCEL FILE =====
wb.save(excel_filename)
print(f"\nExcel report saved as {excel_filename}")

# ===== EMAIL THE FILE =====
print(f"\nEmailing Excel report: {excel_filename}")

try:
    msg = EmailMessage()
    msg["Subject"] = f"NTP Multi-Router Report ({timestamp})"
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content("Attached is the multi-router NTP report in Excel format.")

    with open(excel_filename, "rb") as f:
        file_data = f.read()
        msg.add_attachment(file_data, maintype="application", subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=excel_filename)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, email_password)
        server.send_message(msg)

    print("\u2705 Report emailed successfully!")

except Exception as e:
    print(f"\u274C Email failed: {e}")
