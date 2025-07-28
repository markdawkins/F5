import paramiko
from netmiko import ConnectHandler
from getpass import getpass

def main():
    print("\n=== Cisco Router SNMP Configuration Tool ===\n")

    # Prompt for device info
    ip = input("Enter router IP address: ")
    username = input("Enter SSH username: ")
    password = getpass("Enter SSH password: ")

    # Define the Cisco device
    device = {
        'device_type': 'cisco_ios',
        'host': ip,
        'username': username,
        'password': password,
    }

    try:
        # Connect to the device
        print(f"\nConnecting to {ip}...")
        connection = ConnectHandler(**device)

        # SNMP configuration commands
        snmp_commands = [
            'snmp-server community cville RO',
            'snmp-server community cville2 RW',
            'snmp-server location Proxmox Cluster-1',
            'snmp-server contact mgdawkins2019@gmail.com',
            'snmp-server enable traps',
            'snmp-server host 192.168.1.253 version 2c cville ',
        ]

        print("Sending SNMP configuration commands...")
        output = connection.send_config_set(snmp_commands)

        print("\n--- SNMP Configuration Output ---")
        print(output)

        # Save the configuration
        print("Saving configuration...")
        save_output = connection.save_config()
        print(save_output)

        # Close connection
        connection.disconnect()
        print("\n✅ SNMP configuration completed successfully.")

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
