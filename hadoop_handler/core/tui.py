"""Terminal UI: Zero-flicker arrow-key menu navigation and live status badges."""

import os
import sys
from typing import Optional

from hadoop_handler.core.cluster import get_cluster_status
from hadoop_handler.core.config import (
    BCYAN,
    BGREEN,
    BLUE,
    BOLD,
    CYAN,
    DIVIDER,
    GRAY,
    GREEN,
    IS_WINDOWS,
    NC,
    RED,
    VERSION,
    YELLOW,
)

MENU_OPTIONS = [
    "Diagnose & Auto-Repair System Dependencies",
    "Install Apache Hadoop (Dynamic Version Selector)",
    "Verify Hadoop Installation & Running Daemons",
    "Hadoop <-> Java Compatibility Matrix Checker",
    "Start Hadoop Services (HDFS & YARN)",
    "Stop Hadoop Services",
    "Restart Hadoop Services",
    "Java Runtime Selector & Switcher",
    "In-Place Hadoop Upgrade / Downgrade",
    "Ecosystem Addons (Spark, Hive, Kafka, Trino)",
    "Delete Hadoop Completely",
    "System Service Integration (systemd / launchd)",
    "Check for Updates (Self-Update)",
    "Install Shell Autocompletion",
    "Exit",
]


def render_banner_and_status() -> None:
    """Render branded top banner and live cluster status badges."""
    print(f"\033[2J\033[H", end="")
    print(f"{BLUE}================================================================={NC}")
    print(f"       Hadoop Handler v{VERSION} — Cluster Control Center        ")
    print("      Developer: Aditya Pidurkar (github.com/itsadityapidurkar)   ")
    print(f"{BLUE}================================================================={NC}")

    st = get_cluster_status()

    # Hadoop Badge
    if st["is_installed"]:
        hadoop_badge = f"{GREEN}[✓ Installed ({st['hadoop_version']})]{NC}"
    else:
        hadoop_badge = f"{RED}[✗ Not Installed]{NC}"

    # Java Badge
    if st["java_version"] not in ("Missing", "Unknown"):
        java_badge = f"{GREEN}[✓ {st['java_version']}]{NC}"
    else:
        java_badge = f"{RED}[✗ Missing]{NC}"

    # Services Badge
    active_cnt = st["active_core_count"]
    total_cnt = st["total_core_count"]
    if active_cnt > 0:
        services_badge = f"{GREEN}[✓ {active_cnt}/{total_cnt} Daemons Running]{NC}"
    else:
        services_badge = f"{GRAY}[● Stopped]{NC}"

    print(f"  Hadoop:   {hadoop_badge}")
    print(f"  Java:     {java_badge}")
    print(f"  Services: {services_badge}")
    print(DIVIDER)


def read_key() -> str:
    """Read a single keypress without echo across platforms."""
    if IS_WINDOWS:
        import msvcrt

        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            ch2 = msvcrt.getch()
            if ch2 == b"H":
                return "UP"
            elif ch2 == b"P":
                return "DOWN"
        elif ch in (b"\r", b"\n"):
            return "ENTER"
        elif ch == b"\x1b":
            return "ESC"
        try:
            return ch.decode("utf-8")
        except Exception:
            return ""

    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            # Check if more characters are available immediately (escape sequence)
            r, _, _ = select.select([sys.stdin], [], [], 0.05)
            if r:
                seq = sys.stdin.read(2)
                if seq in ("[A", "OA"):
                    return "UP"
                elif seq in ("[B", "OB"):
                    return "DOWN"
            return "ESC"
        elif ch in ("\r", "\n"):
            return "ENTER"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def render_menu_options(selected_idx: int) -> int:
    """Render options in-place with selection cursor."""
    lines_rendered = 0
    for idx, opt in enumerate(MENU_OPTIONS):
        if idx == selected_idx:
            print(f"  {BGREEN}> [{idx:2d}] {opt:<50}{NC}")
        else:
            print(f"    [{idx:2d}] {opt:<50}")
        lines_rendered += 1
    return lines_rendered


def select_menu_option() -> int:
    """Zero-flicker arrow-key menu selector with fallback for non-TTY."""
    if not sys.stdin.isatty():
        print(DIVIDER)
        for idx, opt in enumerate(MENU_OPTIONS):
            print(f"  [{idx:2d}] {opt}")
        print(DIVIDER)
        try:
            val = input("  Select option [0-14]: ").strip()
            return int(val) if val.isdigit() and 0 <= int(val) < len(MENU_OPTIONS) else 14
        except (KeyboardInterrupt, EOFError):
            return 14

    render_banner_and_status()
    print("  Use UP/DOWN arrows or j/k to navigate, ENTER to select:")
    print(DIVIDER)

    selected = 0
    lines_count = len(MENU_OPTIONS)

    # Hide cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    try:
        render_menu_options(selected)

        while True:
            key = read_key()
            old_selected = selected

            if key in ("UP", "k", "K"):
                selected = (selected - 1) % len(MENU_OPTIONS)
            elif key in ("DOWN", "j", "J"):
                selected = (selected + 1) % len(MENU_OPTIONS)
            elif key == "ENTER":
                return selected
            elif key in ("ESC", "q", "Q"):
                return len(MENU_OPTIONS) - 1
            elif key.isdigit():
                val = int(key)
                if 0 <= val < len(MENU_OPTIONS):
                    return val

            if selected != old_selected:
                # Move cursor up and redraw options in-place
                sys.stdout.write(f"\033[{lines_count}A")
                sys.stdout.flush()
                render_menu_options(selected)
    finally:
        # Restore cursor
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
