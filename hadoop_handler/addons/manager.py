"""Ecosystem Addon Manager: orchestrates Spark, Hive, Kafka, and Trino."""

from typing import Optional

from hadoop_handler.addons.base import BaseAddon
from hadoop_handler.addons.hive import HiveAddon
from hadoop_handler.addons.kafka import KafkaAddon
from hadoop_handler.addons.spark import SparkAddon
from hadoop_handler.addons.trino import TrinoAddon
from hadoop_handler.core.config import (
    BCYAN,
    DIVIDER,
    GRAY,
    GREEN,
    NC,
    RED,
    YELLOW,
)


class AddonManager:
    """Registry and dispatcher for Hadoop ecosystem addons."""

    def __init__(self) -> None:
        self.addons: dict[str, BaseAddon] = {
            "spark": SparkAddon(),
            "hive": HiveAddon(),
            "kafka": KafkaAddon(),
            "trino": TrinoAddon(),
        }

    def get_addon(self, name: str) -> Optional[BaseAddon]:
        return self.addons.get(name.lower())

    def list_addons(self) -> None:
        """Print status table of all registered ecosystem addons."""
        print(DIVIDER)
        print(f"  {BCYAN}ACTION: Hadoop Ecosystem Addon Registry{NC}")
        print(f"{DIVIDER}\n")
        print(f"  {'ADDON':<12} {'VERSION':<12} {'STATUS':<20} {'PORTS'}")
        print("  -----------------------------------------------------------------")
        for addon_id, addon in self.addons.items():
            installed = addon.is_installed()
            ver = addon.get_installed_version() or "—"
            if not installed:
                status = f"{GRAY}Not Installed{NC}"
            elif addon.is_running():
                status = f"{GREEN}[✓] Running{NC}"
            else:
                status = f"{YELLOW}[●] Stopped{NC}"

            ports_str = ", ".join(f"{p}" for p in addon.default_ports.values())
            print(f"  {addon.name:<22} {ver:<12} {status:<29} {ports_str}")
        print(DIVIDER)
        print(f"  {GRAY}Commands: hadoop-handler addon [install|start|stop|remove] <addon_name>{NC}")

    def install(self, name: str, version: Optional[str] = None) -> bool:
        addon = self.get_addon(name)
        if not addon:
            print(f"  {RED}[!] Unknown addon: '{name}'. Available: spark, hive, kafka, trino.{NC}")
            return False
        return addon.install(version)

    def start(self, name: str) -> bool:
        addon = self.get_addon(name)
        if not addon:
            print(f"  {RED}[!] Unknown addon: '{name}'. Available: spark, hive, kafka, trino.{NC}")
            return False
        return addon.start()

    def stop(self, name: str) -> bool:
        addon = self.get_addon(name)
        if not addon:
            print(f"  {RED}[!] Unknown addon: '{name}'. Available: spark, hive, kafka, trino.{NC}")
            return False
        return addon.stop()

    def status(self, name: str) -> None:
        addon = self.get_addon(name)
        if not addon:
            print(f"  {RED}[!] Unknown addon: '{name}'. Available: spark, hive, kafka, trino.{NC}")
            return
        st = addon.status()
        print(DIVIDER)
        print(f"  {BCYAN}STATUS: {addon.name}{NC}")
        print(f"{DIVIDER}\n")
        print(f"  Installed: {'Yes (' + str(st['version']) + ')' if st['installed'] else 'No'}")
        print(f"  Running:   {'Yes' if st['running'] else 'No'}")
        print("  Ports:")
        for port_name, is_open in st["ports"].items():
            state = f"{GREEN}OPEN{NC}" if is_open else f"{GRAY}CLOSED{NC}"
            print(f"    - {port_name}: {state}")
        print(DIVIDER)

    def remove(self, name: str) -> bool:
        addon = self.get_addon(name)
        if not addon:
            print(f"  {RED}[!] Unknown addon: '{name}'. Available: spark, hive, kafka, trino.{NC}")
            return False
        return addon.remove()

    def interactive_menu(self) -> None:
        """Interactive TUI submenu for managing ecosystem addons."""
        while True:
            print(DIVIDER)
            print(f"  {BCYAN}ECOSYSTEM ADDONS: Spark, Hive, Kafka, Trino{NC}")
            print(f"{DIVIDER}\n")
            print("  Select an addon to manage:")
            items = list(self.addons.items())
            for idx, (aid, addon) in enumerate(items, 1):
                st = addon.status()
                badge = f"{GREEN}[Running]{NC}" if st["running"] else (f"{YELLOW}[Installed]{NC}" if st["installed"] else f"{GRAY}[Not Installed]{NC}")
                print(f"    [ {idx} ] {addon.name:<22} {badge}")
            print("    [ 0 ] Back to Main Menu")
            print(DIVIDER)

            try:
                pick = input(f"  Choose option [0-{len(items)}]: ").strip()
            except (KeyboardInterrupt, EOFError):
                break

            if pick == "0" or not pick:
                break

            if pick.isdigit() and 1 <= int(pick) <= len(items):
                _, chosen_addon = items[int(pick) - 1]
                self._manage_single_addon_interactive(chosen_addon)

    def _manage_single_addon_interactive(self, addon: BaseAddon) -> None:
        while True:
            st = addon.status()
            print(DIVIDER)
            print(f"  {BCYAN}MANAGE: {addon.name}{NC}")
            print(f"{DIVIDER}\n")
            status_str = f"{GREEN}Running{NC}" if st["running"] else (f"{YELLOW}Installed (Stopped){NC}" if st["installed"] else f"{GRAY}Not Installed{NC}")
            print(f"  Status: {status_str}")
            print(f"  Description: {addon.description}\n")

            if not st["installed"]:
                print("    1. Install Addon")
                print("    0. Back")
                opts = ["1", "0"]
            else:
                print("    1. Start Service")
                print("    2. Stop Service")
                print("    3. View Status & Ports")
                print("    4. Remove Addon")
                print("    0. Back")
                opts = ["1", "2", "3", "4", "0"]

            print(DIVIDER)
            try:
                act = input("  Select action: ").strip()
            except (KeyboardInterrupt, EOFError):
                break

            if act == "0" or not act:
                break

            if not st["installed"] and act == "1":
                addon.install()
            elif st["installed"]:
                if act == "1":
                    addon.start()
                elif act == "2":
                    addon.stop()
                elif act == "3":
                    self.status(addon.id)
                elif act == "4":
                    addon.remove()
                    break

            input(f"\n  {YELLOW}Press [Enter] to continue...{NC}")
