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
            timeout=15,  # Increased timeout for connection
            look_for_keys=False,  # Disable key-based authentication
            allow_agent=False    # Disable SSH agent
        )
        
        # Create an interactive shell session
        shell = ssh_client.invoke_shell()
        shell.settimeout(15)  # Set timeout for shell operations
        
        # Wait for the shell to be ready and read initial output
        time.sleep(2)
        initial_output = ""
        while True:
            try:
                chunk = shell.recv(4096).decode('ascii', errors='ignore')
                if chunk:
                    initial_output += chunk
                    if any(prompt in initial_output for prompt in ['>', '#']):
                        break
            except:
                break
        
        if not any(prompt in initial_output for prompt in ['>', '#']):
            # If no prompt found, try sending enter to trigger prompt
            shell.send("\n")
            time.sleep(1)
            initial_output = shell.recv(4096).decode('ascii', errors='ignore')
            
            if not any(prompt in initial_output for prompt in ['>', '#']):
                print("Login failed or prompt not recognized")
                ssh_client.close()
                return None, None
        
        # Disable pagination with longer wait time
        shell.send("terminal length 0\n")
        time.sleep(2)
        
        # Clear any remaining buffer
        try:
            shell.recv(4096)
        except:
            pass
        
        # Send show sys hardware command with longer timeout
        print("Executing 'show sys hardware' command (this may take a while)...")
        shell.send("show sys hardware\n")
        
        # Wait for command to start processing
        time.sleep(3)
        
        # Read output with more comprehensive approach
        output = ""
        start_time = time.time()
        max_wait_time = 60  # Increased maximum wait time to 60 seconds
        
        while time.time() - start_time < max_wait_time:
            try:
                # Read available data
                if shell.recv_ready():
                    chunk = shell.recv(8192).decode('ascii', errors='ignore')  # Increased buffer size
                    if chunk:
                        output += chunk
                        print(f"Received {len(chunk)} bytes, total: {len(output)} bytes")
                        
                        # Check if we have the complete output (ends with prompt)
                        if any(prompt in chunk for prompt in ['#', '>']):
                            print("Detected command completion prompt")
                            break
                
                # Check if output is growing or stalled
                time.sleep(1)
                
                # If no data received for 10 seconds, assume command completed
                if len(output) > 0 and time.time() - start_time > 10:
                    # Send a carriage return to check if command is still running
                    shell.send("\n")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"Error reading output: {e}")
                break
        
        # If output is incomplete, try to get more data
        if output and not any(prompt in output for prompt in ['#', '>']):
            print("Output appears incomplete, attempting to get more data...")
            try:
                # Send enter and wait for response
                shell.send("\n")
                time.sleep(3)
                additional_output = shell.recv(8192).decode('ascii', errors='ignore')
                output += additional_output
            except:
                pass
        
        # Clean up the output
        if output:
            # Remove command echo and pagination command
            output = output.replace("terminal length 0", "").strip()
            output = output.replace("show sys hardware", "").strip()
            # Remove trailing prompt
            output = re.sub(r'[\r\n]*[a-zA-Z0-9_-]*[#>][\s\S]*$', '', output)
            output = output.replace("\r\n", "\n").strip()
        
        # Close connection
        try:
            shell.send("exit\n")
            time.sleep(1)
        except:
            pass
        finally:
            ssh_client.close()
        
        print(f"Total output received: {len(output)} characters")
        return output, host
        
    except Exception as e:
        print(f"SSH connection error: {e}")
        return None, None

def parse_show_sys_hardware(output):
    """Parse the show sys hardware output and extract key information"""
    if not output:
        return {"error": "No output received from router"}
    
    parsed_data = {}
    
    # Extract various information using regex for show sys hardware command
    patterns = {
        'model': r'Model\s*:\s*(.*?)(?:\n|$)',
        'serial_number': r'Serial [Nn]umber\s*:\s*(.*?)(?:\n|$)',
        'hardware_version': r'HW [Vv]ersion\s*:\s*(.*?)(?:\n|$)',
        'operating_system': r'Operating [Ss]ystem\s*:\s*(.*?)(?:\n|$)',
        'system_uptime': r'System [Uu]ptime\s*:\s*(.*?)(?:\n|$)',
        'memory': r'Memory\s*:\s*(.*?)(?:\n|$)',
        'processor_type': r'Processor\s*:\s*(.*?)(?:\n|$)',
        'chassis_type': r'Chassis\s*:\s*(.*?)(?:\n|$)',
        'device_name': r'[Dd]evice [Nn]ame\s*:\s*(.*?)(?:\n|$)',
        'boot_version': r'[Bb]oot [Vv]ersion\s*:\s*(.*?)(?:\n|$)',
    }
    
    # Search for each pattern in the output
    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            parsed_data[key] = match.group(1).strip()
        else:
            parsed_data[key] = "Not found"
    
    # If we have very little data, indicate partial output
    if len(output.strip()) < 100:
        parsed_data['output_status'] = "Partial output (less than 100 characters)"
    elif "Not found" in [str(v) for v in parsed_data.values()]:
        parsed_data['output_status'] = "Partial output (key fields missing)"
    else:
        parsed_data['output_status'] = "Complete output"
    
    return parsed_data

def save_to_csv(data, hostname):
    """Save parsed data to CSV file"""
    filename = "results.csv"
    
    # Prepare data for CSV with fields relevant to show sys hardware
    csv_data = {
        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
        'Model': data.get('model', 'N/A'),
        'Serial Number': data.get('serial_number', 'N/A'),
        'Hardware Version': data.get('hardware_version', 'N/A'),
        'Operating System': data.get('operating_system', 'N/A'),
        'System Uptime': data.get('system_uptime', 'N/A'),
        'Memory': data.get('memory', 'N/A'),
        'Processor Type': data.get('processor_type', 'N/A'),
        'Chassis Type': data.get('chassis_type', 'N/A'),
        'Device Name': data.get('device_name', 'N/A'),
        'Boot Version': data.get('boot_version', 'N/A'),
        'Output Status': data.get('output_status', 'N/A'),
        'Hostname': hostname
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
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Raw output from {hostname}:\n")
            f.write("=" * 50 + "\n")
            f.write(output)
            f.write(f"\n\nTotal length: {len(output)} characters")
        print(f"Raw output saved to {filename}")

def main():
    """Main function to execute the script"""
    print("Cisco Router Show System Hardware Script")
    print("=" * 50)
    print("Note: This command may take longer to complete on some devices")
    print("=" * 50)
    
    # Connect to router
    output, host = connect_to_router()
    
    if output and host:
        # Display raw output info
        print(f"\nReceived output: {len(output)} characters")
        
        # Save raw output for debugging
        save_raw_output(output, host)
        
        # Parse the output
        parsed_data = parse_show_sys_hardware(output)
        
        # Display parsed information
        print("\nPARSED INFORMATION FOR:")
        print(host)
        print("=" * 40)
        for key, value in parsed_data.items():
            if key != 'output_status':  # We'll display status separately
                print(f"{key.replace('_', ' ').title()}: {value}")
        
        # Display output status
        print(f"\nOutput Status: {parsed_data.get('output_status', 'Unknown')}")
        
        # Save to CSV
        save_to_csv(parsed_data, host)
        
        print("\nOperation completed!")
        
        # Provide advice based on output status
        status = parsed_data.get('output_status', '')
        if "Partial" in status:
            print("\nNOTE: Output appears to be incomplete.")
            print("Possible solutions:")
            print("1. Try increasing timeout values in the script")
            print("2. Check if the device supports 'show sys hardware'")
            print("3. Try alternative commands like 'show inventory' or 'show version'")
        
    else:
        print("Failed to retrieve data from router. Possible issues:")
        print("- SSH not enabled on router")
        print("- Incorrect credentials")
        print("- Network connectivity issues")
        print("- Router prompt not recognized")
        print("- 'show sys hardware' command not supported on this device")

if __name__ == "__main__":
    main()
