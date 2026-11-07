"""Trino (formerly PrestoSQL) addon installer and interactive query engine manager."""

import os
import shutil
import subprocess
import tarfile
import time
import uuid
from pathlib import Path
from typing import Optional

from hadoop_handler.addons.base import BaseAddon
from hadoop_handler.core.cluster import is_port_open
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
    get_default_hadoop_home,
)
from hadoop_handler.core.downloader import download_file, find_cached_archive
from hadoop_handler.core.system import (
    get_active_shell_config,
    register_shell_env,
    send_notification,
)


class TrinoAddon(BaseAddon):
    """Trino (PrestoSQL) distributed SQL engine for interactive HDFS/Hive analytics."""

    id = "trino"
    name = "Trino (PrestoSQL)"
    description = "Fast distributed SQL query engine for interactive queries over HDFS & Hive"
    default_version = "467"
    default_ports = {"Coordinator Web UI": 8080}

    def __init__(self) -> None:
        self.install_dir = get_default_addon_root() / "trino"

    def is_installed(self) -> bool:
        return self.install_dir.exists() and (self.install_dir / "bin/launcher").exists()

    def get_installed_version(self) -> Optional[str]:
        if not self.is_installed():
            return None
        launcher = self.install_dir / "bin/launcher"
        try:
            res = subprocess.run([str(launcher), "--version"], capture_output=True, text=True, timeout=5.0)
            out = res.stdout.strip() or res.stderr.strip()
            for part in out.split():
                if part.isdigit() or "." in part:
                    return part
        except Exception:
            pass
        return "Installed"

    def is_running(self) -> bool:
        launcher = self.install_dir / "bin/launcher"
        if not launcher.exists():
            return False
        try:
            res = subprocess.run([str(launcher), "status"], capture_output=True, text=True, timeout=3.0)
            return "Running as" in res.stdout or is_port_open(8080)
        except Exception:
            return is_port_open(8080)

    def install(self, version: Optional[str] = None) -> bool:
        target_ver = version or self.default_version
        print(DIVIDER)
        print(f"  {BCYAN}ACTION: Installing Trino (PrestoSQL) {target_ver}{NC}")
        print(f"{DIVIDER}\n")

        if self.is_installed():
            inst_ver = self.get_installed_version()
            if inst_ver == target_ver:
                print(f"  {GREEN}[✓] Trino {target_ver} is already installed at {self.install_dir}.{NC}")
                try:
                    reinst = input("  Do you want to re-install / overwrite? (y/N): ").strip()
                except (KeyboardInterrupt, EOFError):
                    return True
                if reinst.lower() != "y":
                    print("  Keeping existing installation.")
                    return True

        tar_name = f"trino-server-{target_ver}.tar.gz"
        tar_path = DOWNLOADS_DIR / tar_name
        download_url = f"https://repo1.maven.org/maven2/io/trino/trino-server/{target_ver}/{tar_name}"

        print(f"  {GRAY}[1/4]{NC} Retrieving Trino {target_ver} from Maven Central...")
        cached_tar = find_cached_archive(tar_name, min_size=50_000_000)
        if cached_tar:
            print(f"        Found valid cached archive at {cached_tar} ({cached_tar.stat().st_size / (1024*1024):.1f} MB). Skipping download.")
            tar_path = cached_tar
        else:
            success = download_file(download_url, tar_path, f"Downloading Trino Server {target_ver}")
            if not success:
                if tar_path.exists():
                    tar_path.unlink()
                return False

        print(f"\n  {GRAY}[2/4]{NC} Extracting Trino server to {self.install_dir}...")
        if self.install_dir.exists():
            shutil.rmtree(self.install_dir, ignore_errors=True)

        self.install_dir.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=self.install_dir.parent)

        extracted = self.install_dir.parent / f"trino-server-{target_ver}"
        if extracted.exists() and extracted != self.install_dir:
            extracted.rename(self.install_dir)

        print(f"\n  {GRAY}[3/4]{NC} Configuring single-node coordinator and Hive connector...")
        etc_dir = self.install_dir / "etc"
        catalog_dir = etc_dir / "catalog"
        data_dir = self.install_dir / "data"

        etc_dir.mkdir(parents=True, exist_ok=True)
        catalog_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)

        node_id = str(uuid.uuid4())
        node_props = f"""node.environment=production
node.id={node_id}
node.data-dir={data_dir}
"""
        (etc_dir / "node.properties").write_text(node_props, encoding="utf-8")

        jvm_config = """-server
-Xmx2G
-XX:+UseG1GC
-XX:G1ReservePercent=15
-Djdk.attach.allowAttachSelf=true
"""
        (etc_dir / "jvm.config").write_text(jvm_config, encoding="utf-8")

        config_props = """coordinator=true
node-scheduler.include-coordinator=true
http-server.http.port=8080
query.max-memory=1GB
query.max-memory-per-node=512MB
discovery.uri=http://localhost:8080
"""
        (etc_dir / "config.properties").write_text(config_props, encoding="utf-8")

        # Hive catalog connector pointing to Hadoop HDFS and Metastore
        hadoop_home = get_default_hadoop_home()
        core_site = hadoop_home / "etc/hadoop/core-site.xml"
        hdfs_site = hadoop_home / "etc/hadoop/hdfs-site.xml"

        hive_catalog = f"""connector.name=hive
hive.metastore.uri=thrift://localhost:9083
hive.config.resources={core_site},{hdfs_site}
"""
        (catalog_dir / "hive.properties").write_text(hive_catalog, encoding="utf-8")

        print(f"\n  {GRAY}[4/4]{NC} Registering TRINO_HOME in shell configuration...")
        register_shell_env({"TRINO_HOME": str(self.install_dir)})

        print(f"\n  {GREEN}[✓] Trino {target_ver} installed and integrated successfully!{NC}")
        shell_conf = get_active_shell_config()
        if shell_conf:
            print(f"      Run: {YELLOW}source {shell_conf}{NC} to activate environment.")
        send_notification("Hadoop Handler", f"Trino {target_ver} addon installed.")
        return True

    def start(self) -> bool:
        if not self.is_installed():
            print(f"  {RED}[!] Trino is not installed. Run 'hadoop-handler addon install trino' first.{NC}")
            return False

        print(f"  [+] Starting Trino Coordinator daemon on port 8080...")
        launcher = self.install_dir / "bin/launcher"
        subprocess.run([str(launcher), "start"], check=False)
        time.sleep(3)

        if self.is_running():
            print(f"  {GREEN}[✓] Trino started successfully!{NC}")
            print(f"      Coordinator Web UI: {CYAN}http://localhost:8080{NC}")
            send_notification("Hadoop Handler", "Trino coordinator service started.")
            return True
        else:
            print(f"  {YELLOW}[*] Start signal sent. Run 'bin/launcher status' for details.{NC}")
            return False

    def stop(self) -> bool:
        if not self.is_installed():
            return True

        print(f"  [+] Stopping Trino Coordinator...")
        launcher = self.install_dir / "bin/launcher"
        subprocess.run([str(launcher), "stop"], check=False, stderr=subprocess.DEVNULL)
        time.sleep(1)
        print(f"  {GREEN}[✓] Trino stopped.{NC}")
        send_notification("Hadoop Handler", "Trino coordinator stopped.")
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
                "Coordinator Web UI (8080)": is_port_open(8080),
            },
        }

    def remove(self) -> bool:
        print(f"  [+] Removing Trino addon...")
        self.stop()
        if self.install_dir.exists():
            shutil.rmtree(self.install_dir, ignore_errors=True)
        print(f"  {GREEN}[✓] Trino removed.{NC}")
        send_notification("Hadoop Handler", "Trino addon removed.")
        return True
