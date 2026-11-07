"""CLI entry point for hadoop-handler.

Dispatches cross-platform to native bash on Linux/macOS or PowerShell on Windows.
"""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

__version__ = "1.2.0"

PACKAGE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PACKAGE_DIR / "scripts"
CONFIGS_DIR = PACKAGE_DIR / "configs"


def print_help() -> None:
    help_text = f"""Hadoop Handler v{__version__} — Single-Node Cluster Control Center
Developer: Aditya Pidurkar (https://github.com/itsadityapidurkar)

Usage:
  hadoop-handler [COMMAND] [OPTIONS]

Commands:
  (no args)                     Launch interactive TUI control panel (with arrow-key navigation)
  diagnose                      Diagnose and repair system dependencies
  install [--version <ver>]     Install Hadoop with version selection (default: 3.4.2)
  upgrade [<target_version>]    In-place upgrade/downgrade preserving HDFS data
  check-compat [<h_ver>] [<j>]  Check Hadoop and Java matrix compatibility
  java list                     List all detected Java runtimes
  java use <path|version>       Switch active Java runtime for Hadoop
  java switch                   Interactively switch active Java runtime
  verify, status                Verify Hadoop & Java installation status and daemons
  start                         Start HDFS and YARN daemons
  stop                          Stop HDFS and YARN daemons
  restart                       Restart all cluster daemons
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


def print_version() -> None:
    print(f"hadoop-handler {__version__}")


def run_unix(args: list[str]) -> int:
    script_path = SCRIPTS_DIR / "hadoop-handler"
    if not script_path.exists():
        sys.stderr.write(f"[!] Error: Runner script not found at {script_path}\n")
        return 1

    # Ensure user has execute permission on the runner script
    try:
        current_mode = script_path.stat().st_mode
        if not (current_mode & stat.S_IXUSR):
            script_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass

    env = os.environ.copy()
    if CONFIGS_DIR.exists():
        env["HADOOP_HANDLER_CONF_DIR"] = str(CONFIGS_DIR)

    bash_exe = shutil.which("bash") or "/bin/bash"
    cmd = [bash_exe, str(script_path)] + args

    # Try os.execvpe to replace the current Python process directly with bash
    try:
        os.execvpe(bash_exe, cmd, env)
    except (OSError, AttributeError):
        try:
            res = subprocess.run(cmd, env=env)
            return res.returncode
        except KeyboardInterrupt:
            return 130


def run_windows(args: list[str]) -> int:
    script_path = SCRIPTS_DIR / "install.ps1"
    if not script_path.exists():
        sys.stderr.write(f"[!] Error: Runner script not found at {script_path}\n")
        return 1

    ps_exe = shutil.which("powershell") or shutil.which("pwsh")
    if not ps_exe:
        sys.stderr.write("[!] Error: Neither 'powershell' nor 'pwsh' was found in PATH.\n")
        return 1

    cmd = [
        ps_exe,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ] + args

    env = os.environ.copy()
    try:
        res = subprocess.run(cmd, env=env)
        return res.returncode
    except KeyboardInterrupt:
        return 130


def main() -> int:
    args = sys.argv[1:]

    if args:
        first_arg = args[0]
        if first_arg in ("-v", "--version", "-V"):
            print_version()
            return 0
        if first_arg in ("-h", "--help"):
            print_help()
            return 0

    if sys.platform == "win32":
        return run_windows(args)
    return run_unix(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
