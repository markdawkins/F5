###Quick script to run a show command against a short list of IPs dump the output to a csv file#####
import paramiko
import time
import getpass
import csv
from datetime import datetime

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
        #shell.send("show ntp status\n")
        shell.send("list /sys sshd all-properties\n") ########Commands go here. Multiple commands will work \n  needed for each command#####
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

def print_banner():
    """Prints a completion banner."""
    print("\n" + "="*50)
    print("✅ REPORT COMPLETED SUCCESSFULLY!")
    print("="*50)
    print(f"📁 Output saved to: f5_sshd_report.csv\n")

if __name__ == "__main__":
    F5_HOSTS = ["192.168.1.164", "192.168.1.166", "192.168.1.159", "192.168.1.160"]
    username, password = get_f5_credentials()
    
    print("\n" + "="*50)
    print("⚡ Starting SSH Data Collection...")
    print("="*50)
    
    for host in F5_HOSTS:
        output = f5_ssh_login(host, username, password)
        save_to_csv(host, output)
        status = "✅ SUCCESS" if not output.startswith("❌ ERROR") else "❌ FAILED"
        print(f"{host}: {status}")
    
    print_banner()
