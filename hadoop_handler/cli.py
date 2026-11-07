"""Hadoop Handler v2.0.0 CLI Entry Point.

Pure Python Orchestration Engine with Ecosystem Addon Management.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

from hadoop_handler.addons.manager import AddonManager
from hadoop_handler.core.cluster import (
    delete_hadoop,
    install_hadoop,
    restart_services,
    start_services,
    stop_services,
    upgrade_hadoop,
    verify_hadoop,
)
from hadoop_handler.core.config import (
    BCYAN,
    CACHE_DIR,
    CYAN,
    DIVIDER,
    GREEN,
    NC,
    RED,
    VERSION,
    YELLOW,
)
from hadoop_handler.core.java import check_compatibility, list_javas, switch_java
from hadoop_handler.core.system import (
    diagnose_and_repair,
    install_shell_completion,
    manage_system_service,
)
from hadoop_handler.core.tui import select_menu_option


def check_version_banner() -> None:
    """Non-blocking cached version check from PyPI."""
    cache_file = CACHE_DIR / ".version_cache"
    now = time.time()
    last_check = cache_file.stat().st_mtime if cache_file.exists() else 0

    if now - last_check > 43200:  # 12 hours
        try:
            req = urllib.request.Request(
                "https://pypi.org/pypi/hadoop-handler/json",
                headers={"User-Agent": f"Hadoop-Handler/{VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode())
                latest_ver = data.get("info", {}).get("version")
                if latest_ver:
                    cache_file.write_text(latest_ver, encoding="utf-8")
        except Exception:
            pass

    if cache_file.exists():
        try:
            remote_ver = cache_file.read_text(encoding="utf-8").strip()
            if remote_ver:
                def parse_v(v_str: str) -> tuple[int, ...]:
                    return tuple(int(p) for p in v_str.replace("v", "").split(".") if p.isdigit())

                if parse_v(remote_ver) > parse_v(VERSION):
                    print(f"  {YELLOW}* Note: Update available: {VERSION} -> {remote_ver}.{NC}")
                    print(f"    Run {CYAN}hadoop-handler update{NC} or {CYAN}pip install --upgrade hadoop-handler{NC} to update.")
                    print(DIVIDER)
        except Exception:
            pass


def self_update() -> int:
    """Perform in-place update via pip or git."""
    print(DIVIDER)
    print(f"  {BCYAN}ACTION: Checking for Updates (Self-Update){NC}")
    print(f"{DIVIDER}\n")

    # Check git repository
    git_dir = Path(__file__).resolve().parent.parent / ".git"
    if git_dir.exists() and shutil.which("git"):
        print("  Detected git installation. Pulling latest commits from origin...")
        res = subprocess.run(["git", "pull", "origin", "main"], cwd=git_dir.parent, check=False)
        if res.returncode == 0:
            print(f"\n  {GREEN}[✓] Repository updated successfully!{NC}")
            return 0

    # Fallback to pip
    print("  Checking PyPI for latest version...")
    res = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "hadoop-handler"], check=False)
    if res.returncode == 0:
        print(f"\n  {GREEN}[✓] hadoop-handler updated successfully via pip!{NC}")
        return 0

    print(f"\n  {RED}[!] Update failed. Please run 'pip install --upgrade hadoop-handler' manually.{NC}")
    return 1


def print_help() -> None:
    help_text = f"""Hadoop Handler v{VERSION} — Pure Python Cluster & Ecosystem Control Center
Developer: Aditya Pidurkar (https://github.com/itsadityapidurkar)

Usage:
  hadoop-handler [COMMAND] [OPTIONS]

Commands:
  (no args)                     Launch interactive TUI control panel (arrow-key navigation)
  diagnose                      Diagnose and auto-repair system dependencies
  install [--version <ver>]     Install Hadoop with dynamic version selection (default: 3.4.2)
  upgrade [<target_version>]    In-place upgrade/downgrade preserving HDFS data
  check-compat [<h_ver>] [<j>]  Check Hadoop and Java matrix compatibility
  java list                     List all detected Java runtimes
  java use <path|version>       Switch active Java runtime for Hadoop
  java switch                   Interactively switch active Java runtime
  verify, status                Verify Hadoop & Java installation status and daemons
  start                         Start HDFS and YARN daemons
  stop                          Stop HDFS and YARN daemons
  restart                       Restart all cluster daemons
  addon list                    List all big data addons (Spark, Hive, Kafka, Trino)
  addon install <name>          Install ecosystem addon (spark|hive|kafka|trino)
  addon status <name>           Check addon status and listening ports
  addon start <name>            Start ecosystem addon services
  addon stop <name>             Stop ecosystem addon services
  addon remove <name>           Remove ecosystem addon
  delete                        Remove Hadoop cluster and related directories
  service <action>              Manage system service (enable|disable|status|start|stop)
  update                        Check and perform in-place self-update
  completion <shell>            Generate autocompletion script (bash|zsh|fish|powershell)
  --install-completion          Automatically register autocompletion in active shell

Options:
  -v, --version                 Show version and exit
  -h, --help                    Show this help message and exit

Online Documentation:
  https://github.com/itsadityapidurkar/hadoop-handler
"""
    print(help_text)


def interactive_loop() -> int:
    """Main interactive control center loop."""
    addon_mgr = AddonManager()

    while True:
        choice = select_menu_option()

        if choice == 0:
            diagnose_and_repair()
        elif choice == 1:
            install_hadoop()
        elif choice == 2:
            verify_hadoop()
        elif choice == 3:
            check_compatibility()
        elif choice == 4:
            start_services()
        elif choice == 5:
            stop_services()
        elif choice == 6:
            restart_services()
        elif choice == 7:
            switch_java()
        elif choice == 8:
            upgrade_hadoop()
        elif choice == 9:
            addon_mgr.interactive_menu()
        elif choice == 10:
            delete_hadoop()
        elif choice == 11:
            print(DIVIDER)
            print(f"  {BCYAN}ACTION: System Service Integration{NC}")
            print(DIVIDER)
            print("    1. Enable on boot/login")
            print("    2. Disable service")
            print("    3. Service status")
            print("    4. Start service")
            print("    5. Stop service")
            print("    0. Cancel")
            try:
                s_pick = input("  Select action [0-5]: ").strip()
                s_map = {"1": "enable", "2": "disable", "3": "status", "4": "start", "5": "stop"}
                if s_pick in s_map:
                    manage_system_service(s_map[s_pick])
            except (KeyboardInterrupt, EOFError):
                pass
        elif choice == 12:
            self_update()
        elif choice == 13:
            install_shell_completion()
        elif choice == 14:
            print("\n  Exiting Hadoop Handler. Goodbye!")
            return 0

        input(f"\n  {YELLOW}Press [Enter] to return to the main menu...{NC}")


def main() -> int:
    args = sys.argv[1:]

    if not args:
        check_version_banner()
        return interactive_loop()

    cmd = args[0]

    if cmd in ("-v", "--version", "-V"):
        print(f"hadoop-handler {VERSION}")
        return 0
    elif cmd in ("-h", "--help"):
        print_help()
        return 0
    elif cmd in ("0", "diagnose", "repair"):
        return diagnose_and_repair()
    elif cmd in ("1", "install"):
        version = None
        if len(args) > 2 and args[1] == "--version":
            version = args[2]
        elif len(args) > 1 and not args[1].startswith("-"):
            version = args[1]
        return 0 if install_hadoop(version) else 1
    elif cmd in ("2", "verify", "status"):
        verify_hadoop()
        return 0
    elif cmd in ("3", "start"):
        start_services()
        return 0
    elif cmd in ("4", "stop"):
        stop_services()
        return 0
    elif cmd == "restart":
        restart_services()
        return 0
    elif cmd in ("check-compat", "compat"):
        h_ver = args[1] if len(args) > 1 else None
        j_ver = args[2] if len(args) > 2 else None
        compat, _, _ = check_compatibility(h_ver, j_ver)
        return 0 if compat else 1
    elif cmd == "java":
        sub = args[1] if len(args) > 1 else "list"
        if sub == "list":
            list_javas()
            return 0
        elif sub == "use":
            target = args[2] if len(args) > 2 else None
            return 0 if switch_java(target) else 1
        elif sub == "switch":
            target = args[2] if len(args) > 2 else None
            return 0 if switch_java(target) else 1
        else:
            print(f"  {RED}[!] Unknown java subcommand: {sub}. Available: list, switch, use.{NC}")
            return 1
    elif cmd == "addon":
        addon_mgr = AddonManager()
        if len(args) == 1 or args[1] == "list":
            addon_mgr.list_addons()
            return 0
        sub = args[1]
        name = args[2] if len(args) > 2 else ""
        if not name:
            print(f"  {RED}[!] Error: Addon name required (spark, hive, kafka, trino).{NC}")
            return 1
        if sub == "install":
            ver = args[4] if len(args) > 4 and args[3] == "--version" else (args[3] if len(args) > 3 and not args[3].startswith("-") else None)
            return 0 if addon_mgr.install(name, ver) else 1
        elif sub == "start":
            return 0 if addon_mgr.start(name) else 1
        elif sub == "stop":
            return 0 if addon_mgr.stop(name) else 1
        elif sub == "status":
            addon_mgr.status(name)
            return 0
        elif sub == "remove":
            return 0 if addon_mgr.remove(name) else 1
        else:
            print(f"  {RED}[!] Unknown addon action: {sub}. Available: list, install, status, start, stop, remove.{NC}")
            return 1
    elif cmd == "upgrade":
        ver = args[1] if len(args) > 1 else None
        return 0 if upgrade_hadoop(ver) else 1
    elif cmd in ("5", "delete"):
        delete_hadoop()
        return 0
    elif cmd in ("6", "service"):
        act = args[1] if len(args) > 1 else "status"
        return manage_system_service(act)
    elif cmd in ("7", "update"):
        return self_update()
    elif cmd in ("8", "completion"):
        target_shell = args[1] if len(args) > 1 else None
        return install_shell_completion(target_shell)
    elif cmd == "--install-completion":
        return install_shell_completion()
    elif cmd == "menu":
        return interactive_loop()
    else:
        print(f"  {RED}[!] Unknown command: {cmd}{NC}")
        print("  Run 'hadoop-handler --help' for usage.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
