import paramiko
import getpass

def run_f5_commands(host, username, password):
    commands = [
        "list /sys sshd all-properties",
        "modify /sys sshd include \"Ciphers aes256,arcfour128,arcfour256,arcfour\"",
        "save sys config",
        "list /sys sshd all-properties"
    ]

    try:
        # Create SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"Connecting to {host}...")
        ssh.connect(hostname=host, username=username, password=password)

        for cmd in commands:
            print(f"\nRunning: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode()
            error = stderr.read().decode()
            if output:
                print(output.strip())
            if error:
                print("Error:", error.strip())

        ssh.close()
        print("\nUpdate completed successfully.")

    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    host = input("Enter F5 device IP: ")
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    run_f5_commands(host, username, password)
