#!/usr/bin/env python3
"""
f5_nslookup.py

Prompts for host/ip, username, password, SSHes to an F5 device, switches to bash,
runs nslookup webbanking.america.com 10.1.1.1, prints the output, and appends a row
to LookupOutput.csv with host, timestamp, and the output.

Requires: paramiko
    pip install paramiko
"""

import paramiko
import time
import csv
from datetime import datetime
import getpass
import sys

CSV_FILE = "LookupOutput.csv"
NSLOOKUP_CMD = "nslookup webbanking.america.com 10.1.1.1"

def read_from_shell_until_idle(shell, timeout=20.0, idle_time=1.0):
    """
    Read from an interactive shell until no new data for idle_time seconds, or until overall timeout.
    Returns the collected output as a string.
    """
    end_time = time.time() + timeout
    collected = b""
    last_len = 0
    last_recv_time = time.time()
    while time.time() < end_time:
        if shell.recv_ready():
            try:
                data = shell.recv(65536)
            except Exception:
                break
            if not data:
                # no more data
                break
            collected += data
            last_recv_time = time.time()
            last_len = len(collected)
        else:
            # if no new data, check idle
            if time.time() - last_recv_time >= idle_time:
                break
            time.sleep(0.1)
    try:
        return collected.decode(errors="replace")
    except Exception:
        return collected.decode("utf-8", errors="replace")

def run_nslookup_on_f5(host, username, password, port=22, look_cmd=NSLOOKUP_CMD):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(hostname=host, port=port, username=username, password=password, look_for_keys=False, allow_agent=False, timeout=10)
    except Exception as e:
        print(f"SSH connection failed: {e}")
        return None, f"SSH connection failed: {e}"

    try:
        shell = client.invoke_shell()
        time.sleep(0.5)
        _ = read_from_shell_until_idle(shell, timeout=2.0)  # clear banner/prompt

        # Try to start bash. On F5 the common method is "run util bash" (or "run /util bash")
        # We'll try a couple of variants for compatibility.
        bash_commands = ["run util bash", "run /util bash", "bash", "run -c 'bash'"]
        started_bash = False
        bash_start_output = ""

        for cmd in bash_commands:
            shell.send(cmd + "\n")
            # wait a moment and read output
            out = read_from_shell_until_idle(shell, timeout=5.0)
            bash_start_output += f"\n---Attempt: {cmd}---\n{out}\n"
            # heuristics: look for common bash prompts, or for presence of '#' or '$' that indicate shell.
            # Also if "root@" appears (F5's bash prompt often shows root@...), assume bash started.
            if ("root@" in out) or out.strip().endswith("#") or out.strip().endswith("$") or "bash:" not in out:
                # This is heuristic — assume bash
                started_bash = True
                break
            # else try next

        if not started_bash:
            # still continue but warn
            print("Warning: could not reliably detect entry into bash. Continuing to try running nslookup anyway.")
            # (bash_start_output contains attempted responses)

        # Now send the nslookup command
        shell.send(look_cmd + "\n")
        # Read output
        ns_output = read_from_shell_until_idle(shell, timeout=15.0, idle_time=1.0)

        # After command, try to exit bash gracefully
        shell.send("exit\n")
        time.sleep(0.5)
        _ = read_from_shell_until_idle(shell, timeout=2.0)

        shell.close()
        client.close()

        # Combine any bash start logs with nslookup output for full trace if desired
        full_output = bash_start_output + "\n---nslookup output---\n" + ns_output
        return ns_output, full_output

    except Exception as e:
        try:
            client.close()
        except:
            pass
        return None, f"Exception while running commands: {e}"

def append_to_csv(filename, host, timestamp_iso, output_text):
    # We'll store the output as a single CSV cell. To keep it readable, replace CRLF with spaces or keep as-is; csv will handle quoting.
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([host, timestamp_iso, output_text])

def main():
    print("F5 nslookup helper")
    host = input("Enter F5 IP or hostname: ").strip()
    if not host:
        print("No host provided, exiting.")
        sys.exit(1)
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    print(f"\nConnecting to {host} ...")
    ns_output, full_output = run_nslookup_on_f5(host, username, password)
    timestamp_iso = datetime.now().isoformat(sep=" ", timespec="seconds")

    if ns_output is None:
        # full_output contains error message
        print("Failed to get nslookup output:")
        print(full_output)
        # still record the failure into CSV so there's an audit trail
        append_to_csv(CSV_FILE, host, timestamp_iso, full_output)
        print("Finished and Lookup recorded")
        return

    # Print the command output to screen
    print("\n=== nslookup output ===\n")
    print(ns_output.strip())
    print("\n=======================\n")

    # Append to CSV
    try:
        append_to_csv(CSV_FILE, host, timestamp_iso, ns_output)
    except Exception as e:
        print(f"Failed to append to {CSV_FILE}: {e}")
        # still exit but inform user
        print("Lookup ran but failed to record to CSV.")
        return

    print("Finished and Lookup recorded")

if __name__ == "__main__":
    main()
