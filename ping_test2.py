#!/usr/bin/env python3
"""
f5_ping_test.py

This script:
- Prompts the user for an F5 device IP/hostname, username, and password
- Logs into the F5 via SSH
- Runs pings to 8.8.8.8 and 4.4.4.4 inside the bash shell of the F5
- Parses the ping results (packets transmitted, received, loss %, RTT stats)
- Echoes results to the screen
- Saves results to PingOutput1.csv
- Prints "Ping Test completed" once finished
"""

import paramiko
import getpass
import re
import csv
import sys
import time

def run_ssh_command(host, username, password, command, port=22, timeout=20):
    """
    Opens an SSH connection to the F5 and executes a command.
    Returns stdout and stderr as strings.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username=username, password=password, timeout=timeout)
    except Exception as e:
        raise RuntimeError(f"SSH connection failed: {e}")
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode(errors="ignore")
        err = stderr.read().decode(errors="ignore")
        return out, err
    finally:
        client.close()

def parse_ping_output(raw_output):
    """
    Parse ping command output and extract summary stats.
    Returns a dictionary with transmitted, received, loss %, and RTT stats.
    """
    res = {
        "transmitted": None,
        "received": None,
        "packet_loss_pct": None,
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
        "mdev_ms": None
    }

    # Match "packets transmitted, received, loss %"
    m = re.search(r"(?P<tx>\d+)\s+packets transmitted,\s*(?P<rx>\d+)\s+received,\s*(?P<loss>[\d\.]+)%", raw_output)
    if m:
        res["transmitted"] = int(m.group("tx"))
        res["received"] = int(m.group("rx"))
        try:
            res["packet_loss_pct"] = float(m.group("loss"))
        except:
            res["packet_loss_pct"] = None

    # Match "rtt min/avg/max/mdev"
    m2 = re.search(r"rtt .* = (?P<min>[\d\.]+)/(?P<avg>[\d\.]+)/(?P<max>[\d\.]+)/(?P<mdev>[\d\.]+)", raw_output)
    if m2:
        res["min_ms"] = float(m2.group("min"))
        res["avg_ms"] = float(m2.group("avg"))
        res["max_ms"] = float(m2.group("max"))
        res["mdev_ms"] = float(m2.group("mdev"))

    return res

def run_ping_tests(host, username, password, destinations, csv_filename="PingOutput1.csv"):
    """
    Run ping tests to the given destinations from the F5 device.
    Echo results to the screen and write them to a CSV file.
    """
    rows = []
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    for dest in destinations:
        # Run ping inside bash shell on F5
        cmd = f"run util bash -c 'ping -c 5 {dest}'"
        try:
            out, err = run_ssh_command(host, username, password, cmd)
        except Exception as e:
            out = ""
            err = str(e)

        parsed = parse_ping_output(out)

        # Build a result row
        row = {
            "timestamp": timestamp,
            "device": host,
            "destination": dest,
            "transmitted": parsed["transmitted"],
            "received": parsed["received"],
            "packet_loss_pct": parsed["packet_loss_pct"],
            "min_ms": parsed["min_ms"],
            "avg_ms": parsed["avg_ms"],
            "max_ms": parsed["max_ms"],
            "mdev_ms": parsed["mdev_ms"],
            "raw_output": out.strip().replace("\n", "\\n"),
            "error_output": err.strip().replace("\n", "\\n") if err else ""
        }

        # Echo row to display
        print("---- Ping Result ----")
        for k, v in row.items():
            print(f"{k}: {v}")
        print("---------------------\n")

        rows.append(row)

    # Write rows to CSV file
    fieldnames = ["timestamp","device","destination","transmitted","received",
                  "packet_loss_pct","min_ms","avg_ms","max_ms","mdev_ms",
                  "raw_output","error_output"]

    try:
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
    except Exception as e:
        raise RuntimeError(f"Failed to write CSV '{csv_filename}': {e}")

def main():
    """
    Main program logic:
    - Prompt user for device info
    - Run ping tests
    - Save + display results
    """
    print("=== F5 Ping Test Script ===")
    host = input("Enter F5 IP or hostname: ").strip()
    if not host:
        print("Host required. Exiting.")
        sys.exit(1)
    username = input("Enter username: ").strip()
    if not username:
        print("Username required. Exiting.")
        sys.exit(1)
    password = getpass.getpass("Enter password: ")

    # Destinations to test
    destinations = ["8.8.8.8", "4.4.4.4"]
    csv_filename = "PingOutput1.csv"

    try:
        run_ping_tests(host, username, password, destinations, csv_filename=csv_filename)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)

    print(f"\nPing results written to {csv_filename}")
    print("Ping Test completed")

if __name__ == "__main__":
    main()
