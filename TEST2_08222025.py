import csv
import getpass
import re
import time
from datetime import datetime
import paramiko

def connect_to_router():
    """Connect to router using SSH with username and password only"""
    # Get connection details from user
    host = input("Enter router IP address or hostname: ")
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    
    try:
        # Establish SSH connection
        print(f"Connecting to {host} via SSH...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect to the device
        ssh.connect(hostname=host, username=username, password=password, timeout=10)
        
        # Create shell channel
        shell = ssh.invoke_shell()
        time.sleep(2)  # Wait for shell to initialize
        
        # Read initial output
        initial_output = shell.recv(1000).decode('ascii', errors='ignore')
        
        # Check if we're at a prompt
        if not any(prompt in initial_output for prompt in ['>', '#']):
            # Send enter to trigger prompt
            shell.send("\n")
            time.sleep(1)
            initial_output = shell.recv(1000).decode('ascii', errors='ignore')
            
            if not any(prompt in initial_output for prompt in ['>', '#']):
                print("Login failed or prompt not recognized")
                ssh.close()
                return None, None
        
        # Disable pagination
        shell.send("terminal length 0\n")
        time.sleep(1)
        
        # Clear buffer
        while shell.recv_ready():
            shell.recv(1000)
        
        # Send show sys hardware command
        print("Executing 'show sys hardware' command...")
        shell.send("show sys hardware\n")
        time.sleep(3)  # Give time for command to execute
        
        # Read output
        output = ""
        start_time = time.time()
        while time.time() - start_time < 10:  # Timeout after 10 seconds
            if shell.recv_ready():
                chunk = shell.recv(4096).decode('ascii', errors='ignore')
                output += chunk
                # Check if we have the complete output (ends with prompt)
                if any(prompt in chunk for prompt in ['#', '>']):
                    break
            time.sleep(0.5)
        
        # Clean up the output
        if output:
            # Remove command echo and pagination command
            output = output.replace("terminal length 0", "").strip()
            output = output.replace("show sys hardware", "").strip()
            # Remove trailing prompt
            output = re.sub(r'[\r\n]*[a-zA-Z0-9_-]*[#>][\s\S]*$', '', output)
            output = output.replace("\r\n", "\n").strip()
        
        # Close connection
        shell.send("exit\n")
        time.sleep(1)
        ssh.close()
        
        return output, host
        
    except Exception as e:
        print(f"SSH connection error: {e}")
        return None, None

def parse_show_sys_hardware(output):
    """Parse the show sys hardware output and extract key information"""
    if not output:
        return {"error": "No output received from router"}
    
    parsed_data = {}
    
    # Extract various information using regex for show sys hardware
    patterns = {
        'model': r'(?i)Model\s*:\s*([^\n]+)',
        'serial_number': r'(?i)Serial\s*Number\s*:\s*([^\n]+)',
        'ios_version': r'(?i)Software\s*Version\s*:\s*([^\n]+)',
        'memory': r'(?i)Memory\s*:\s*([^\n]+)',
        'flash_memory': r'(?i)Flash\s*Memory\s*:\s*([^\n]+)',
        'uptime': r'(?i)Uptime\s*:\s*([^\n]+)',
        'processor': r'(?i)Processor\s*:\s*([^\n]+)',
        'interfaces': r'(?i)Interfaces\s*:\s*([^\n]+)',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            parsed_data[key] = match.group(1).strip()
        else:
            parsed_data[key] = "Not found"
    
    return parsed_data

def save_to_csv(data, hostname):
    """Save parsed data to CSV file"""
    filename = "results.csv"
    
    # Prepare data for CSV
    csv_data = {
        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'Hostname': hostname,
        'Model': data.get('model', 'N/A'),
        'Serial Number': data.get('serial_number', 'N/A'),
        'IOS Version': data.get('ios_version', 'N/A'),
        'Memory': data.get('memory', 'N/A'),
        'Flash Memory': data.get('flash_memory', 'N/A'),
        'Uptime': data.get('uptime', 'N/A'),
        'Processor': data.get('processor', 'N/A'),
        'Interfaces': data.get('interfaces', 'N/A'),
    }
    
    try:
        # Check if file exists to determine if we need to write headers
        file_exists = False
        try:
            with open(filename, 'r'):
                file_exists = True
        except FileNotFoundError:
            pass
        
        with open(filename, 'a', newline='') as csvfile:
            fieldnames = list(csv_data.keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(csv_data)
        
        print(f"Results saved to {filename}")
        
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def save_raw_output(output, hostname):
    """Save raw output to a text file for debugging"""
    if output:
        filename = f"raw_output_{hostname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f:
            f.write(f"Raw output from {hostname}:\n")
            f.write("=" * 50 + "\n")
            f.write(output)
        print(f"Raw output saved to {filename}")

def main():
    print("Cisco Router Hardware Information Script")
    print("=" * 50)
    
    # Connect to router
    output, host = connect_to_router()
    
    if output and host:
        # Display raw output to screen
        print("\n" + "=" * 60)
        print("RAW SHOW SYS HARDWARE OUTPUT:")
        print("=" * 60)
        print(output)
        print("=" * 60)
        
        # Save raw output for debugging
        save_raw_output(output, host)
        
        # Parse the output
        parsed_data = parse_show_sys_hardware(output)
        
        # Display parsed information
        print("\nPARSED INFORMATION:")
        print("=" * 40)
        for key, value in parsed_data.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        
        # Save to CSV
        save_to_csv(parsed_data, host)
        
        print("\nOperation completed successfully!")
    else:
        print("Failed to retrieve data from router. Possible issues:")
        print("- SSH not enabled on router")
        print("- Incorrect credentials")
        print("- Network connectivity issues")
        print("- Router prompt not recognized")

if __name__ == "__main__":
    main()
