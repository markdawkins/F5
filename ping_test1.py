#!/usr/bin/env python3
"""
f5_ping_test.py

Prompts for F5 host, username, password.
SSH -> runs pings via bash on the F5:
  run util bash -c 'ping -c 5 8.8.8.8'
  run util bash -c 'ping -c 5 4.4.4.4'

Outputs results to PingOutput1.csv and prints "Ping Test completed".
"""

import paramiko
import getpass
import re
import csv
import sys
import time

def run_ssh_command(host, username, password, command, port=22, timeout=20):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username=username, password=password, timeout=timeout)
    except Exception as e:
        raise RuntimeError(f"SSH connection failed: {e}")
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        # Wait for command to complete
        out = stdout.read().decode(errors="ignore")
        err = stderr.read().decode(errors="ignore")
        return out, err
    finally:
        client.close()

def parse_ping_output(raw_output):
    """
    Parse standard Linux ping output for summary info.
    Returns a dict with keys:
      transmitted, received, packet_loss_pct, min_ms, avg_ms, max_ms, mdev_ms
    Missing fields set to None.
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

    # Example summary line:
    # "5 packets transmitted, 5 received, 0% packet loss, time 4005ms"
    m = re.search(r"(?P<tx>\d+)\s+packets transmitted,\s*(?P<rx>\d+)\s+received,\s*(?P<loss>[\d\.]+)%\s+packet loss", raw_output)
    if m:
        res["transmitted"] = int(m.group("tx"))
        res["received"] = int(m.group("rx"))
        # packet loss may be float but commonly integer
        try:
            res["packet_loss_pct"] = float(m.group("loss"))
        except:
            res["packet_loss_pct"] = None

    # Example rtt line:
    # "rtt min/avg/max/mdev = 0.026/0.033/0.042/0.006 ms"
    m2 = re.search(r"rtt .* = (?P<min>[\d\.]+)/(?P<avg>[\d\.]+)/(?P<max>[\d\.]+)/(?P<mdev>[\d\.]+) ms", raw_output)
    if m2:
        res["min_ms"] = float(m2.group("min"))
        res["avg_ms"] = float(m2.group("avg"))
        res["max_ms"] = float(m2.group("max"))
        res["mdev_ms"] = float(m2.group("mdev"))
    else:
        # Some busybox/other ping outputs may use "round-trip min/avg/max = ..." or different labels; try alternative:
        m3 = re.search(r"round-trip .* = (?P<min>[\d\.]+)/(?P<avg>[\d\.]+)/(?P<max>[\d\.]+)", raw_output)
        if m3:
            try:
                res["min_ms"] = float(m3.group("min"))
                res["avg_ms"] = float(m3.group("avg"))
                res["max_ms"] = float(m3.group("max"))
            except:
                pass

    return res

def run_ping_tests(host, username, password, destinations, csv_filename="PingOutput1.csv"):
    rows = []
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    for dest in destinations:
        # Build command to run under bash on the F5 device
        # Using: run util bash -c 'ping -c 5 8.8.8.8'
        # This executes the ping within bash on the F5 without needing interactive shell
        cmd = f"run util bash -c 'ping -c 5 {dest}'"
        try:
            out, err = run_ssh_command(host, username, password, cmd)
        except Exception as e:
            out = ""
            err = str(e)

        parsed = parse_ping_output(out)
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
            "raw_output": out.strip().replace("\r\n", "\\n").replace("\n", "\\n"),
            "error_output": err.strip().replace("\r\n", "\\n").replace("\n", "\\n") if err else ""
        }
        rows.append(row)

    # Write CSV
    fieldnames = ["timestamp","device","destination","transmitted","received","packet_loss_pct","min_ms","avg_ms","max_ms","mdev_ms","raw_output","error_output"]
    try:
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
    except Exception as e:
        raise RuntimeError(f"Failed to write CSV '{csv_filename}': {e}")

def main():
    print("F5 Ping Test Script")
    host = input("Enter F5 IP or hostname: ").strip()
    if not host:
        print("Host required. Exiting.")
        sys.exit(1)
    username = input("Enter username: ").strip()
    if not username:
        print("Username required. Exiting.")
        sys.exit(1)
    password = getpass.getpass("Enter password: ")

    destinations = ["8.8.8.8", "4.4.4.4"]
    csv_filename = "PingOutput1.csv"

    try:
        run_ping_tests(host, username, password, destinations, csv_filename=csv_filename)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)

    print(f"Ping results written to {csv_filename}")
    print("Ping Test completed")

if __name__ == "__main__":
    main()
