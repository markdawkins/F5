#!/usr/bin/env python3
"""
f5_ping_test.py

This script:
- Prompts the user for an F5 device IP/hostname, username, and password
- Logs into the F5 via SSH
- Runs pings to specific destinations inside the bash shell of the F5
- Associates each destination IP with a friendly hostname label
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
import os

def run_ssh_command(host, username, password, command, port=22, timeout=20):
    """Connect to F5 via SSH and run a single command"""
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
    """Extract summary stats from ping output"""
    res = {
        "transmitted": None,
        "received": None,
        "packet_loss_pct": None,
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
        "mdev_ms": None
    }

    # packets transmitted/received/loss
    m = re.search(r"(?P<tx>\d+)\s+packets transmitted,\s*(?P<rx>\d+)\s+received,\s*(?P<loss>[\d\.]+)%", raw_output)
    if m:
        res["transmitted"] = int(m.group("tx"))
        res["received"] = int(m.group("rx"))
        try:
            res["packet_loss_pct"] = float(m.group("loss"))
        except:
            res["packet_loss_pct"] = None

    # rtt stats
    m2 = re.search(r"rtt .* = (?P<min>[\d\.]+)/(?P<avg>[\d\.]+)/(?P<max>[\d\.]+)/(?P<mdev>[\d\.]+)", raw_output)
    if m2:
        res["min_ms"] = float(m2.group("min"))
        res["avg_ms"] = float(m2.group("avg"))
        res["max_ms"] = float(m2.group("max"))
        res["mdev_ms"] = float(m2.group("mdev"))

    return res

def run_ping_tests(host, username, password, destinations, csv_filename="PingOutput1.csv"):
    """
    Run ping tests on the F5, print results, and save to CSV.
    destinations = { "8.8.8.8": "GoogleDNS", "4.4.4.4": "Level3DNS" }
    """
    rows = []
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    for dest_ip, dest_name in destinations.items():
        cmd = f"run util bash -c 'ping -c 5 {dest_ip}'"
        try:
            out, err = run_ssh_command(host, username, password, cmd)
        except Exception as e:
            out = ""
            err = str(e)

        parsed = parse_ping_output(out)

        row = {
            "timestamp": timestamp,
            "device": host,
            "destination_ip": dest_ip,
            "destination_name": dest_name,   # <-- friendly name
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

        # Echo row to screen
        print("---- Ping Result ----")
        for k, v in row.items():
            print(f"{k}: {v}")
        print("---------------------\n")

        rows.append(row)

    # Write results to CSV in user home folder for safety
    csv_path = os.path.expanduser(f"~/{csv_filename}")
    fieldnames = ["timestamp","device","destination_ip","destination_name","transmitted",
                  "received","packet_loss_pct","min_ms","avg_ms","max_ms","mdev_ms",
                  "raw_output","error_output"]

    try:
        with open(csv_path, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
    except Exception as e:
        raise RuntimeError(f"Failed to write CSV '{csv_path}': {e}")

    print(f"\nResults written to {csv_path}")

def main():
    """Main script logic"""
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

    # Mapping of IPs -> Friendly hostnames
    destinations = {
        "8.8.8.8": "GoogleDNS",
        "4.4.4.4": "Level3DNS"
    }

    try:
        run_ping_tests(host, username, password, destinations, csv_filename="PingOutput1.csv")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)

    print("Ping Test completed")

if __name__ == "__main__":
    main()
