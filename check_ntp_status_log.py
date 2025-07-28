from netmiko import ConnectHandler
import getpass
from datetime import datetime
import os

# Prompt user for router info
router_ip = input("Enter the router IP address: ")
username = input("Enter your SSH username: ")
password = getpass.getpass("Enter your SSH password: ")

# Timestamp for filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"ntp_report_{router_ip.replace('.', '_')}_{timestamp}.txt"

# Netmiko connection dictionary
cisco_device = {
    "device_type": "cisco_ios",
    "host": router_ip,
    "username": username,
    "password": password,
}

try:
    print(f"\nConnecting to {router_ip}...")
    net_connect = ConnectHandler(**cisco_device)

    print("Fetching NTP status...")
    ntp_status = net_connect.send_command("show ntp status")

    print("Fetching NTP associations...")
    ntp_associations = net_connect.send_command("show ntp associations")

    net_connect.disconnect()

    # Combine output
    report = (
        f"=== NTP STATUS ({router_ip}) ===\n{ntp_status}\n\n"
        f"=== NTP ASSOCIATIONS ({router_ip}) ===\n{ntp_associations}\n"
    )

    # Write to file
    with open(log_filename, "w") as log_file:
        log_file.write(report)

    print("\n--- Output ---")
    print(report)
    print(f"✅ NTP report saved to: {os.path.abspath(log_filename)}")

except Exception as e:
    print(f"\nError: {e}")
