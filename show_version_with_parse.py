import paramiko
import getpass
import sys
import time
import re
import csv
import os
from datetime import datetime

class CiscoSSHClient:
    def __init__(self):
        self.ssh = None
        self.shell = None
        
    def connect(self, host, username, enable_password):
        try:
            # Establish SSH connection
            print(f"Connecting to {host} via SSH...")
            self.ssh = paramiko.SSHClient()
            
            # Automatically add host keys (not recommended for production)
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Get SSH password (different from enable password)
            ssh_password = getpass.getpass("Enter SSH password: ")
            
            # Connect to the device
            self.ssh.connect(
                hostname=host,
                username=username,
                password=ssh_password,
                look_for_keys=False,
                allow_agent=False,
                timeout=10
            )
            
            # Create an interactive shell
            self.shell = self.ssh.invoke_shell()
            time.sleep(1)
            
            # Clear initial buffer
            self._clear_buffer()
            
            # Enter enable mode
            self._enter_enable_mode(enable_password)
            
            # Disable pagination
            self._disable_pagination()
            
            return True
            
        except paramiko.AuthenticationException:
            print("Authentication failed. Please check your credentials.")
            return False
        except paramiko.SSHException as e:
            print(f"SSH connection failed: {e}")
            return False
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def _clear_buffer(self):
        """Clear the initial buffer"""
        if self.shell.recv_ready():
            self.shell.recv(65535)
    
    def _enter_enable_mode(self, enable_password):
        """Enter enable mode on the Cisco device"""
        # Check if we're already in enable mode
        self.shell.send("enable\n")
        time.sleep(1)
        
        output = self._receive_output()
        if "Password:" in output:
            # Need to provide enable password
            self.shell.send(enable_password + "\n")
            time.sleep(1)
            
            # Verify we entered enable mode
            output = self._receive_output()
            if "#" not in output:
                raise Exception("Failed to enter enable mode - check enable password")
        elif "#" in output:
            # Already in enable mode
            pass
    
    def _disable_pagination(self):
        """Disable pagination on the Cisco device"""
        self.shell.send("terminal length 0\n")
        time.sleep(1)
        self._clear_buffer()
    
    def _receive_output(self, timeout=2):
        """Receive output from the SSH shell"""
        output = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.shell.recv_ready():
                output += self.shell.recv(65535).decode('ascii')
                time.sleep(0.1)
            else:
                break
        
        return output
    
    def execute_command(self, command):
        """Execute a command and return the output"""
        try:
            # Send command
            self.shell.send(command + "\n")
            time.sleep(2)  # Wait for command to execute
            
            # Receive output
            output = self._receive_output()
            return output
            
        except Exception as e:
            return f"Error executing command: {e}"
    
    def disconnect(self):
        """Close the SSH connection"""
        if self.ssh:
            self.shell.send("exit\n")
            time.sleep(1)
            self.ssh.close()
            print("SSH connection closed.")

def parse_show_version(output):
    """Parse show version output for specific information"""
    parsed_data = {
        'version': 'Not found',
        'uptime': 'Not found',
        'config_register': 'Not found',
        'hostname': 'Not found',
        'model': 'Not found'
    }
    
    # Extract version
    version_match = re.search(r'Cisco IOS Software.*?Version ([^,]+)', output)
    if version_match:
        parsed_data['version'] = version_match.group(1).strip()
    else:
        # Alternative pattern for some devices
        version_match = re.search(r'Software \(([^)]+)\)', output)
        if version_match:
            parsed_data['version'] = version_match.group(1).strip()
    
    # Extract uptime
    uptime_match = re.search(r'uptime is (.+?)\n', output)
    if uptime_match:
        parsed_data['uptime'] = uptime_match.group(1).strip()
    
    # Extract configuration register
    config_reg_match = re.search(r'Configuration register is (0x[0-9A-F]+)', output, re.IGNORECASE)
    if config_reg_match:
        parsed_data['config_register'] = config_reg_match.group(1).strip()
    
    # Extract hostname
    hostname_match = re.search(r'^([a-zA-Z0-9_-]+)[#>]', output, re.MULTILINE)
    if hostname_match:
        parsed_data['hostname'] = hostname_match.group(1).strip()
    
    # Extract model
    model_match = re.search(r'cisco (.+?) \(', output, re.IGNORECASE)
    if model_match:
        parsed_data['model'] = model_match.group(1).strip()
    else:
        # Alternative pattern for model
        model_match = re.search(r'Model\.+?: (.+?)\n', output)
        if model_match:
            parsed_data['model'] = model_match.group(1).strip()
    
    return parsed_data

def save_to_csv(data, router_ip, filename='result_s.csv'):
    """Save parsed data to CSV file"""
    file_exists = os.path.isfile(filename)
    
    with open(filename, 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'router_ip', 'hostname', 'model', 'version', 'uptime', 'config_register']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header if file doesn't exist
        if not file_exists:
            writer.writeheader()
        
        # Add timestamp and router IP to data
        data_to_write = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'router_ip': router_ip,
            'hostname': data['hostname'],
            'model': data['model'],
            'version': data['version'],
            'uptime': data['uptime'],
            'config_register': data['config_register']
        }
        
        writer.writerow(data_to_write)
    
    print(f"Data saved to {filename}")

def display_parsed_data(data, router_ip):
    """Display parsed data in a formatted way"""
    print("\n" + "="*60)
    print("PARSED INFORMATION:")
    print("="*60)
    print(f"Router IP:      {router_ip}")
    print(f"Hostname:       {data['hostname']}")
    print(f"Model:          {data['model']}")
    print(f"Version:        {data['version']}")
    print(f"Uptime:         {data['uptime']}")
    print(f"Config Register: {data['config_register']}")
    print("="*60)

def main():
    # Get user input
    router_ip = input("Enter router IP address: ")
    username = input("Enter username: ")
    enable_password = getpass.getpass("Enter enable password: ")
    
    # Create SSH client
    client = CiscoSSHClient()
    
    try:
        # Connect to router via SSH
        if client.connect(router_ip, username, enable_password):
            # Execute show version command
            print("Executing 'show version' command...")
            result = client.execute_command("show version")
            
            # Display raw output for debugging (optional)
            # print("\nRaw output:\n" + "="*40)
            # print(result)
            # print("="*40)
            
            # Parse the output
            parsed_data = parse_show_version(result)
            
            # Display the parsed data
            display_parsed_data(parsed_data, router_ip)
            
            # Save to CSV file
            save_to_csv(parsed_data, router_ip)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    # Check if paramiko is installed
    try:
        import paramiko
    except ImportError:
        print("Error: paramiko module is required for SSH connections.")
        print("Install it using: pip install paramiko")
        sys.exit(1)
    
    main()
