#!/usr/bin/env python3
"""
Install/uninstall macOS launchd plist for scheduled digest runs.
"""

import os
import sys
import plistlib
import subprocess
import argparse


PLIST_FILENAME = "com.youtube-digest.pipeline.plist"
PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{PLIST_FILENAME}")


def find_skill_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_python() -> str:
    """Find the current Python executable path."""
    return sys.executable


def create_plist(frequency: str) -> dict:
    """Create a launchd plist based on frequency."""
    skill_dir = find_skill_dir()
    python_path = find_python()
    script_path = os.path.join(skill_dir, "scripts", "pipeline_orchestrator.py")

    plist = {
        "Label": "com.youtube-digest.pipeline",
        "ProgramArguments": [
            python_path,
            script_path,
            "--run-once",
        ],
        "WorkingDirectory": skill_dir,
        "StandardOutPath": os.path.join(skill_dir, "data", "pipeline.log"),
        "StandardErrorPath": os.path.join(skill_dir, "data", "pipeline_error.log"),
        "RunAtLoad": False,
    }

    if frequency == "daily":
        # Run every day at 8:00 AM (randomized minute to avoid thundering herd)
        plist["StartCalendarInterval"] = {
            "Hour": 8,
            "Minute": 3,
        }
    elif frequency == "weekly":
        # Run every Monday at 8:00 AM
        plist["StartCalendarInterval"] = {
            "Weekday": 2,  # Monday
            "Hour": 8,
            "Minute": 3,
        }
    else:  # monthly
        # Run on the 1st of each month
        plist["StartCalendarInterval"] = {
            "Day": 1,
            "Hour": 8,
            "Minute": 3,
        }

    return plist


def install(frequency: str = "daily"):
    """Install the launchd plist."""
    plist = create_plist(frequency)

    os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
    with open(PLIST_PATH, "wb") as f:
        plistlib.dump(plist, f)

    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}", PLIST_PATH],
        capture_output=True,
    )
    result = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", PLIST_PATH],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"  ✓ Installed schedule: {frequency}")
        print(f"    Plist: {PLIST_PATH}")
        print(f"    Logs:  {os.path.join(find_skill_dir(), 'data', 'pipeline.log')}")
        print(f"    View with: launchctl list | grep youtube-digest")
    else:
        print(f"  ✗ Failed to install: {result.stderr}")


def uninstall():
    """Remove the launchd plist."""
    if not os.path.exists(PLIST_PATH):
        print("  No schedule installed.")
        return

    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}", PLIST_PATH],
        capture_output=True,
    )
    os.remove(PLIST_PATH)
    print(f"  ✓ Removed schedule.")


def show():
    """Show current schedule."""
    if os.path.exists(PLIST_PATH):
        with open(PLIST_PATH, "rb") as f:
            plist = plistlib.load(f)
        interval = plist.get("StartCalendarInterval", {})
        print(f"  Schedule installed:")
        if "Day" in interval:
            print(f"    Monthly on day {interval['Day']} at {interval.get('Hour', 8)}:{interval.get('Minute', 0):02d}")
        elif "Weekday" in interval:
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            print(f"    Weekly on {days[interval['Weekday'] - 1]} at {interval.get('Hour', 8)}:{interval.get('Minute', 0):02d}")
        else:
            print(f"    Daily at {interval.get('Hour', 8)}:{interval.get('Minute', 0):02d}")
    else:
        print("  No schedule installed.")


def main():
    parser = argparse.ArgumentParser(description="youtube-digest launchd scheduler")
    parser.add_argument("--install", action="store_true", help="Install auto-schedule")
    parser.add_argument("--uninstall", action="store_true", help="Remove schedule")
    parser.add_argument("--show", action="store_true", help="Show current schedule")
    parser.add_argument("--frequency", type=str, default="daily",
                       choices=["daily", "weekly", "monthly"],
                       help="Schedule frequency (default: daily)")
    args = parser.parse_args()

    if args.install:
        install(args.frequency)
    elif args.uninstall:
        uninstall()
    elif args.show:
        show()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
