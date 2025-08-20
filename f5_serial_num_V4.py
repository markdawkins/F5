import paramiko
import csv
import getpass
import re
import time
from datetime import datetime
import socket

def connect_to_f5_ssh():
    """
    Establish SSH connection to F5 BIG-IP device and execute 'show sys hardware' command.
    
    Returns:
        tuple: (command_output, hostname) or (None, None) if failed
    """
    # Get connection details from user
    host = input("Enter F5 BIG-IP IP address or hostname: ")
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    
    # F5 typically uses SSH port 22
    ssh_port = 22
    
    # Create SSH client instance
    ssh_client = paramiko.SSHClient()
    
    # Automatically add host keys (use with caution in production)
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to F5 BIG-IP {host} via SSH...")
        
        # Establish SSH connection with timeout
        ssh_client.connect(
            hostname=host,
            port=ssh_port,
            username=username,
            password=password,
            timeout=15,  # Longer timeout for F5 devices
            look_for_keys=False,
            allow_agent=False
        )
        
        # Create interactive shell session
        print("Establishing SSH shell session...")
        shell = ssh_client.invoke_shell()
        
        # Wait for the shell to be ready and read initial output
        time.sleep(3)
        initial_output = shell.recv(5000).decode('utf-8')
        
        # Check if we're at the F5 prompt (typically ends with ]# or ]$)
        if not any(prompt in initial_output for prompt in [']#', ']$', ':']):
            print("Waiting for F5 prompt...")
            time.sleep(2)
            shell.send("\n")  # Send enter to get prompt
            time.sleep(2)
            initial_output = shell.recv(5000).decode('utf-8')
        
        # Send the show sys hardware command
        print("Executing 'show sys hardware' command...")
        shell.send("show sys hardware\n")
        
        # Wait for command to execute
        time.sleep(5)
        
        # Initialize output buffer
        output = ""
        max_wait_time = 30  # Maximum time to wait for command completion
        start_time = time.time()
        
        # Read output until command completion or timeout
        while time.time() - start_time < max_wait_time:
            if shell.recv_ready():
                chunk = shell.recv(4096).decode('utf-8')
                output += chunk
                
                # F5 commands typically complete with a prompt (]# or ]$)
                if any(prompt in chunk for prompt in [']#', ']$']):
                    break
            else:
                time.sleep(1)
        
        # Clean up the output - remove the command echo and prompt
        output = output.replace("show sys hardware", "").strip()
        
        # Remove F5 prompt from the end
        output = re.sub(r'[\r\n]*.*[\]\#\$][\r\n]*$', '', output)
        output = output.replace("\r\n", "\n")
        
        # Close SSH connection
        ssh_client.close()
        
        print("SSH connection closed successfully.")
        return output, host
        
    except paramiko.AuthenticationException:
        print("Authentication failed. Please check your credentials.")
        return None, None
    except paramiko.SSHException as ssh_err:
        print(f"SSH connection error: {ssh_err}")
        return None, None
    except socket.timeout:
        print("Connection timed out. Check network connectivity.")
        return None, None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None, None
    finally:
        # Ensure SSH client is always closed
        if ssh_client:
            ssh_client.close()

def parse_f5_hardware(output):
    """
    Parse the 'show sys hardware' output and extract key F5 hardware information.
    
    Args:
        output (str): Raw output from the 'show sys hardware' command
        
    Returns:
        dict: Parsed information with various F5 hardware details
    """
    if not output:
        return {"error": "No output received from F5 device"}
    
    parsed_data = {}
    
    # Regex patterns to extract specific information from F5 hardware output
    patterns = {
        'chassis_type': r'Chassis Type\s+(.+)',
        'platform': r'Platform\s+(.+)',
        'serial_number': r'Serial Number\s+(.+)',
        'hostname': r'Hostname\s+(.+)',
        'system_version': r'System Version\s+(.+)',
        'baseboard_serial': r'Baseboard Serial Number\s+(.+)',
        'manufacturer': r'Manufacturer\s+(.+)',
        'product_name': r'Product Name\s+(.+)',
        'cpu_model': r'CPU Model\s+(.+)',
        'cpu_speed': r'CPU Speed\s+(.+)',
        'cpu_cores': r'CPU Cores\s+(\d+)',
        'memory_total': r'Memory Total\s+([\d\.]+\s*[GMK]B)',
        'memory_slots_used': r'Memory Slots Used\s+(\d+)',
        'memory_slots_total': r'Memory Slots Total\s+(\d+)',
    }
    
    # Apply each regex pattern to extract information
    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            parsed_data[key] = match.group(1).strip()
        else:
            parsed_data[key] = "Not found"
    
    # Extract additional F5-specific information
    
    # CPU information
    cpu_info_match = re.search(r'CPU\s+([^\n]+)', output)
    if cpu_info_match and 'cpu_model' not in parsed_data:
        parsed_data['cpu_info'] = cpu_info_match.group(1).strip()
    
    # Memory information
    memory_match = re.search(r'Memory\s+([^\n]+)', output)
    if memory_match and 'memory_total' not in parsed_data:
        parsed_data['memory_info'] = memory_match.group(1).strip()
    
    # Disk information
    disk_match = re.findall(r'(\w+)\s+(\d+\.\d+ [GMK]B).*?(\d+\.\d+ [GMK]B).*?(\d+\.\d+ [GMK]B)', output)
    if disk_match:
        parsed_data['disk_info'] = "; ".join([f"{x[0]}: {x[1]} used of {x[3]}" for x in disk_match])
    
    # Interface information
    interfaces = re.findall(r'Interface\s+(\d+/\d+)\s+([^\n]+)', output)
    if interfaces:
        parsed_data['interface_count'] = str(len(interfaces))
        parsed_data['interfaces'] = "; ".join([f"{iface[0]}: {iface[1]}" for iface in interfaces[:5]]) + ("..." if len(interfaces) > 5 else "")
    
    # Power supply information
    psus = re.findall(r'Power Supply\s+(\d+)\s+([^\n]+)', output)
    if psus:
        parsed_data['power_supply_count'] = str(len(psus))
        parsed_data['power_supply_status'] = "; ".join([f"PSU{psu[0]}: {psu[1]}" for psu in psus])
    
    # Fan information
    fans = re.findall(r'Fan\s+(\d+)\s+([^\n]+)', output)
    if fans:
        parsed_data['fan_count'] = str(len(fans))
        parsed_data['fan_status'] = "; ".join([f"Fan{fan[0]}: {fan[1]}" for fan in fans[:3]]) + ("..." if len(fans) > 3 else "")
    
    return parsed_data

def save_to_csv(parsed_data, hostname):
    """
    Save parsed F5 hardware information to a CSV file.
    
    Args:
        parsed_data (dict): Parsed information from show sys hardware command
        hostname (str): F5 hostname or IP address
    """
    filename = "f5_hardware_results.csv"
    
    # Prepare data structure for CSV writing
    csv_data = {
        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'F5 Hostname': parsed_data.get('hostname', 'N/A'),
        'F5 IP Address': hostname,
        'Chassis Type': parsed_data.get('chassis_type', 'N/A'),
        'Platform': parsed_data.get('platform', 'N/A'),
        'Serial Number': parsed_data.get('serial_number', 'N/A'),
        'Baseboard Serial': parsed_data.get('baseboard_serial', 'N/A'),
        'Manufacturer': parsed_data.get('manufacturer', 'N/A'),
        'Product Name': parsed_data.get('product_name', 'N/A'),
        'System Version': parsed_data.get('system_version', 'N/A'),
        'CPU Model': parsed_data.get('cpu_model', parsed_data.get('cpu_info', 'N/A')),
        'CPU Cores': parsed_data.get('cpu_cores', 'N/A'),
        'CPU Speed': parsed_data.get('cpu_speed', 'N/A'),
        'Total Memory': parsed_data.get('memory_total', parsed_data.get('memory_info', 'N/A')),
        'Memory Slots Used': parsed_data.get('memory_slots_used', 'N/A'),
        'Memory Slots Total': parsed_data.get('memory_slots_total', 'N/A'),
        'Interface Count': parsed_data.get('interface_count', 'N/A'),
        'Power Supply Count': parsed_data.get('power_supply_count', 'N/A'),
        'Fan Count': parsed_data.get('fan_count', 'N/A'),
        'Disk Info': parsed_data.get('disk_info', 'N/A')
    }
    
    try:
        # Check if file exists to determine if headers are needed
        file_exists = False
        try:
            with open(filename, 'r'):
                file_exists = True
        except FileNotFoundError:
            pass
        
        # Write data to CSV file
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = list(csv_data.keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header only if file doesn't exist
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(csv_data)
        
        print(f"✓ Results successfully saved to {filename}")
        
    except Exception as e:
        print(f"✗ Error saving to CSV: {e}")

def save_raw_output(output, hostname):
    """
    Save raw command output to a text file for debugging and reference.
    
    Args:
        output (str): Raw output from the show sys hardware command
        hostname (str): F5 hostname or IP address
    """
    if output:
        # Create filename with timestamp for uniqueness
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"f5_hardware_raw_{hostname}_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Raw 'show sys hardware' output from F5 {hostname}\n")
                f.write("=" * 70 + "\n")
                f.write(f"Capture time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")
                f.write(output)
            
            print(f"✓ Raw output saved to {filename}")
            
        except Exception as e:
            print(f"✗ Error saving raw output: {e}")

def display_parsed_info(parsed_data):
    """
    Display parsed F5 hardware information in a formatted way to the console.
    
    Args:
        parsed_data (dict): Parsed information from show sys hardware command
    """
    print("\n" + "=" * 70)
    print("F5 BIG-IP HARDWARE INFORMATION:")
    print("=" * 70)
    
    # Display order for better readability
    display_order = [
        'hostname', 'chassis_type', 'platform', 'serial_number',
        'system_version', 'manufacturer', 'product_name',
        'cpu_model', 'cpu_cores', 'cpu_speed',
        'memory_total', 'memory_slots_used', 'memory_slots_total',
        'interface_count', 'power_supply_count', 'fan_count',
        'baseboard_serial'
    ]
    
    # Friendly names for display
    friendly_names = {
        'hostname': 'Hostname',
        'chassis_type': 'Chassis Type',
        'platform': 'Platform',
        'serial_number': 'Serial Number',
        'system_version': 'System Version',
        'manufacturer': 'Manufacturer',
        'product_name': 'Product Name',
        'cpu_model': 'CPU Model',
        'cpu_cores': 'CPU Cores',
        'cpu_speed': 'CPU Speed',
        'memory_total': 'Total Memory',
        'memory_slots_used': 'Memory Slots Used',
        'memory_slots_total': 'Memory Slots Total',
        'interface_count': 'Interface Count',
        'power_supply_count': 'Power Supply Count',
        'fan_count': 'Fan Count',
        'baseboard_serial': 'Baseboard Serial',
        'disk_info': 'Disk Information'
    }
    
    for key in display_order:
        if key in parsed_data and parsed_data[key] != "Not found":
            friendly_name = friendly_names.get(key, key.replace('_', ' ').title())
            print(f"{friendly_name:<25}: {parsed_data[key]}")
    
    # Display additional info if available
    additional_info = ['disk_info', 'interfaces', 'power_supply_status', 'fan_status']
    for info in additional_info:
        if info in parsed_data and parsed_data[info] != "Not found":
            friendly_name = friendly_names.get(info, info.replace('_', ' ').title())
            print(f"{friendly_name:<25}: {parsed_data[info]}")

def main():
    """
    Main function to orchestrate the SSH connection and data processing for F5.
    """
    print("F5 BIG-IP Hardware Information Script (SSH)")
    print("=" * 60)
    print("This script connects to an F5 BIG-IP device via SSH,")
    print("executes 'show sys hardware', and saves results to CSV.")
    print("=" * 60)
    
    # Check if paramiko is available
    try:
        import paramiko
    except ImportError:
        print("Error: paramiko module is required but not installed.")
        print("Install it using: pip install paramiko")
        return
    
    # Connect to F5 and get output
    output, host = connect_to_f5_ssh()
    
    if output and host:
        # Display raw output to screen
        print("\n" + "=" * 70)
        print("RAW SHOW SYS HARDWARE OUTPUT:")
        print("=" * 70)
        print(output)
        print("=" * 70)
        
        # Save raw output for debugging
        save_raw_output(output, host)
        
        # Parse the output
        parsed_data = parse_f5_hardware(output)
        
        # Display parsed information in formatted way
        display_parsed_info(parsed_data)
        
        # Save to CSV
        save_to_csv(parsed_data, host)
        
        print("\n" + "=" * 70)
        print("✓ Operation completed successfully!")
        print("=" * 70)
        
    else:
        print("\n✗ Failed to retrieve data from F5 device.")
        print("Possible issues:")
        print("- SSH not enabled on F5")
        print("- Incorrect credentials")
        print("- Network connectivity issues")
        print("- Firewall blocking port 22")
        print("- User doesn't have sufficient privileges")

if __name__ == "__main__":
    main()
