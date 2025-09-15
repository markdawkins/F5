import paramiko
import csv
from datetime import datetime
import getpass

# CSV file path
CSV_FILE = "serial_num_log.csv"

def get_f5_serial(host, username, password):
    """SSH into F5 and return only the Chassis Serial Number."""
    try:
        # Open SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=username, password=password)

        # Run tmsh command
        stdin, stdout, stderr = ssh.exec_command("tmsh show sys hardware | grep -i 'Chassis Serial'")

        output = stdout.read().decode().strip()
        error_output = stderr.read().decode().strip()
        ssh.close()

        # If there's no output, raise an error
        if not output:
            if error_output:
                return f"Command error: {error_output}"
            else:
                return "Error: No output from command (serial number not found)."

        # Example line: "Chassis Serial  : 1234XYZ"
        serial_number = output.split(":")[-1].strip() if ":" in output else output
        return serial_number

    except Exception as e:
        return f"Connection/Execution Error: {e}"

def log_serial_to_csv(host, serial):
    """Append timestamp, host, and serial to CSV log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CSV_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, host, serial])

if __name__ == "__main__":
    # Prompt user for F5 login details
    host = input("Enter F5 host IP or hostname: ")
    username = input("Enter F5 username: ")
    password = getpass.getpass("Enter F5 password: ")

    # Get serial number
    serial = get_f5_serial(host, username, password)

    # Print result to screen
    print(f"Result for {host}: {serial}")

    # Log to CSV (even errors, so you know it was attempted)
    log_serial_to_csv(host, serial)
