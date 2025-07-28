from netmiko import ConnectHandler
import getpass

# Prompt user for router details
router_ip = input("Enter the router IP address: ")
username = input("Enter your SSH username: ")
password = getpass.getpass("Enter your SSH password: ")

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

    print("\nFetching NTP status...")
    ntp_status = net_connect.send_command("show ntp status")
    print("\n=== NTP STATUS ===")
    print(ntp_status)

    print("\nFetching NTP associations...")
    ntp_associations = net_connect.send_command("show ntp associations")
    print("\n=== NTP ASSOCIATIONS ===")
    print(ntp_associations)

    net_connect.disconnect()

except Exception as e:
    print(f"\nError: {e}")
