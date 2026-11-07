"""Apache Spark addon installer, lifecycle manager, and HDFS/YARN integration."""

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
    get_default_hadoop_home,
)
from hadoop_handler.core.downloader import download_file, resolve_apache_url
from hadoop_handler.core.system import (
    get_active_shell_config,
    register_shell_env,
    send_notification,
)


class SparkAddon(BaseAddon):
    """Apache Spark with native Hadoop HDFS and YARN cluster integration."""

    id = "spark"
    name = "Apache Spark"
    description = "Unified engine for large-scale data processing integrated with HDFS & YARN"
    default_version = "3.5.3"
    default_ports = {"Master Web UI": 8080, "Worker Web UI": 8081, "Master RPC": 7077}

    def __init__(self) -> None:
        self.install_dir = get_default_addon_root() / "spark"

    def is_installed(self) -> bool:
        return self.install_dir.exists() and (self.install_dir / "bin/spark-submit").exists()

    def get_installed_version(self) -> Optional[str]:
        if not self.is_installed():
            return None
        spark_submit = self.install_dir / "bin/spark-submit"
        try:
            res = subprocess.run([str(spark_submit), "--version"], capture_output=True, text=True, timeout=5.0)
            out = res.stderr or res.stdout
            for line in out.splitlines():
                if "version" in line.lower() and "spark" in line.lower():
                    parts = line.strip().split()
                    for p in parts:
                        if p.replace(".", "").isdigit():
                            return p
        except Exception:
            pass
        return "Installed"

    def is_running(self) -> bool:
        daemons = get_active_daemons()
        return "Master" in daemons or is_port_open(7077) or is_port_open(8080)

    def install(self, version: Optional[str] = None) -> bool:
        target_ver = version or self.default_version
        print(DIVIDER)
        print(f"  {BCYAN}ACTION: Installing Apache Spark {target_ver}{NC}")
        print(f"{DIVIDER}\n")

        tar_name = f"spark-{target_ver}-bin-hadoop3.tgz"
        tar_path = DOWNLOADS_DIR / tar_name
        download_url = resolve_apache_url("spark", tar_name, f"spark-{target_ver}")

        print(f"  {GRAY}[1/4]{NC} Retrieving Apache Spark {target_ver} archive...")
        if tar_path.exists() and tar_path.stat().st_size > 10000000:
            print(f"        {tar_name} already cached in ~/Downloads.")
        else:
            success = download_file(download_url, tar_path, f"Downloading Apache Spark {target_ver}")
            if not success:
                if tar_path.exists():
                    tar_path.unlink()
                return False

        print(f"\n  {GRAY}[2/4]{NC} Extracting Spark binaries to {self.install_dir}...")
        if self.install_dir.exists():
            shutil.rmtree(self.install_dir, ignore_errors=True)

        self.install_dir.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=self.install_dir.parent)

        extracted = self.install_dir.parent / f"spark-{target_ver}-bin-hadoop3"
        if extracted.exists() and extracted != self.install_dir:
            extracted.rename(self.install_dir)

        print(f"\n  {GRAY}[3/4]{NC} Configuring Spark integration with Hadoop HDFS & YARN...")
        conf_dir = self.install_dir / "conf"
        conf_dir.mkdir(parents=True, exist_ok=True)

        hadoop_home = str(get_default_hadoop_home())
        java_home = os.environ.get("JAVA_HOME", "")

        spark_env = f"""# Spark Environment Configuration for Hadoop Handler
export SPARK_HOME="{self.install_dir}"
export HADOOP_HOME="{hadoop_home}"
export HADOOP_CONF_DIR="{hadoop_home}/etc/hadoop"
export JAVA_HOME="{java_home}"
export SPARK_MASTER_HOST="localhost"
export SPARK_LOCAL_IP="localhost"
"""
        (conf_dir / "spark-env.sh").write_text(spark_env, encoding="utf-8")
        (conf_dir / "spark-env.sh").chmod(0o755)

        spark_defaults = """# Default system properties included when running spark-submit.
spark.master                     yarn
spark.eventLog.enabled           false
spark.driver.memory              1g
spark.executor.memory            1g
"""
        (conf_dir / "spark-defaults.conf").write_text(spark_defaults, encoding="utf-8")

        print(f"\n  {GRAY}[4/4]{NC} Registering SPARK_HOME in shell configuration...")
        register_shell_env({"SPARK_HOME": str(self.install_dir)})

        print(f"\n  {GREEN}[✓] Apache Spark {target_ver} installed and integrated successfully!{NC}")
        shell_conf = get_active_shell_config()
        if shell_conf:
            print(f"      Run: {YELLOW}source {shell_conf}{NC} to activate environment.")
        send_notification("Hadoop Handler", f"Apache Spark {target_ver} addon installed.")
        return True

    def start(self) -> bool:
        if not self.is_installed():
            print(f"  {RED}[!] Apache Spark is not installed. Run 'hadoop-handler addon install spark' first.{NC}")
            return False

        print(f"  [+] Starting Apache Spark Standalone Cluster (Master & Worker)...")
        start_master = self.install_dir / "sbin/start-master.sh"
        start_worker = self.install_dir / "sbin/start-worker.sh"

        subprocess.run([str(start_master)], check=False)
        time.sleep(1)
        subprocess.run([str(start_worker), "spark://localhost:7077"], check=False)
        time.sleep(2)

        if self.is_running():
            print(f"  {GREEN}[✓] Apache Spark started successfully!{NC}")
            print(f"      Master Web UI: {CYAN}http://localhost:8080{NC}")
            print(f"      Master RPC:    {CYAN}spark://localhost:7077{NC}")
            send_notification("Hadoop Handler", "Apache Spark services started.")
            return True
        else:
            print(f"  {YELLOW}[*] Start command sent. Check {self.install_dir}/logs for details.{NC}")
            return False

    def stop(self) -> bool:
        if not self.is_installed():
            return True

        print(f"  [+] Stopping Apache Spark services...")
        stop_worker = self.install_dir / "sbin/stop-worker.sh"
        stop_master = self.install_dir / "sbin/stop-master.sh"

        subprocess.run([str(stop_worker)], check=False, stderr=subprocess.DEVNULL)
        subprocess.run([str(stop_master)], check=False, stderr=subprocess.DEVNULL)
        time.sleep(1)
        print(f"  {GREEN}[✓] Apache Spark stopped.{NC}")
        send_notification("Hadoop Handler", "Apache Spark services stopped.")
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
                "Master Web UI (8080)": is_port_open(8080),
                "Worker Web UI (8081)": is_port_open(8081),
                "Master RPC (7077)": is_port_open(7077),
            },
        }

    def remove(self) -> bool:
        print(f"  [+] Removing Apache Spark addon...")
        self.stop()
        if self.install_dir.exists():
            shutil.rmtree(self.install_dir, ignore_errors=True)
        print(f"  {GREEN}[✓] Apache Spark removed.{NC}")
        send_notification("Hadoop Handler", "Apache Spark addon removed.")
        return True
