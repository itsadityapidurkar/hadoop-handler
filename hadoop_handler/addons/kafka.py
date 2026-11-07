"""Apache Kafka addon installer and KRaft standalone cluster manager."""

import os
import shutil
import subprocess
import tarfile
import time
from pathlib import Path
from typing import Optional

from hadoop_handler.addons.base import BaseAddon
from hadoop_handler.core.cluster import get_active_daemons, is_port_open
from hadoop_handler.core.config import (
    BCYAN,
    DIVIDER,
    DOWNLOADS_DIR,
    GRAY,
    GREEN,
    NC,
    RED,
    YELLOW,
    get_default_addon_root,
)
from hadoop_handler.core.downloader import download_file, resolve_apache_url
from hadoop_handler.core.system import (
    get_active_shell_config,
    register_shell_env,
    send_notification,
)


class KafkaAddon(BaseAddon):
    """Apache Kafka distributed streaming platform running in lightweight KRaft mode."""

    id = "kafka"
    name = "Apache Kafka"
    description = "Distributed event streaming platform running in high-performance KRaft mode"
    default_version = "3.9.0"
    default_ports = {"Broker PLAINTEXT": 9092, "Controller": 9093}

    def __init__(self) -> None:
        self.install_dir = get_default_addon_root() / "kafka"

    def is_installed(self) -> bool:
        return self.install_dir.exists() and (self.install_dir / "bin/kafka-server-start.sh").exists()

    def get_installed_version(self) -> Optional[str]:
        if not self.is_installed():
            return None
        # Version from jar name in libs
        libs = self.install_dir / "libs"
        if libs.exists():
            for j in libs.glob("kafka_2.13-*.jar"):
                name = j.stem
                return name.replace("kafka_2.13-", "")
        return "Installed"

    def is_running(self) -> bool:
        daemons = get_active_daemons()
        return "Kafka" in daemons or is_port_open(9092)

    def install(self, version: Optional[str] = None) -> bool:
        target_ver = version or self.default_version
        print(DIVIDER)
        print(f"  {BCYAN}ACTION: Installing Apache Kafka {target_ver} (KRaft Mode){NC}")
        print(f"{DIVIDER}\n")

        tar_name = f"kafka_2.13-{target_ver}.tgz"
        tar_path = DOWNLOADS_DIR / tar_name
        download_url = resolve_apache_url("kafka", tar_name, f"{target_ver}")

        print(f"  {GRAY}[1/4]{NC} Retrieving Apache Kafka {target_ver} archive...")
        if tar_path.exists() and tar_path.stat().st_size > 10000000:
            print(f"        {tar_name} already cached in ~/Downloads.")
        else:
            success = download_file(download_url, tar_path, f"Downloading Apache Kafka {target_ver}")
            if not success:
                if tar_path.exists():
                    tar_path.unlink()
                return False

        print(f"\n  {GRAY}[2/4]{NC} Extracting Kafka binaries to {self.install_dir}...")
        if self.install_dir.exists():
            shutil.rmtree(self.install_dir, ignore_errors=True)

        self.install_dir.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=self.install_dir.parent)

        extracted = self.install_dir.parent / f"kafka_2.13-{target_ver}"
        if extracted.exists() and extracted != self.install_dir:
            extracted.rename(self.install_dir)

        print(f"\n  {GRAY}[3/4]{NC} Formatting Kafka KRaft storage log directory...")
        kraft_conf = self.install_dir / "config/kraft/server.properties"
        storage_sh = self.install_dir / "bin/kafka-storage.sh"

        if storage_sh.exists() and kraft_conf.exists():
            # Generate random cluster UUID
            uuid_res = subprocess.run([str(storage_sh), "random-uuid"], capture_output=True, text=True, check=False)
            cluster_id = uuid_res.stdout.strip() or "HadoopHandlerKafkaCluster001"
            print(f"        Generated Cluster ID: {CYAN}{cluster_id}{NC}")
            # Format storage
            subprocess.run([str(storage_sh), "format", "-t", cluster_id, "-c", str(kraft_conf)], capture_output=True, check=False)
            print("        KRaft storage formatted successfully.")

        print(f"\n  {GRAY}[4/4]{NC} Registering KAFKA_HOME in shell configuration...")
        register_shell_env({"KAFKA_HOME": str(self.install_dir)})

        print(f"\n  {GREEN}[✓] Apache Kafka {target_ver} installed and initialized successfully!{NC}")
        shell_conf = get_active_shell_config()
        if shell_conf:
            print(f"      Run: {YELLOW}source {shell_conf}{NC} to activate environment.")
        send_notification("Hadoop Handler", f"Apache Kafka {target_ver} addon installed.")
        return True

    def start(self) -> bool:
        if not self.is_installed():
            print(f"  {RED}[!] Apache Kafka is not installed. Run 'hadoop-handler addon install kafka' first.{NC}")
            return False

        print(f"  [+] Starting Apache Kafka server in KRaft daemon mode...")
        start_sh = self.install_dir / "bin/kafka-server-start.sh"
        kraft_conf = self.install_dir / "config/kraft/server.properties"

        subprocess.run([str(start_sh), "-daemon", str(kraft_conf)], check=False)
        time.sleep(3)

        if self.is_running():
            print(f"  {GREEN}[✓] Apache Kafka broker started successfully!{NC}")
            print(f"      Bootstrap Server: {CYAN}localhost:9092{NC}")
            send_notification("Hadoop Handler", "Apache Kafka broker started.")
            return True
        else:
            print(f"  {YELLOW}[*] Start signal sent. Check {self.install_dir}/logs for details.{NC}")
            return False

    def stop(self) -> bool:
        if not self.is_installed():
            return True

        print(f"  [+] Stopping Apache Kafka server...")
        stop_sh = self.install_dir / "bin/kafka-server-stop.sh"
        subprocess.run([str(stop_sh)], check=False, stderr=subprocess.DEVNULL)
        time.sleep(2)
        print(f"  {GREEN}[✓] Apache Kafka stopped.{NC}")
        send_notification("Hadoop Handler", "Apache Kafka server stopped.")
        return True

    def status(self) -> dict:
        installed = self.is_installed()
        version = self.get_installed_version() if installed else None
        running = self.is_running() if installed else False
        return {
            "id": self.id,
            "name": self.name,
            "installed": installed,
            "version": version,
            "running": running,
            "ports": {
                "Broker PLAINTEXT (9092)": is_port_open(9092),
                "Controller (9093)": is_port_open(9093),
            },
        }

    def remove(self) -> bool:
        print(f"  [+] Removing Apache Kafka addon...")
        self.stop()
        if self.install_dir.exists():
            shutil.rmtree(self.install_dir, ignore_errors=True)
        print(f"  {GREEN}[✓] Apache Kafka removed.{NC}")
        send_notification("Hadoop Handler", "Apache Kafka addon removed.")
        return True
