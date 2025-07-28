
import paramiko
import time
import getpass
import csv
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "code.lab.072025@gmail.com"
RECEIVER_EMAIL = "mark.dawkins@gmail.com"
EMAIL_PASSWORD = "your_app_password_here"  # Use App Password for Gmail

def get_f5_credentials():
    """Prompt user for F5 device credentials."""
    print("\n" + "="*50)
    print("F5 SSH Configuration Report Tool")
    print("="*50)
    username = input("\nUsername: ").strip()
    password = getpass.getpass("Password: ").strip()
    return username, password

def f5_ssh_login(host, username, password, port=22):
    """Logs into an F5 device via SSH and executes command."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"\n🔌 Connecting to {host}...")
        ssh.connect(host, port=port, username=username, password=password, timeout=10)
        shell = ssh.invoke_shell()
        time.sleep(1)
        
        shell.send("tmsh list /sys sshd all-properties\n")
        time.sleep(2)
        
        output = ""
        while shell.recv_ready():
            output += shell.recv(4096).decode('utf-8')
            time.sleep(0.5)
        
        return output.strip()
    
    except Exception as e:
        return f"❌ ERROR: {str(e)}"
    finally:
        if ssh.get_transport() is not None and ssh.get_transport().is_active():
            ssh.close()

def save_to_csv(host, output, filename="f5_sshd_report.csv"):
    """Appends results to a single CSV file with timestamp and blank line separation."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header if file is empty
        if csvfile.tell() == 0:
            writer.writerow(["Timestamp", "Host", "Output"])
        
        # Write host header
        writer.writerow([timestamp, host, "="*50])
        
        # Split output into lines and write each line
        for line in output.split('\n'):
            if line.strip():  # Skip empty lines in the output
                writer.writerow([timestamp, host, line.strip()])
        
        # Add blank line separator
        writer.writerow([])

def send_email_with_attachment(filename):
    """Sends the CSV report via email."""
    try:
        # Create message container
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = f"F5 SSH Configuration Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Email body
        body = """Please find attached the F5 SSH configuration report.
        
This report contains the SSH configuration details for all monitored F5 devices.
"""
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach CSV file
        with open(filename, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {filename}",
        )
        msg.attach(part)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print(f"\n📧 Email sent successfully to {RECEIVER_EMAIL}")
        return True
    
    except Exception as e:
        print(f"\n❌ Failed to send email: {str(e)}")
        return False

def print_banner():
    """Prints a completion banner."""
    print("\n" + "="*50)
    print("✅ REPORT COMPLETED SUCCESSFULLY!")
    print("="*50)
    print(f"📁 Output saved to: f5_sshd_report.csv\n")

if __name__ == "__main__":
    F5_HOSTS = ["192.168.1.164", "192.168.1.166", "192.168.1.159" , "192.168.1.160"]
    username, password = get_f5_credentials()
    
    print("\n" + "="*50)
    print("⚡ Starting SSH Data Collection...")
    print("="*50)
    
    # Clear existing report file
    open("f5_sshd_report.csv", "w").close()
    
    for host in F5_HOSTS:
        output = f5_ssh_login(host, username, password)
        save_to_csv(host, output)
        status = "✅ SUCCESS" if not output.startswith("❌ ERROR") else "❌ FAILED"
        print(f"{host}: {status}")
    
    # Send email with report
    email_sent = send_email_with_attachment("f5_sshd_report.csv")
    
    print_banner()
