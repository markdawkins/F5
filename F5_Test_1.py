#!/usr/bin/env python
import paramiko
import time
import getpass
import datetime
import csv
import os

#subname = datetime.now().strftime("%Y%m%d-%H%M%S")

def f5_ssh_login(host, username, password, port=22):
    """
    Logs into an F5 device via SSH, executes tmsh command, and returns the output.

    Args:
        host (str): F5 device IP address or hostname
        username (str): SSH username
        password (str): SSH password
        port (int): SSH port (default: 22)

    Returns:
        str: Output of the command execution
    """
    # Initialize SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"Connecting to {host}...")
        ssh.connect(host, port=port, username=username, password=password, timeout=10)

        # Create an interactive shell
        shell = ssh.invoke_shell()

        # Wait for the shell to be ready
        time.sleep(1)

        # Send the tmsh command
        command = "tmsh list /sys sshd all-properties\n"
        #command = "show ip int brief\n" 
        shell.send(command)

        # Wait for command execution
        time.sleep(2)

        # Read the output
        output = ""
        while shell.recv_ready():
            output += shell.recv(4096).decode('utf-8')
            time.sleep(0.5)

        # Close the connection
        ssh.close()

        return output

    except Exception as e:

        print(f"An error occurred: {str(e)}")
        if ssh.get_transport() is not None and ssh.get_transport().is_active():
            ssh.close()
        return None

if __name__ == "__main__":
    # Configuration - replace with your F5 device details
    F5_HOST = input("your_f5_hostname_or_ip: ")
    F5_USERNAME = input("your_username: ")
    F5_PASSWORD = getpass.getpass("your_password: ")

    # Execute and capture output
    output = f5_ssh_login(F5_HOST, F5_USERNAME, F5_PASSWORD)

    if output:
        print(" ")
        print(F5_HOST)
        print(" ")
        print("\nCommand Output:")
        print("=" * 50)
        print(output)
        print("=" * 50)
        print(" ")

        # Optionally save to file
# Prepare timestamp and clean output
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
clean_output = output.replace('\n', '\\n').replace('\r', '').replace(',', ';')  # CSV-safe

csv_file = "f5_sshd_properties.csv"
file_exists = os.path.isfile(csv_file)

# Append CSV row
with open(csv_file, "a", newline='') as csvfile:
    writer = csv.writer(csvfile)
    if not file_exists:
        writer.writerow(["timestamp", "host", "command_output"])  # Write header if file is new
    writer.writerow([timestamp, F5_HOST, clean_output])

print(f"\nOutput appended to {csv_file}")
