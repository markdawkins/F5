import paramiko
import csv
import getpass
import re
import time
from datetime import datetime
import socket

def connect_to_router_ssh():
    """
    Establish SSH connection to Cisco router and execute 'show version' command.
    
    Returns:
        tuple: (command_output, hostname) or (None, None) if failed
    """
    # Get connection details from user
    host = input("Enter router IP address or hostname: ")
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    
    # Optional: SSH port (default is 22)
    ssh_port = 22
    
    # Create SSH client instance
    ssh_client = paramiko.SSHClient()
    
    # Automatically add host keys (use with caution in production)
    # In production, you should use known_hosts file instead
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {host} via SSH...")
        
        # Establish SSH connection with timeout
        ssh_client.connect(
            hostname=host,
            port=ssh_port,
            username=username,
            password=password,
            timeout=10,
            look_for_keys=False,  # Don't look for SSH keys
            allow_agent=False    # Don't use SSH agent
        )
        
        # Create interactive shell session
        print("Establishing SSH shell session...")
        shell = ssh_client.invoke_shell()
        
        # Wait for the shell to be ready and read initial output
        time.sleep(2)
        initial_output = shell.recv(1000).decode('utf-8')
        
        # Check if we need to enter enable mode
        if '>' in initial_output:
            print("Entering enable mode...")
            shell.send("enable\n")
            time.sleep(1)
            enable_output = shell.recv(1000).decode('utf-8')
            
            # If password prompt appears for enable mode
            if "Password:" in enable_output:
                enable_password = getpass.getpass("Enter enable password: ")
                shell.send(enable_password + "\n")
                time.sleep(2)
                shell.recv(1000)  # Clear the buffer
        
        # Send the show version command
        print("Executing 'show version' command...")
        shell.send("show version\n")
        
        # Wait for command to execute and read output
        time.sleep(3)
        
        # Initialize output buffer
        output = ""
        
        # Read output until command completion (detected by prompt)
        while True:
            if shell.recv_ready():
                chunk = shell.recv(1024).decode('utf-8')
                output += chunk
                
                # Check if we've reached the command prompt indicating command completion
                if any(prompt in chunk for prompt in ['#', '>']):
                    break
            else:
                # Small delay to prevent CPU spinning
                time.sleep(0.5)
                
        # Clean up the output - remove the command echo and prompt
        output = output.replace("show version", "").strip()
        output = re.sub(r'[\r\n]*[a-zA-Z0-9_-]*[#>][\r\n]*$', '', output)
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

def parse_show_version(output):
    """
    Parse the 'show version' output and extract key information using regex.
    
    Args:
        output (str): Raw output from the 'show version' command
        
    Returns:
        dict: Parsed information with various router details
    """
    if not output:
        return {"error": "No output received from router"}
    
    parsed_data = {}
    
    # Regex patterns to extract specific information from show version output
    patterns = {
        'software_version': r'Cisco IOS Software.*?Version ([^,\n]+)',
        'rommon_version': r'ROM:.*?([^\s,]+)',
        'system_image': r'System image file is "([^"]+)"',
        'uptime': r'uptime is (.*?)\n',
        'processor_type': r'processor.*?with (\d+K/\d+K) bytes of memory',
        'chassis': r'cisco (\S+) \(\S+\) processor',
        'serial_number': r'Processor board ID (\S+)',
        'config_register': r'Configuration register is (\S+)',
        'hostname': r'([a-zA-Z0-9_-]+)[#>]',  # Extract hostname from prompt
        'model': r'[Cc]isco (\d+)[\s\(]',     # Extract model number
    }
    
    # Apply each regex pattern to extract information
    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            parsed_data[key] = match.group(1).strip()
        else:
            parsed_data[key] = "Not found"
    
    # Additional specific extractions
    # Memory information
    memory_match = re.search(r'with (\d+K/\d+K) bytes of memory', output)
    parsed_data['memory'] = memory_match.group(1) if memory_match else "Not found"
    
    # Interface count
    interfaces_match = re.search(r'(\d+) (FastEthernet|GigabitEthernet).*interface', output)
    parsed_data['interface_count'] = interfaces_match.group(1) if interfaces_match else "Not found"
    
    # IOS feature set
    feature_match = re.search(r'Software \((.*?)\), Version', output)
    parsed_data['ios_feature_set'] = feature_match.group(1) if feature_match else "Not found"
    
    return parsed_data

def save_to_csv(parsed_data, hostname):
    """
    Save parsed router information to a CSV file.
    
    Args:
        parsed_data (dict): Parsed information from show version command
        hostname (str): Router hostname or IP address
    """
    filename = "results.csv"
    
    # Prepare data structure for CSV writing
    csv_data = {
        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'Router Hostname': parsed_data.get('hostname', 'N/A'),
        'Router IP': hostname,
        'Software Version': parsed_data.get('software_version', 'N/A'),
        'IOS Feature Set': parsed_data.get('ios_feature_set', 'N/A'),
        'System Image': parsed_data.get('system_image', 'N/A'),
        'Chassis Model': parsed_data.get('chassis', 'N/A'),
        'Processor Type': parsed_data.get('processor_type', 'N/A'),
        'Memory': parsed_data.get('memory', 'N/A'),
        'Serial Number': parsed_data.get('serial_number', 'N/A'),
        'Uptime': parsed_data.get('uptime', 'N/A'),
        'Config Register': parsed_data.get('config_register', 'N/A'),
        'Interface Count': parsed_data.get('interface_count', 'N/A'),
        'ROM Version': parsed_data.get('rommon_version', 'N/A')
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
        output (str): Raw output from the show version command
        hostname (str): Router hostname or IP address
    """
    if output:
        # Create filename with timestamp for uniqueness
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"raw_output_{hostname}_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Raw 'show version' output from {hostname}\n")
                f.write("=" * 60 + "\n")
                f.write(f"Capture time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                f.write(output)
            
            print(f"✓ Raw output saved to {filename}")
            
        except Exception as e:
            print(f"✗ Error saving raw output: {e}")

def display_parsed_info(parsed_data):
    """
    Display parsed information in a formatted way to the console.
    
    Args:
        parsed_data (dict): Parsed information from show version command
    """
    print("\n" + "=" * 60)
    print("PARSED ROUTER INFORMATION:")
    print("=" * 60)
    
    # Display order for better readability
    display_order = [
        'hostname', 'software_version', 'ios_feature_set', 
        'chassis', 'serial_number', 'processor_type', 'memory',
        'interface_count', 'uptime', 'config_register',
        'system_image', 'rommon_version'
    ]
    
    # Friendly names for display
    friendly_names = {
        'hostname': 'Router Hostname',
        'software_version': 'IOS Version',
        'ios_feature_set': 'Feature Set',
        'chassis': 'Chassis Model',
        'serial_number': 'Serial Number',
        'processor_type': 'Processor',
        'memory': 'Memory',
        'interface_count': 'Interface Count',
        'uptime': 'Uptime',
        'config_register': 'Config Register',
        'system_image': 'System Image',
        'rommon_version': 'ROM Version'
    }
    
    for key in display_order:
        if key in parsed_data and parsed_data[key] != "Not found":
            friendly_name = friendly_names.get(key, key.replace('_', ' ').title())
            print(f"{friendly_name}: {parsed_data[key]}")

def main():
    """
    Main function to orchestrate the SSH connection and data processing.
    """
    print("Cisco Router Show Version Script (SSH)")
    print("=" * 50)
    print("This script connects to a Cisco router via SSH,")
    print("executes 'show version', and saves results to CSV.")
    print("=" * 50)
    
    # Check if paramiko is available
    try:
        import paramiko
    except ImportError:
        print("Error: paramiko module is required but not installed.")
        print("Install it using: pip install paramiko")
        return
    
    # Connect to router and get output
    output, host = connect_to_router_ssh()
    
    if output and host:
        # Display raw output to screen
        print("\n" + "=" * 60)
        print("RAW SHOW VERSION OUTPUT:")
        print("=" * 60)
        print(output)
        print("=" * 60)
        
        # Save raw output for debugging
        save_raw_output(output, host)
        
        # Parse the output
        parsed_data = parse_show_version(output)
        
        # Display parsed information in formatted way
        display_parsed_info(parsed_data)
        
        # Save to CSV
        save_to_csv(parsed_data, host)
        
        print("\n" + "=" * 60)
        print("✓ Operation completed successfully!")
        print("=" * 60)
        
    else:
        print("\n✗ Failed to retrieve data from router.")
        print("Possible issues:")
        print("- SSH not enabled on router")
        print("- Incorrect credentials")
        print("- Network connectivity issues")
        print("- Firewall blocking port 22")

if __name__ == "__main__":
    main()
