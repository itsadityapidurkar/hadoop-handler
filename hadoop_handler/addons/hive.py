"""Apache Hive addon installer, metastore schema init, and HDFS warehouse integration."""

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
from hadoop_handler.core.downloader import (
    download_file,
    find_cached_archive,
    resolve_apache_url,
)
from hadoop_handler.core.system import (
    get_active_shell_config,
    register_shell_env,
    send_notification,
)


class HiveAddon(BaseAddon):
    """Apache Hive data warehouse with Derby/HDFS metastore integration."""

    id = "hive"
    name = "Apache Hive"
    description = "Distributed SQL data warehouse engine built on top of Apache Hadoop HDFS"
    default_version = "3.1.3"
    default_ports = {"Metastore Thrift": 9083, "HiveServer2 JDBC": 10000, "Web UI": 10002}

    def __init__(self) -> None:
        self.install_dir = get_default_addon_root() / "hive"

    def is_installed(self) -> bool:
        return self.install_dir.exists() and (self.install_dir / "bin/hive").exists()

    def get_installed_version(self) -> Optional[str]:
        if not self.is_installed():
            return None
        hive_bin = self.install_dir / "bin/hive"
        try:
            res = subprocess.run([str(hive_bin), "--version"], capture_output=True, text=True, timeout=5.0)
            out = res.stderr or res.stdout
            for line in out.splitlines():
                if "hive" in line.lower() and "version" in line.lower():
                    parts = line.strip().split()
                    for p in parts:
                        if p.replace(".", "").isdigit():
                            return p
        except Exception:
            pass
        return "Installed"

    def is_running(self) -> bool:
        daemons = get_active_daemons()
        return (
            "RunJar" in daemons
            or is_port_open(9083)
            or is_port_open(10000)
        )

    def install(self, version: Optional[str] = None) -> bool:
        target_ver = version or self.default_version
        print(DIVIDER)
        print(f"  {BCYAN}ACTION: Installing Apache Hive {target_ver}{NC}")
        print(f"{DIVIDER}\n")

        if self.is_installed():
            inst_ver = self.get_installed_version()
            if inst_ver == target_ver:
                print(f"  {GREEN}[✓] Apache Hive {target_ver} is already installed at {self.install_dir}.{NC}")
                try:
                    reinst = input("  Do you want to re-install / overwrite? (y/N): ").strip()
                except (KeyboardInterrupt, EOFError):
                    return True
                if reinst.lower() != "y":
                    print("  Keeping existing installation.")
                    return True

        tar_name = f"apache-hive-{target_ver}-bin.tar.gz"
        tar_path = DOWNLOADS_DIR / tar_name
        download_url = resolve_apache_url("hive", tar_name, f"hive-{target_ver}")

        print(f"  {GRAY}[1/5]{NC} Retrieving Apache Hive {target_ver} archive...")
        cached_tar = find_cached_archive(tar_name, min_size=50_000_000)
        if cached_tar:
            print(f"        Found valid cached archive at {cached_tar} ({cached_tar.stat().st_size / (1024*1024):.1f} MB). Skipping download.")
            tar_path = cached_tar
        else:
            success = download_file(download_url, tar_path, f"Downloading Apache Hive {target_ver}")
            if not success:
                if tar_path.exists():
                    tar_path.unlink()
                return False

        print(f"\n  {GRAY}[2/5]{NC} Extracting Hive binaries to {self.install_dir}...")
        if self.install_dir.exists():
            shutil.rmtree(self.install_dir, ignore_errors=True)

        self.install_dir.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=self.install_dir.parent)

        extracted = self.install_dir.parent / f"apache-hive-{target_ver}-bin"
        if extracted.exists() and extracted != self.install_dir:
            extracted.rename(self.install_dir)

        print(f"\n  {GRAY}[3/5]{NC} Resolving Hadoop classpath and Guava dependency conflicts...")
        hadoop_home = get_default_hadoop_home()
        # Fix Guava conflict: Hive 3 ships old Guava 19, Hadoop 3 uses newer Guava 27+
        hive_lib = self.install_dir / "lib"
        for old_guava in hive_lib.glob("guava-19*.jar"):
            old_guava.unlink()
            print("        Removed outdated guava-19 jar from Hive lib.")

        hadoop_guavas = list((hadoop_home / "share/hadoop/common/lib").glob("guava-*.jar"))
        if hadoop_guavas:
            shutil.copy2(hadoop_guavas[0], hive_lib / hadoop_guavas[0].name)
            print(f"        Copied compatible {hadoop_guavas[0].name} from Hadoop.")

        print(f"\n  {GRAY}[4/5]{NC} Configuring hive-site.xml and Derby metastore warehouse...")
        conf_dir = self.install_dir / "conf"
        conf_dir.mkdir(parents=True, exist_ok=True)

        hive_site = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>javax.jdo.option.ConnectionURL</name>
        <value>jdbc:derby:;databaseName=metastore_db;create=true</value>
        <description>JDBC connect string for a JDBC metastore</description>
    </property>
    <property>
        <name>javax.jdo.option.ConnectionDriverName</name>
        <value>org.apache.derby.jdbc.EmbeddedDriver</value>
        <description>Driver class name for a JDBC metastore</description>
    </property>
    <property>
        <name>hive.metastore.warehouse.dir</name>
        <value>/user/hive/warehouse</value>
        <description>location of default database for the warehouse</description>
    </property>
    <property>
        <name>hive.metastore.uris</name>
        <value>thrift://localhost:9083</value>
    </property>
    <property>
        <name>hive.metastore.schema.verification</name>
        <value>false</value>
    </property>
</configuration>
"""
        (conf_dir / "hive-site.xml").write_text(hive_site, encoding="utf-8")

        # Initialize schema if schematool exists
        schematool = self.install_dir / "bin/schematool"
        if schematool.exists():
            print("        Initializing Derby metastore schema...")
            env = os.environ.copy()
            env["HADOOP_HOME"] = str(hadoop_home)
            env["HIVE_HOME"] = str(self.install_dir)
            subprocess.run([str(schematool), "-dbType", "derby", "-initSchema"], env=env, capture_output=True, check=False)

        print(f"\n  {GRAY}[5/5]{NC} Registering HIVE_HOME in shell configuration...")
        register_shell_env({"HIVE_HOME": str(self.install_dir)})

        print(f"\n  {GREEN}[✓] Apache Hive {target_ver} installed and configured successfully!{NC}")
        shell_conf = get_active_shell_config()
        if shell_conf:
            print(f"      Run: {YELLOW}source {shell_conf}{NC} to activate environment.")
        send_notification("Hadoop Handler", f"Apache Hive {target_ver} addon installed.")
        return True

    def start(self) -> bool:
        if not self.is_installed():
            print(f"  {RED}[!] Apache Hive is not installed. Run 'hadoop-handler addon install hive' first.{NC}")
            return False

        print(f"  [+] Starting Apache Hive Metastore Service (Thrift on port 9083)...")
        hive_bin = self.install_dir / "bin/hive"
        logs_dir = self.install_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["HADOOP_HOME"] = str(get_default_hadoop_home())
        env["HIVE_HOME"] = str(self.install_dir)

        log_file = logs_dir / "metastore.log"
        with open(log_file, "a") as f:
            subprocess.Popen([str(hive_bin), "--service", "metastore"], stdout=f, stderr=f, env=env)

        time.sleep(3)
        if self.is_running():
            print(f"  {GREEN}[✓] Apache Hive Metastore started successfully!{NC}")
            print(f"      Thrift Endpoint: {CYAN}thrift://localhost:9083{NC}")
            send_notification("Hadoop Handler", "Apache Hive Metastore service started.")
            return True
        else:
            print(f"  {YELLOW}[*] Start signal sent. Check {log_file} for startup details.{NC}")
            return False

    def stop(self) -> bool:
        if not self.is_installed():
            return True

        print(f"  [+] Stopping Apache Hive services...")
        # Kill running metastore or hiveserver2 Java processes
        try:
            res = subprocess.run(["jps", "-l"], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and ("HiveMetaStore" in parts[1] or "HiveServer2" in parts[1]):
                    pid = parts[0]
                    subprocess.run(["kill", "-9", pid], check=False)
                    print(f"        Stopped Hive process (PID {pid}).")
        except Exception:
            pass

        print(f"  {GREEN}[✓] Apache Hive stopped.{NC}")
        send_notification("Hadoop Handler", "Apache Hive services stopped.")
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
                "Metastore Thrift (9083)": is_port_open(9083),
                "HiveServer2 (10000)": is_port_open(10000),
            },
        }

    def remove(self) -> bool:
        print(f"  [+] Removing Apache Hive addon...")
        self.stop()
        if self.install_dir.exists():
            shutil.rmtree(self.install_dir, ignore_errors=True)
        print(f"  {GREEN}[✓] Apache Hive removed.{NC}")
        send_notification("Hadoop Handler", "Apache Hive addon removed.")
        return True
