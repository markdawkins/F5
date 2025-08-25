import csv
import getpass
import re
import time
from datetime import datetime
import paramiko  # Import paramiko for SSH functionality

def connect_to_router():
    """Connect to router using SSH with username and password only"""
    # Get connection details from user
    host = input("Enter router IP address or hostname: ")
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    
    try:
        # Create SSH client instance
        print(f"Connecting to {host} via SSH...")
        ssh_client = paramiko.SSHClient()
        
        # Automatically add host keys (not recommended for production)
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Establish SSH connection with timeout
        ssh_client.connect(
            hostname=host,
            username=username,
            password=password,
            timeout=10,
            look_for_keys=False,  # Disable key-based authentication
            allow_agent=False    # Disable SSH agent
        )
        
        # Create an interactive shell session
        shell = ssh_client.invoke_shell()
        
        # Wait for the shell to be ready
        time.sleep(2)
        
        # Read initial output to check if login was successful
        initial_output = shell.recv(1000).decode('ascii', errors='ignore')
        
        if not any(prompt in initial_output for prompt in ['>', '#']):
            # If no prompt found, try sending enter to trigger prompt
            shell.send("\n")
            time.sleep(1)
            initial_output = shell.recv(1000).decode('ascii', errors='ignore')
            
            if not any(prompt in initial_output for prompt in ['>', '#']):
                print("Login failed or prompt not recognized")
                ssh_client.close()
                return None, None
        
        # Disable pagination
        shell.send("terminal length 0\n")
        time.sleep(1)
        shell.recv(1000)  # Clear buffer
        
        # Send show version command
        print("Executing 'show version' command...")
        shell.send("show version\n")
        time.sleep(3)  # Give time for command to execute
        
        # Read output until prompt appears
        output = ""
        start_time = time.time()
        while time.time() - start_time < 10:  # Timeout after 10 seconds
            if shell.recv_ready():
                chunk = shell.recv(1000).decode('ascii', errors='ignore')
                if chunk:
                    output += chunk
                    # Check if we have the complete output (ends with prompt)
                    if any(prompt in chunk for prompt in ['#', '>']):
                        break
            time.sleep(0.5)
        
        # If we didn't get much output, try alternative read method
        if len(output.strip()) < 50:
            time.sleep(2)
            output = shell.recv(1000).decode('ascii', errors='ignore')
        
        # Clean up the output
        if output:
            # Remove command echo and pagination command
            output = output.replace("terminal length 0", "").strip()
            output = output.replace("show version", "").strip()
            # Remove trailing prompt
            output = re.sub(r'[\r\n]*[a-zA-Z0-9_-]*[#>][\s\S]*$', '', output)
            output = output.replace("\r\n", "\n").strip()
        
        # Close connection
        shell.send("exit\n")
        time.sleep(1)
        ssh_client.close()
        
        return output, host
        
    except Exception as e:
        print(f"SSH connection error: {e}")
        return None, None

def parse_show_version(output):
    """Parse the show version output and extract key information"""
    if not output:
        return {"error": "No output received from router"}
    
    parsed_data = {}
    
    # Extract various information using regex
    patterns = {
        'software_version': r'Cisco IOS Software.*?Version ([^,\n]+)',
        'uptime': r'uptime is (.*?)\n',
        'processor_board_id': r'Processor board ID (.*?)\n',
        'compiled': r'Compiled (.*?)\n',
        'Configuration_register': r'(?i)configuration\s+register[^\n]*\s+([^\n]+)',
        }
    
    # Search for each pattern in the output
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
        'Software Version': data.get('software_version', 'N/A'),
        'Uptime': data.get('uptime', 'N/A'),
        'Processor Board ID': data.get('processor_board_id', 'N/A'),
        'Compiled': data.get('compiled', 'N/A'),
        'Configuraton register': data.get('Configuration_register', 'N/A'),
        'Hostname': hostname  # hostname is defined as a parameter
    }
        
    try:
        # Check if file exists to determine if we need to write headers
        file_exists = False
        try:
            with open(filename, 'r'):
                file_exists = True
        except FileNotFoundError:
            pass
        
        # Open CSV file in append mode
        with open(filename, 'a', newline='') as csvfile:
            fieldnames = list(csv_data.keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header if file doesn't exist
            if not file_exists:
                writer.writeheader()
            
            # Write data row
            writer.writerow(csv_data)
        
        print(f"Results saved to {filename}")
        
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def save_raw_output(output, hostname):
    """Save raw output to a text file for debugging"""
    if output:
        # Create filename with hostname and timestamp
        filename = f"raw_output_{hostname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f:
            f.write(f"Raw output from {hostname}:\n")
            f.write("=" * 50 + "\n")
            f.write(output)
        print(f"Raw output saved to {filename}")

def main():
    """Main function to execute the script"""
    print("Cisco Router Show Version Script")
    print("=" * 40)
    
    # Connect to router
    output, host = connect_to_router()
    
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
        
        # Display parsed information
        print("\nPARSED INFORMATION FOR:")
        print("\n")
        print(host)
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
