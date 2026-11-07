"""Hadoop Single-Node cluster lifecycle management: install, upgrade, daemons, verify, delete."""

import os
import shutil
import socket
import subprocess
import tarfile
import time
from pathlib import Path
from typing import Optional

from hadoop_handler.core.config import (
    BCYAN,
    BRED,
    CONFIGS_DIR,
    CYAN,
    DIVIDER,
    DOWNLOADS_DIR,
    GRAY,
    GREEN,
    IS_LINUX,
    IS_MACOS,
    IS_WINDOWS,
    NC,
    RED,
    USER_HOME,
    YELLOW,
    get_default_data_dir,
    get_default_hadoop_home,
    get_default_tmp_dir,
)
from hadoop_handler.core.downloader import download_file, resolve_hadoop_url
from hadoop_handler.core.java import check_compatibility, detect_installed_javas, switch_java
from hadoop_handler.core.system import (
    get_active_shell_config,
    register_shell_env,
    remove_shell_env,
    send_notification,
)


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    """Test if a local TCP port is open and listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def get_active_daemons() -> list[str]:
    """Get list of active Hadoop/Java daemons from jps."""
    jps_bin = shutil.which("jps")
    if not jps_bin and os.environ.get("JAVA_HOME"):
        cand = Path(os.environ["JAVA_HOME"]) / "bin" / ("jps.exe" if IS_WINDOWS else "jps")
        if cand.exists():
            jps_bin = str(cand)

    if not jps_bin:
        return []

    try:
        res = subprocess.run([jps_bin], capture_output=True, text=True, timeout=3.0)
        daemons = []
        for line in res.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] != "Jps":
                daemons.append(parts[1])
        return daemons
    except Exception:
        return []


def get_cluster_status() -> dict:
    """Retrieve detailed status of local Hadoop cluster."""
    hadoop_home = get_default_hadoop_home()
    is_installed = hadoop_home.exists() and (hadoop_home / "bin").exists()

    hadoop_ver = "Not Installed"
    if is_installed:
        which_hadoop = str(hadoop_home / "bin" / ("hadoop.cmd" if IS_WINDOWS else "hadoop"))
        if Path(which_hadoop).exists():
            try:
                res = subprocess.run([which_hadoop, "version"], capture_output=True, text=True, timeout=3.0)
                first = res.stdout.splitlines()[0] if res.stdout else ""
                hadoop_ver = first.split()[1] if len(first.split()) > 1 else "Unknown"
            except Exception:
                hadoop_ver = "Installed"

    active_java_home = os.environ.get("JAVA_HOME", "")
    java_ver = "Missing"
    java_cmd = str(Path(active_java_home) / "bin/java") if active_java_home else shutil.which("java")
    if java_cmd:
        try:
            res = subprocess.run([java_cmd, "-version"], capture_output=True, text=True, timeout=3.0)
            v_out = res.stderr or res.stdout
            if v_out:
                first = v_out.splitlines()[0]
                java_ver = first.replace("openjdk version", "").replace("java version", "").strip(' "')
        except Exception:
            java_ver = "Detected"

    daemons = get_active_daemons()
    core_daemons = ["NameNode", "DataNode", "SecondaryNameNode", "ResourceManager", "NodeManager"]
    active_core = [d for d in core_daemons if d in daemons]

    return {
        "is_installed": is_installed,
        "hadoop_home": hadoop_home,
        "hadoop_version": hadoop_ver,
        "java_version": java_ver,
        "active_daemons": daemons,
        "active_core_count": len(active_core),
        "total_core_count": len(core_daemons),
        "ports": {
            "namenode_web": is_port_open(9870),
            "resourcemanager_web": is_port_open(8088),
            "hdfs_rpc": is_port_open(9000),
        },
    }


def verify_hadoop() -> None:
    """Detailed cluster status and diagnostics readout."""
    print(DIVIDER)
    print(f"  {BCYAN}ACTION: Verifying Hadoop System Status{NC}")
    print(f"{DIVIDER}\n")

    st = get_cluster_status()
    if not st["is_installed"]:
        print(f"  {RED}[!] Error: Hadoop is not installed or HADOOP_HOME is not set correctly.{NC}")
        return

    print(f"  {GRAY}HADOOP_HOME:{NC}   {GREEN}{st['hadoop_home']}{NC}")
    print(f"  {GRAY}Hadoop Version:{NC} {GREEN}{st['hadoop_version']}{NC}")
    print(f"  {GRAY}Java Runtime:{NC}   {GREEN}{st['java_version']}{NC}")

    print(f"\n  {GRAY}Active Cluster Daemons (jps):{NC}")
    print(f"  {DIVIDER}")
    daemons = st["active_daemons"]
    if daemons:
        for d in daemons:
            print(f"  [✓] {d}")
    else:
        print("  [●] No Hadoop daemons currently running.")

    print(f"\n  {GRAY}Service Web UIs and RPC Ports:{NC}")
    print(f"  {DIVIDER}")
    p = st["ports"]
    nn_status = f"{GREEN}ONLINE{NC} (http://localhost:9870)" if p["namenode_web"] else f"{GRAY}OFFLINE{NC}"
    rm_status = f"{GREEN}ONLINE{NC} (http://localhost:8088)" if p["resourcemanager_web"] else f"{GRAY}OFFLINE{NC}"
    rpc_status = f"{GREEN}LISTENING{NC} (hdfs://localhost:9000)" if p["hdfs_rpc"] else f"{GRAY}NOT CONNECTED{NC}"

    print(f"  HDFS NameNode Web:        {nn_status}")
    print(f"  YARN ResourceManager Web: {rm_status}")
    print(f"  HDFS Default RPC (9000):  {rpc_status}")

    print()
    check_compatibility(st["hadoop_version"])


def install_hadoop(version: Optional[str] = None) -> bool:
    """Install and configure Apache Hadoop with dynamic version selection."""
    print(DIVIDER)
    print(f"  {BCYAN}ACTION: Installing Apache Hadoop (Dynamic Version Selector){NC}")
    print(f"{DIVIDER}\n")

    selected_ver = version
    if not selected_ver:
        print("  Select Hadoop Version to Install:")
        print("    1. 3.4.2 (Latest Stable, Java 8/11/17/21) [Default]")
        print("    2. 3.4.1 (Java 8/11/17/21)")
        print("    3. 3.3.6 (Production LTS, Java 8/11/17)")
        print("    4. 3.3.5 (Java 8/11)")
        print("    5. 3.2.4 (Legacy, Java 8/11)")
        print("    6. Custom version")
        try:
            choice = input("  Enter choice [1-6, default 1]: ").strip()
            mapping = {
                "1": "3.4.2",
                "2": "3.4.1",
                "3": "3.3.6",
                "4": "3.3.5",
                "5": "3.2.4",
            }
            if choice == "6":
                selected_ver = input("  Enter version string (e.g. 3.4.0): ").strip()
            else:
                selected_ver = mapping.get(choice, "3.4.2")
        except (KeyboardInterrupt, EOFError):
            print("\n  Installation cancelled.")
            return False

    selected_ver = selected_ver or "3.4.2"
    print(f"\n  Target Hadoop Version: {GREEN}{selected_ver}{NC}")

    # 1. Java Validation
    print(f"\n  {GRAY}[1/8]{NC} Validating Java runtime...")
    jvms = detect_installed_javas()
    if not jvms:
        print(f"  {RED}[!] No Java runtimes detected on this system. Please install OpenJDK.{NC}")
        return False

    active_jvm = next((j for j in jvms if j.is_active), jvms[0])
    print(f"        Active Java: {CYAN}Java {active_jvm.major}{NC} ({active_jvm.path})")
    compat, _, _ = check_compatibility(selected_ver, str(active_jvm.major))
    if not compat:
        try:
            sw = input("\n  Would you like to select an alternative installed Java? (y/N): ").strip()
            if sw.lower() == "y":
                switch_java()
                jvms = detect_installed_javas()
                active_jvm = next((j for j in jvms if j.is_active), jvms[0])
        except (KeyboardInterrupt, EOFError):
            pass

    target_home = get_default_hadoop_home()
    target_data = get_default_data_dir()
    target_tmp = get_default_tmp_dir()
    tar_name = f"hadoop-{selected_ver}.tar.gz"
    tar_path = DOWNLOADS_DIR / tar_name
    download_url = resolve_hadoop_url(selected_ver)

    # 2. System Directories
    print(f"\n  {GRAY}[2/8]{NC} Creating required system directories...")
    (target_data / "namenode").mkdir(parents=True, exist_ok=True)
    (target_data / "datanode").mkdir(parents=True, exist_ok=True)
    target_tmp.mkdir(parents=True, exist_ok=True)

    # 3. Retrieve Tarball
    print(f"\n  {GRAY}[3/8]{NC} Retrieving Apache Hadoop {selected_ver} tarball...")
    if tar_path.exists() and tar_path.stat().st_size > 1000000:
        print(f"        {tar_name} already cached in ~/Downloads. Skipping download.")
    else:
        success = download_file(download_url, tar_path, f"Retrieving Apache Hadoop {selected_ver}")
        if not success:
            if tar_path.exists():
                tar_path.unlink()
            return False
        send_notification("Hadoop Handler", f"Apache Hadoop {selected_ver} downloaded.")

    # 4. Extract
    print(f"\n  {GRAY}[4/8]{NC} Extracting and relocating binaries...")
    if target_home.exists():
        shutil.rmtree(target_home, ignore_errors=True)

    extract_parent = target_home.parent
    extract_parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=extract_parent)

    extracted_dir = extract_parent / f"hadoop-{selected_ver}"
    if extracted_dir.exists() and extracted_dir != target_home:
        extracted_dir.rename(target_home)

    print("        Extraction completed successfully.")
    send_notification("Hadoop Handler", f"Apache Hadoop {selected_ver} binaries extracted.")

    # 5. Passwordless SSH Configuration (Unix)
    if not IS_WINDOWS:
        print(f"\n  {GRAY}[5/8]{NC} Configuring passwordless SSH keys...")
        ssh_dir = USER_HOME / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        id_rsa = ssh_dir / "id_rsa"
        id_rsa_pub = ssh_dir / "id_rsa.pub"
        auth_keys = ssh_dir / "authorized_keys"

        if not id_rsa.exists():
            subprocess.run(["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", str(id_rsa), "-N", ""], check=False)

        if id_rsa_pub.exists():
            pub_key = id_rsa_pub.read_text().strip()
            existing_auth = auth_keys.read_text() if auth_keys.exists() else ""
            if pub_key not in existing_auth:
                with open(auth_keys, "a") as f:
                    f.write(f"\n{pub_key}\n")
            auth_keys.chmod(0o600)

        # Pre-scan localhost
        known_hosts = ssh_dir / "known_hosts"
        res = subprocess.run(["ssh-keyscan", "-H", "localhost"], capture_output=True, text=True)
        if res.stdout:
            with open(known_hosts, "a") as f:
                f.write(res.stdout)

    # 6. Shell Environment Variables
    print(f"\n  {GRAY}[6/8]{NC} Registering path variables in shell configuration...")
    env_vars = {
        "JAVA_HOME": str(active_jvm.path),
        "HADOOP_HOME": str(target_home),
        "HADOOP_CONF_DIR": f"{target_home}/etc/hadoop",
        "HADOOP_COMMON_HOME": str(target_home),
        "HADOOP_HDFS_HOME": str(target_home),
        "HADOOP_MAPRED_HOME": str(target_home),
        "YARN_HOME": str(target_home),
        "HADOOP_COMMON_LIB_NATIVE_DIR": f"{target_home}/lib/native",
    }
    register_shell_env(env_vars)
    for k, v in env_vars.items():
        os.environ[k] = v

    # 7. XML Templates & hadoop-env.sh
    print(f"\n  {GRAY}[7/8]{NC} Building cluster configuration files...")
    conf_dir = target_home / "etc/hadoop"
    conf_dir.mkdir(parents=True, exist_ok=True)

    # Template core-site.xml
    core_site = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://localhost:9000</value>
    </property>
    <property>
        <name>hadoop.tmp.dir</name>
        <value>{target_tmp}</value>
    </property>
</configuration>
"""
    (conf_dir / "core-site.xml").write_text(core_site, encoding="utf-8")

    # Template hdfs-site.xml
    hdfs_site = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>file://{target_data}/namenode</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>file://{target_data}/datanode</value>
    </property>
</configuration>
"""
    (conf_dir / "hdfs-site.xml").write_text(hdfs_site, encoding="utf-8")

    # Copy mapred, yarn, workers from package templates if available
    for tpl in ["mapred-site.xml", "yarn-site.xml", "workers"]:
        src = CONFIGS_DIR / tpl
        if src.exists():
            shutil.copy2(src, conf_dir / tpl)
        else:
            if tpl == "workers":
                (conf_dir / "workers").write_text("localhost\n", encoding="utf-8")

    # Configure hadoop-env.sh
    hadoop_env_sh = conf_dir / "hadoop-env.sh"
    if hadoop_env_sh.exists():
        content = hadoop_env_sh.read_text(encoding="utf-8")
        import re
        if "export JAVA_HOME=" in content:
            content = re.sub(r"^#?\s*export JAVA_HOME=.*$", f"export JAVA_HOME={active_jvm.path}", content, flags=re.MULTILINE)
        else:
            content += f"\nexport JAVA_HOME={active_jvm.path}\n"
        hadoop_env_sh.write_text(content, encoding="utf-8")

    # 8. Format NameNode
    print(f"\n  {GRAY}[8/8]{NC} Formatting HDFS NameNode system...")
    hdfs_bin = str(target_home / "bin" / ("hdfs.cmd" if IS_WINDOWS else "hdfs"))
    subprocess.run([hdfs_bin, "namenode", "-format", "-force"], check=False)

    print(f"\n  {GREEN}[✓] Installation of Hadoop {selected_ver} completed successfully!{NC}")
    shell_conf = get_active_shell_config()
    if shell_conf:
        print(f"      Reload your shell profile: {YELLOW}source {shell_conf}{NC}")
    send_notification("Hadoop Handler", f"Hadoop {selected_ver} installation completed.")
    return True


def upgrade_hadoop(target_version: Optional[str] = None) -> bool:
    """In-place upgrade or downgrade preserving XML configs and HDFS data blocks."""
    print(DIVIDER)
    print(f"  {BCYAN}ACTION: In-Place Hadoop Upgrade / Downgrade{NC}")
    print(f"{DIVIDER}\n")

    st = get_cluster_status()
    if not st["is_installed"]:
        print(f"  {RED}[!] Error: No active Hadoop installation found. Please run Install first.{NC}")
        return False

    current_ver = st["hadoop_version"]
    print(f"  Current Hadoop Version: {CYAN}{current_ver}{NC}")

    target_ver = target_version
    if not target_ver:
        print("\n  Select Target Hadoop Version to Migrate To:")
        print("    1. 3.4.2 (Latest Stable, Java 8/11/17/21)")
        print("    2. 3.4.1 (Java 8/11/17/21)")
        print("    3. 3.3.6 (LTS Production, Java 8/11/17)")
        print("    4. 3.3.5 (Java 8/11)")
        print("    5. 3.2.4 (Legacy, Java 8/11)")
        print("    6. Custom version")
        print("    7. Cancel")
        try:
            choice = input("  Enter choice [1-7]: ").strip()
            mapping = {
                "1": "3.4.2",
                "2": "3.4.1",
                "3": "3.3.6",
                "4": "3.3.5",
                "5": "3.2.4",
            }
            if choice == "6":
                target_ver = input("  Enter target version: ").strip()
            elif choice == "7":
                print("  Migration cancelled.")
                return False
            else:
                target_ver = mapping.get(choice, "3.4.2")
        except (KeyboardInterrupt, EOFError):
            print("\n  Migration cancelled.")
            return False

    if current_ver == target_ver:
        print(f"  {YELLOW}[*] Cluster is already running Hadoop {target_ver}.{NC}")
        return True

    print(f"\n  Target Hadoop Version: {GREEN}{target_ver}{NC}")
    compat, _, _ = check_compatibility(target_ver)
    if not compat:
        proceed = input("\n  Proceed anyway despite compatibility warning? (y/N): ").strip()
        if proceed.lower() != "y":
            print("  Migration aborted.")
            return False

    hadoop_home = st["hadoop_home"]
    conf_src = hadoop_home / "etc/hadoop"

    # Step 1: Stop Services
    print(f"\n  {GRAY}[1/5]{NC} Stopping active cluster daemons...")
    stop_services()

    # Step 2: Backup Configs
    print(f"  {GRAY}[2/5]{NC} Backing up cluster XML configurations...")
    backup_dir = USER_HOME / f".hadoop-handler/backup_{int(time.time())}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for f in ["core-site.xml", "hdfs-site.xml", "mapred-site.xml", "yarn-site.xml", "workers", "hadoop-env.sh"]:
        if (conf_src / f).exists():
            shutil.copy2(conf_src / f, backup_dir / f)
    print(f"        Configurations backed up to {backup_dir}.")

    # Step 3: Retrieve Archive
    print(f"\n  {GRAY}[3/5]{NC} Retrieving Hadoop {target_ver}...")
    tar_name = f"hadoop-{target_ver}.tar.gz"
    tar_path = DOWNLOADS_DIR / tar_name
    if not tar_path.exists():
        download_url = resolve_hadoop_url(target_ver)
        if not download_file(download_url, tar_path, f"Downloading Hadoop {target_ver}"):
            return False

    # Step 4: Swap Binaries (Preserving HDFS Data Blocks)
    print(f"\n  {GRAY}[4/5]{NC} Swapping binaries (preserving existing HDFS data blocks)...")
    shutil.rmtree(hadoop_home, ignore_errors=True)
    extract_parent = hadoop_home.parent
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=extract_parent)
    extracted = extract_parent / f"hadoop-{target_ver}"
    if extracted.exists() and extracted != hadoop_home:
        extracted.rename(hadoop_home)

    # Step 5: Restore Configs
    print(f"\n  {GRAY}[5/5]{NC} Restoring cluster XML configurations...")
    new_conf = hadoop_home / "etc/hadoop"
    new_conf.mkdir(parents=True, exist_ok=True)
    for item in backup_dir.iterdir():
        shutil.copy2(item, new_conf / item.name)
    shutil.rmtree(backup_dir, ignore_errors=True)

    print(f"\n  {GREEN}[✓] In-place migration to Hadoop {target_ver} successful!{NC}")
    print("      (Existing HDFS data blocks and configuration files were preserved).")
    send_notification("Hadoop Handler", f"Hadoop migrated to version {target_ver}.")

    try:
        start_now = input("\n  Do you want to start cluster services now? (Y/n): ").strip()
        if start_now.lower() != "n":
            start_services()
    except (KeyboardInterrupt, EOFError):
        pass
    return True


def start_services() -> None:
    """Start HDFS and YARN daemons."""
    print(DIVIDER)
    print(f"  {BCYAN}ACTION: Starting Hadoop Services (HDFS & YARN){NC}")
    print(f"{DIVIDER}\n")

    st = get_cluster_status()
    if not st["is_installed"]:
        print(f"  {RED}[!] Error: Hadoop is not installed.{NC}")
        return

    hadoop_home = st["hadoop_home"]
    sbin = hadoop_home / "sbin"

    if IS_WINDOWS:
        start_dfs = str(sbin / "start-dfs.cmd")
        start_yarn = str(sbin / "start-yarn.cmd")
        print(f"  {GRAY}[1/2]{NC} Starting HDFS...")
        subprocess.run([start_dfs], check=False)
        print(f"  {GRAY}[2/2]{NC} Starting YARN...")
        subprocess.run([start_yarn], check=False)
    else:
        start_dfs = str(sbin / "start-dfs.sh")
        start_yarn = str(sbin / "start-yarn.sh")
        print(f"  {GRAY}[1/2]{NC} Starting Distributed File System (HDFS)...")
        subprocess.run([start_dfs], check=False)
        print(f"\n  {GRAY}[2/2]{NC} Starting YARN Resource Manager & Nodes...")
        subprocess.run([start_yarn], check=False)

    time.sleep(2)
    print(f"\n  {GREEN}[✓] Active Hadoop daemons after startup:{NC}")
    print(f"  {DIVIDER}")
    daemons = get_active_daemons()
    for d in daemons:
        print(f"  [✓] {d}")
    send_notification("Hadoop Handler", "Hadoop cluster services (HDFS & YARN) started.")


def stop_services() -> None:
    """Stop HDFS and YARN daemons."""
    print(DIVIDER)
    print(f"  {BCYAN}ACTION: Stopping Hadoop Services (YARN & HDFS){NC}")
    print(f"{DIVIDER}\n")

    st = get_cluster_status()
    if not st["is_installed"]:
        print(f"  {RED}[!] Error: Hadoop is not installed.{NC}")
        return

    hadoop_home = st["hadoop_home"]
    sbin = hadoop_home / "sbin"

    if IS_WINDOWS:
        stop_all = str(sbin / "stop-all.cmd")
        subprocess.run([stop_all], check=False)
    else:
        stop_yarn = str(sbin / "stop-yarn.sh")
        stop_dfs = str(sbin / "stop-dfs.sh")
        print(f"  {GRAY}[1/2]{NC} Stopping YARN Resource Manager & Nodes...")
        subprocess.run([stop_yarn], check=False)
        print(f"\n  {GRAY}[2/2]{NC} Stopping Distributed File System (HDFS)...")
        subprocess.run([stop_dfs], check=False)

    time.sleep(1)
    print(f"\n  {GREEN}[✓] Active Hadoop daemons after stop signal:{NC}")
    print(f"  {DIVIDER}")
    daemons = get_active_daemons()
    if daemons:
        for d in daemons:
            print(f"  [!] {d}")
    else:
        print("  [●] All cluster daemons stopped.")
    send_notification("Hadoop Handler", "Hadoop cluster services stopped.")


def restart_services() -> None:
    """Restart all cluster services."""
    stop_services()
    time.sleep(2)
    start_services()


def delete_hadoop() -> None:
    """Completely wipe Hadoop installation and data."""
    print(DIVIDER)
    print(f"  {BRED}ACTION: Completely Uninstalling Hadoop{NC}")
    print(f"{DIVIDER}\n")
    print(f"  {RED}[!] WARNING: This will permanently delete your Hadoop installation,{NC}")
    print(f"  {RED}    configuration files, HDFS directories, and path profiles.{NC}\n")

    try:
        confirm = input("  Are you sure you want to proceed? (y/N): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n  Uninstall aborted.")
        return

    if confirm.lower() != "y":
        print(f"  {YELLOW}Uninstall aborted.{NC}")
        return

    st = get_cluster_status()
    stop_services()

    print(f"\n  {GRAY}[1/3]{NC} Deleting binaries and directories...")
    if st["hadoop_home"].exists():
        shutil.rmtree(st["hadoop_home"], ignore_errors=True)
        print(f"        Deleted {st['hadoop_home']}.")

    data_dir = get_default_data_dir()
    tmp_dir = get_default_tmp_dir()
    if data_dir.exists():
        shutil.rmtree(data_dir, ignore_errors=True)
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
    print("        Removed HDFS blocks and temporary directories.")

    print(f"\n  {GRAY}[2/3]{NC} Cleaning downloaded tarballs...")
    for item in DOWNLOADS_DIR.glob("hadoop-*.tar.gz"):
        item.unlink(missing_ok=True)
    print("        Removed tarball cache.")

    print(f"\n  {GRAY}[3/3]{NC} Cleaning environment variables...")
    remove_shell_env()
    print("        Cleaned shell environment variables.")

    print(f"\n  {GREEN}[✓] Uninstall completed.{NC}")
    send_notification("Hadoop Handler", "Hadoop installation deleted.")
