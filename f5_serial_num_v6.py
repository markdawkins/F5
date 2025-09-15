import paramiko
import csv
from datetime import datetime
import getpass

# CSV file path
CSV_FILE = "serial_num_log.csv"

def get_f5_serials(host, username, password):
    """SSH into F5 and return Chassis Serial and Appliance Serial numbers if available."""
    try:
        # Open SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=username, password=password)

        # Run tmsh command
        stdin, stdout, stderr = ssh.exec_command("tmsh show sys hardware")

        output = stdout.read().decode().strip()
        error_output = stderr.read().decode().strip()
        ssh.close()

        if error_output:
            return f"Command error: {error_output}", None

        if not output:
            return "Error: No output from command", None

        chassis_serial = None
        appliance_serial = None

        for line in output.splitlines():
            if "Chassis Serial" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    chassis_serial = parts[1].strip()
            elif "Appliance Serial" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    appliance_serial = parts[1].strip()

        if not chassis_serial and not appliance_serial:
            return "Error: No serial numbers found", None

        return chassis_serial, appliance_serial

    except Exception as e:
        return f"Connection/Execution Error: {e}", None

def log_serial_to_csv(host, chassis_serial, appliance_serial):
    """Append timestamp, host, chassis serial, and appliance serial to CSV log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, host, chassis_serial or "N/A", appliance_serial or "N/A"])

if __name__ == "__main__":
    # Prompt user for F5 login details
    host = input("Enter F5 host IP or hostname: ")
    username = input("Enter F5 username: ")
    password = getpass.getpass("Enter F5 password: ")

    # Get serial numbers
    chassis_serial, appliance_serial = get_f5_serials(host, username, password)

    # Print result to screen
    print(f"\nResults for {host}:")
    print(f"  Chassis Serial   : {chassis_serial if chassis_serial else 'N/A'}")
    print(f"  Appliance Serial : {appliance_serial if appliance_serial else 'N/A'}")

    # Log to CSV
    log_serial_to_csv(host, chassis_serial, appliance_serial)
    print(f"\nLogged to {CSV_FILE}")
