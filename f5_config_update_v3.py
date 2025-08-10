import paramiko
import getpass
import csv
from datetime import datetime

# Function to connect to F5 device and run TMOS commands
def run_f5_commands(host, username, password):
    # Commands to run on the F5 device
    commands = [
        "list /sys sshd all-properties",
        "modify /sys sshd include \"Ciphers aes256,arcfour128,arcfour256,arcfour\"",
        "save sys config",
        "list /sys sshd all-properties"
    ]

    # CSV log file name
    log_file = "f5_ssh_update_log.csv"

    try:
        # Create SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {host}...")
        ssh.connect(hostname=host, username=username, password=password)

        # Run each command in sequence
        for cmd in commands:
            print(f"\nRunning: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode()
            error = stderr.read().decode()

            # Print command results
            if output:
                print(output.strip())
            if error:
                print("Error:", error.strip())

        ssh.close()
        status = "Update completed successfully"
        print(f"\n{status}")

    except Exception as e:
        status = f"Connection failed: {e}"
        print(status)

    # Append result to CSV log file with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, host, status])


if __name__ == "__main__":
    # Prompt for connection details
    host = input("Enter F5 device IP address or hostname: ").strip()
    username = input("Enter username: ").strip()
    password = getpass.getpass("Enter password: ")

    # Run update process
    run_f5_commands(host, username, password)
