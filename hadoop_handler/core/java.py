"""Java runtime detection, multi-JDK switching, and Hadoop compatibility matrix."""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from hadoop_handler.core.config import (
    BCYAN,
    CYAN,
    DIVIDER,
    GRAY,
    GREEN,
    IS_LINUX,
    IS_MACOS,
    IS_WINDOWS,
    NC,
    RED,
    YELLOW,
)
from hadoop_handler.core.system import (
    get_active_shell_config,
    register_shell_env,
    send_notification,
)


@dataclass
class JVMRecord:
    major: int
    version_str: str
    path: Path
    is_active: bool = False


def detect_installed_javas() -> list[JVMRecord]:
    """Scan host filesystem for all valid JDK installations."""
    seen_canonical = set()
    records: list[JVMRecord] = []

    active_java_home = os.environ.get("JAVA_HOME")
    active_path: Optional[Path] = None
    if active_java_home:
        try:
            active_path = Path(active_java_home).resolve()
        except Exception:
            pass

    def check_and_add(jvm_dir: Path) -> None:
        if not jvm_dir.exists():
            return
        java_exe = jvm_dir / "bin" / ("java.exe" if IS_WINDOWS else "java")
        if not java_exe.is_file() or not os.access(java_exe, os.X_OK):
            return

        try:
            canonical = jvm_dir.resolve()
        except Exception:
            return

        if canonical in seen_canonical:
            return
        seen_canonical.add(canonical)

        # Query version
        try:
            res = subprocess.run(
                [str(java_exe), "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5.0,
            )
            v_output = res.stderr or res.stdout
            first_line = v_output.splitlines()[0] if v_output else ""
            match = re.search(r'version "([^"]+)"', first_line)
            v_str = match.group(1) if match else "unknown"

            major = 0
            if v_str.startswith("1."):
                major = int(v_str.split(".")[1])
            else:
                major_part = v_str.split(".")[0]
                major = int(major_part) if major_part.isdigit() else 0

            is_active = False
            if active_path and canonical == active_path:
                is_active = True

            records.append(JVMRecord(major=major, version_str=v_str, path=canonical, is_active=is_active))
        except Exception:
            pass

    # 1. Current JAVA_HOME
    if active_path:
        check_and_add(active_path)

    # 2. PATH java binary
    which_java = shutil.which("java")
    if which_java:
        try:
            real_java = Path(which_java).resolve()
            # real_java is in <JVM_HOME>/bin/java
            check_and_add(real_java.parent.parent)
        except Exception:
            pass

    # 3. Standard Linux directories
    if IS_LINUX and Path("/usr/lib/jvm").exists():
        for d in Path("/usr/lib/jvm").iterdir():
            if d.is_dir():
                check_and_add(d)

    # 4. Standard macOS directories
    if IS_MACOS:
        jvm_root = Path("/Library/Java/JavaVirtualMachines")
        if jvm_root.exists():
            for d in jvm_root.iterdir():
                home = d / "Contents/Home"
                if home.exists():
                    check_and_add(home)

        # Query macOS java_home utility
        if shutil.which("/usr/libexec/java_home"):
            try:
                res = subprocess.run(["/usr/libexec/java_home", "-X"], capture_output=True, text=True)
                for line in res.stdout.splitlines():
                    if "<string>" in line and "</string>" in line:
                        p = line.replace("<string>", "").replace("</string>", "").strip()
                        check_and_add(Path(p))
            except Exception:
                pass

    # 5. Standard Windows directories
    if IS_WINDOWS:
        for root in ["C:/Program Files/Java", "C:/Program Files/Eclipse Adoptium", "C:/Program Files/Amazon Corretto"]:
            p = Path(root)
            if p.exists():
                for d in p.iterdir():
                    if d.is_dir():
                        check_and_add(d)

    # If no active marker set yet, mark first record or fallback
    if records and not any(r.is_active for r in records):
        records[0].is_active = True

    return sorted(records, key=lambda x: (x.major, x.version_str), reverse=True)


def list_javas() -> None:
    """Print formatted list of detected Java runtimes."""
    jvms = detect_installed_javas()
    print(DIVIDER)
    print(f"  {BCYAN}ACTION: Detected Java Runtimes (JVMs){NC}")
    print(f"{DIVIDER}\n")
    print(f"  {'INDEX':<7} {'VERSION':<14} {'PATH':<45} {'ACTIVE'}")
    print("  -----------------------------------------------------------------")
    for idx, jvm in enumerate(jvms, 1):
        active_badge = f"{GREEN}[ACTIVE]{NC}" if jvm.is_active else ""
        print(f"  [{idx:2d}]    Java {jvm.major:<9} {str(jvm.path):<45} {active_badge}")
    print(DIVIDER)


def switch_java(target: Optional[str] = None) -> bool:
    """Interactively or programmatically switch active Java runtime for Hadoop."""
    jvms = detect_installed_javas()
    if not jvms:
        print(f"  {RED}[!] No Java runtimes found on this machine.{NC}")
        return False

    chosen: Optional[JVMRecord] = None

    if target:
        # Check by 1-based index
        if target.isdigit():
            val = int(target)
            if 1 <= val <= len(jvms):
                chosen = jvms[val - 1]
            else:
                # Or check by major version number (e.g., 21, 11, 8)
                for j in jvms:
                    if j.major == val:
                        chosen = j
                        break
        else:
            # Check by path match
            for j in jvms:
                if str(j.path) == target or target in str(j.path):
                    chosen = j
                    break

    if not chosen:
        print(DIVIDER)
        print(f"  {BCYAN}ACTION: Switch Java Runtime for Hadoop{NC}")
        print(f"{DIVIDER}\n")
        print("  Available Java Runtimes on this system:")
        for idx, jvm in enumerate(jvms, 1):
            mark = f"{GREEN}[ACTIVE]{NC}" if jvm.is_active else ""
            print(f"    [ {idx} ] Java {jvm.major:<2} ({jvm.path}) {mark}")
        print("    [ 0 ] Cancel")
        print(DIVIDER)

        try:
            pick = input(f"  Select Java runtime to use [1-{len(jvms)}]: ").strip()
            if pick.isdigit():
                val = int(pick)
                if 1 <= val <= len(jvms):
                    chosen = jvms[val - 1]
        except (KeyboardInterrupt, EOFError):
            print("\n  Operation cancelled.")
            return False

    if not chosen:
        print("  Operation cancelled.")
        return False

    chosen_path = str(chosen.path)
    os.environ["JAVA_HOME"] = chosen_path
    print(f"  [+] Setting JAVA_HOME={GREEN}{chosen_path}{NC}")

    # Update hadoop-env.sh if Hadoop is installed
    hadoop_home = os.environ.get("HADOOP_HOME")
    if hadoop_home:
        env_sh = Path(hadoop_home) / "etc/hadoop/hadoop-env.sh"
        if env_sh.exists():
            content = env_sh.read_text(encoding="utf-8")
            if "export JAVA_HOME=" in content:
                content = re.sub(r"^#?\s*export JAVA_HOME=.*$", f"export JAVA_HOME={chosen_path}", content, flags=re.MULTILINE)
            else:
                content += f"\nexport JAVA_HOME={chosen_path}\n"
            env_sh.write_text(content, encoding="utf-8")
            print(f"  [+] Updated {env_sh}")

    # Update active shell profile
    shell_conf = get_active_shell_config()
    if shell_conf and shell_conf.exists():
        content = shell_conf.read_text(encoding="utf-8")
        if "export JAVA_HOME=" in content:
            content = re.sub(r'export JAVA_HOME="?[^"\n]+"?', f'export JAVA_HOME="{chosen_path}"', content)
            shell_conf.write_text(content, encoding="utf-8")
            print(f"  [+] Updated {shell_conf}")
        else:
            register_shell_env({"JAVA_HOME": chosen_path})

    print(f"\n  {GREEN}[✓] Active Java runtime switched successfully to Java {chosen.major}!{NC}")
    send_notification("Hadoop Handler", f"Switched Hadoop Java runtime to Java {chosen.major}.")
    return True


def check_compatibility(
    hadoop_version: Optional[str] = None,
    java_version: Optional[str] = None,
) -> tuple[bool, str, str]:
    """Check Hadoop and Java matrix compatibility and return (compatible, reason, recommendation)."""
    h_ver = hadoop_version
    if not h_ver:
        which_hadoop = shutil.which("hadoop")
        if which_hadoop:
            try:
                res = subprocess.run([which_hadoop, "version"], capture_output=True, text=True)
                first = res.stdout.splitlines()[0]
                h_ver = first.split()[1]
            except Exception:
                h_ver = "3.4.2"
        else:
            h_ver = "3.4.2"

    j_ver = java_version
    if not j_ver:
        active_jh = os.environ.get("JAVA_HOME")
        java_cmd = str(Path(active_jh) / "bin/java") if active_jh else (shutil.which("java") or "")
        if java_cmd:
            try:
                res = subprocess.run([java_cmd, "-version"], capture_output=True, text=True)
                v_out = res.stderr or res.stdout
                first = v_out.splitlines()[0]
                match = re.search(r'version "([^"]+)"', first)
                if match:
                    val = match.group(1)
                    j_ver = val.split(".")[1] if val.startswith("1.") else val.split(".")[0]
            except Exception:
                j_ver = "unknown"
        else:
            j_ver = "unknown"

    try:
        h_major = int(h_ver.split(".")[0])
        h_minor = int(h_ver.split(".")[1])
    except Exception:
        h_major, h_minor = 3, 4

    try:
        j_major = int(j_ver)
    except Exception:
        j_major = 21

    print(f"  Checking compatibility: Hadoop {CYAN}{h_ver}{NC} <-> Java {CYAN}{j_ver}{NC}...")

    compatible = False
    reason = ""
    recommended = ""

    if h_major >= 3 and h_minor >= 4:
        if j_major in (8, 11, 17, 21):
            compatible = True
        elif j_major > 21:
            compatible = False
            reason = f"Java {j_major} is newer than officially validated LTS runtimes."
            recommended = "Java 11, 17, or 21"
        else:
            compatible = False
            reason = "Hadoop 3.4+ requires at least Java 8."
            recommended = "Java 11, 17, or 21"
    elif h_major == 3 and h_minor == 3:
        if j_major in (8, 11, 17):
            compatible = True
        else:
            compatible = False
            reason = f"Hadoop 3.3.x does not support Java {j_major} (fails on Java 21+)."
            recommended = "Java 8, 11, or 17"
    elif h_major == 3 and h_minor <= 2:
        if j_major in (8, 11):
            compatible = True
        else:
            compatible = False
            reason = "Hadoop 3.0-3.2 fails on Java 17+ due to JVM module encapsulation (JEP 396/403)."
            recommended = "Java 8 or Java 11"
    elif h_major == 2:
        if j_major in (7, 8):
            compatible = True
        else:
            compatible = False
            reason = "Hadoop 2.x only supports Java 7 or Java 8."
            recommended = "Java 8"

    if compatible:
        print(f"  {GREEN}[✓] Compatible: Hadoop {h_ver} is officially verified on Java {j_ver}.{NC}")
    else:
        print(f"  {RED}[!] Incompatibility Detected: {reason}{NC}")
        print(f"      {YELLOW}Recommended runtime for Hadoop {h_ver}: {recommended}.{NC}")
        print(f"      {GRAY}Tip: Use 'hadoop-handler java switch' to select a compatible JVM.{NC}")

    return compatible, reason, recommended
