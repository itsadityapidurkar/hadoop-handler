"""System utility module for OS commands, services, and shell configuration."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from hadoop_handler.core.config import (
    BCYAN,
    BRED,
    CYAN,
    DIVIDER,
    GRAY,
    GREEN,
    IS_LINUX,
    IS_MACOS,
    IS_WINDOWS,
    NC,
    RED,
    USER_HOME,
    YELLOW,
)


def send_notification(title: str, message: str) -> None:
    """Send native desktop notification across platforms."""
    try:
        if IS_LINUX and shutil.which("notify-send"):
            subprocess.run(["notify-send", title, message], check=False, stderr=subprocess.DEVNULL)
        elif IS_MACOS and shutil.which("osascript"):
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script], check=False, stderr=subprocess.DEVNULL)
        elif IS_WINDOWS and (shutil.which("powershell") or shutil.which("pwsh")):
            ps = shutil.which("powershell") or shutil.which("pwsh")
            toast_cmd = (
                f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
                f"ContentType = WindowsRuntime] > $null; "
                f"$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                f"$textNodes = $template.GetElementsByTagName('text'); "
                f"$textNodes.Item(0).AppendChild($template.CreateTextNode('{title}')) > $null; "
                f"$textNodes.Item(1).AppendChild($template.CreateTextNode('{message}')) > $null; "
                f"$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Hadoop Handler'); "
                f"$notifier.Show([Windows.UI.Notifications.ToastNotification]::new($template));"
            )
            subprocess.run([ps, "-NoProfile", "-Command", toast_cmd], check=False, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def run_command(
    cmd: list[str],
    check: bool = False,
    capture: bool = True,
    env: Optional[dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Run an external command with appropriate environment."""
    exec_env = os.environ.copy()
    if env:
        exec_env.update(env)

    if capture:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=check,
            env=exec_env,
        )
    return subprocess.run(cmd, check=check, env=exec_env)


def get_active_shell_config() -> Optional[Path]:
    """Get active shell configuration file path."""
    shell_env = os.environ.get("SHELL", "")
    if "zsh" in shell_env:
        return USER_HOME / ".zshrc"
    elif "bash" in shell_env:
        return USER_HOME / ".bashrc"
    if (USER_HOME / ".bashrc").exists():
        return USER_HOME / ".bashrc"
    if (USER_HOME / ".zshrc").exists():
        return USER_HOME / ".zshrc"
    return None


def register_shell_env(vars_dict: dict[str, str], marker: str = "# --- HADOOP HANDLER ENVIRONMENT VARIABLES ---") -> None:
    """Register or update environment variables in shell configuration."""
    conf_file = get_active_shell_config()
    if not conf_file or IS_WINDOWS:
        return

    content = ""
    if conf_file.exists():
        content = conf_file.read_text(encoding="utf-8")

    lines = []
    lines.append(f"\n{marker}")
    for k, v in vars_dict.items():
        lines.append(f'export {k}="{v}"')

    # Add path if binaries are defined
    if "HADOOP_HOME" in vars_dict:
        lines.append('export PATH="$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin"')
    if "SPARK_HOME" in vars_dict:
        lines.append('export PATH="$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin"')
    if "HIVE_HOME" in vars_dict:
        lines.append('export PATH="$PATH:$HIVE_HOME/bin"')
    if "KAFKA_HOME" in vars_dict:
        lines.append('export PATH="$PATH:$KAFKA_HOME/bin"')
    if "TRINO_HOME" in vars_dict:
        lines.append('export PATH="$PATH:$TRINO_HOME/bin"')

    new_block = "\n".join(lines) + "\n"

    if marker in content:
        # Replace existing block
        import re
        pattern = re.compile(rf"{re.escape(marker)}.*?(?=\n\n|\Z)", re.DOTALL)
        content = pattern.sub(new_block.strip(), content)
    else:
        content = content.rstrip() + "\n" + new_block

    conf_file.write_text(content, encoding="utf-8")


def remove_shell_env(marker: str = "# --- HADOOP HANDLER ENVIRONMENT VARIABLES ---") -> None:
    """Remove registered environment variables from shell configuration."""
    for conf_name in [".bashrc", ".zshrc"]:
        conf_file = USER_HOME / conf_name
        if conf_file.exists():
            content = conf_file.read_text(encoding="utf-8")
            if marker in content:
                import re
                pattern = re.compile(rf"{re.escape(marker)}.*?(?=\n\n|\Z)", re.DOTALL)
                cleaned = pattern.sub("", content).strip() + "\n"
                conf_file.write_text(cleaned, encoding="utf-8")


def manage_system_service(action: str = "status") -> int:
    """Manage background service via systemd on Linux or launchd on macOS."""
    if IS_LINUX:
        unit_dir = USER_HOME / ".config/systemd/user"
        unit_file = unit_dir / "hadoop.service"
        hadoop_bin = shutil.which("hadoop-handler") or "hadoop-handler"

        if action == "enable":
            print(f"  [+] Creating systemd user unit: {unit_file}...")
            unit_dir.mkdir(parents=True, exist_ok=True)
            hadoop_home = os.environ.get("HADOOP_HOME", "/opt/hadoop")
            java_home = os.environ.get("JAVA_HOME", "")
            unit_content = f"""[Unit]
Description=Apache Hadoop Single-Node Services (HDFS & YARN)
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
Environment="HADOOP_HOME={hadoop_home}"
Environment="JAVA_HOME={java_home}"
ExecStart={hadoop_bin} start
ExecStop={hadoop_bin} stop

[Install]
WantedBy=default.target
"""
            unit_file.write_text(unit_content, encoding="utf-8")
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
            subprocess.run(["systemctl", "--user", "enable", "hadoop.service"], check=False)
            print(f"  {GREEN}[✓] Hadoop service enabled! Services will automatically start on login.{NC}")
            send_notification("Hadoop Handler", "Systemd user service enabled.")
            return 0
        elif action == "disable":
            print("  [+] Disabling Hadoop systemd user service...")
            subprocess.run(["systemctl", "--user", "stop", "hadoop.service"], check=False, stderr=subprocess.DEVNULL)
            subprocess.run(["systemctl", "--user", "disable", "hadoop.service"], check=False, stderr=subprocess.DEVNULL)
            if unit_file.exists():
                unit_file.unlink()
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
            print(f"  {GREEN}[✓] Hadoop service disabled and unit removed.{NC}")
            send_notification("Hadoop Handler", "Systemd user service disabled.")
            return 0
        elif action == "status":
            subprocess.run(["systemctl", "--user", "status", "hadoop.service", "--no-pager"], check=False)
            return 0
        elif action in ("start", "stop"):
            res = subprocess.run(["systemctl", "--user", action, "hadoop.service"], check=False)
            print(f"  {GREEN}[✓] Signal '{action}' dispatched to systemd.{NC}")
            return res.returncode

    elif IS_MACOS:
        agent_dir = USER_HOME / "Library/LaunchAgents"
        plist_file = agent_dir / "in.adityapidurkar.hadoop.plist"
        hadoop_bin = shutil.which("hadoop-handler") or "hadoop-handler"

        if action == "enable":
            agent_dir.mkdir(parents=True, exist_ok=True)
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>in.adityapidurkar.hadoop</string>
    <key>ProgramArguments</key>
    <array>
        <string>{hadoop_bin}</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
            plist_file.write_text(plist_content, encoding="utf-8")
            subprocess.run(["launchctl", "load", str(plist_file)], check=False)
            print(f"  {GREEN}[✓] LaunchAgent enabled for macOS.{NC}")
            return 0
        elif action == "disable":
            subprocess.run(["launchctl", "unload", str(plist_file)], check=False)
            if plist_file.exists():
                plist_file.unlink()
            print(f"  {GREEN}[✓] LaunchAgent disabled for macOS.{NC}")
            return 0
        elif action == "status":
            subprocess.run(["launchctl", "list", "in.adityapidurkar.hadoop"], check=False)
            return 0

    print(f"  {YELLOW}[*] Service management is not supported for platform: {sys.platform}{NC}")
    return 1


def generate_completion(shell_name: str) -> str:
    """Generate autocompletion script for the requested shell."""
    subcommands = (
        "diagnose install verify status start stop restart upgrade check-compat "
        "java addon delete service update completion --version --help --install-completion"
    )

    if shell_name == "bash":
        return f"""# Hadoop Handler shell completion
_hadoop_handler_completions() {{
    local cur prev opts
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    opts="{subcommands}"

    if [ "$prev" = "service" ]; then
        COMPREPLY=( $(compgen -W "enable disable status start stop" -- "$cur") )
        return 0
    elif [ "$prev" = "java" ]; then
        COMPREPLY=( $(compgen -W "list switch use" -- "$cur") )
        return 0
    elif [ "$prev" = "addon" ]; then
        COMPREPLY=( $(compgen -W "list install status start stop remove" -- "$cur") )
        return 0
    elif [ "$prev" = "completion" ]; then
        COMPREPLY=( $(compgen -W "bash zsh fish powershell" -- "$cur") )
        return 0
    fi

    COMPREPLY=( $(compgen -W "${{opts}}" -- "$cur") )
    return 0
}}
complete -F _hadoop_handler_completions hadoop-handler
"""
    elif shell_name == "zsh":
        return f"""# Hadoop Handler shell completion
autoload -Uz bashcompinit && bashcompinit
_hadoop_handler_completions() {{
    local cur prev opts
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    opts="{subcommands}"

    if [ "$prev" = "service" ]; then
        COMPREPLY=( $(compgen -W "enable disable status start stop" -- "$cur") )
        return 0
    elif [ "$prev" = "java" ]; then
        COMPREPLY=( $(compgen -W "list switch use" -- "$cur") )
        return 0
    elif [ "$prev" = "addon" ]; then
        COMPREPLY=( $(compgen -W "list install status start stop remove" -- "$cur") )
        return 0
    elif [ "$prev" = "completion" ]; then
        COMPREPLY=( $(compgen -W "bash zsh fish powershell" -- "$cur") )
        return 0
    fi

    COMPREPLY=( $(compgen -W "${{opts}}" -- "$cur") )
    return 0
}}
complete -F _hadoop_handler_completions hadoop-handler
"""
    elif shell_name == "fish":
        return f"""complete -c hadoop-handler -f -a "{subcommands}"
complete -c hadoop-handler -n "__fish_seen_subcommand_from service" -f -a "enable disable status start stop"
complete -c hadoop-handler -n "__fish_seen_subcommand_from java" -f -a "list switch use"
complete -c hadoop-handler -n "__fish_seen_subcommand_from addon" -f -a "list install status start stop remove"
complete -c hadoop-handler -n "__fish_seen_subcommand_from completion" -f -a "bash zsh fish powershell"
"""
    elif shell_name == "powershell":
        return """Register-ArgumentCompleter -Native -CommandName hadoop-handler -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    $commands = @('diagnose', 'install', 'verify', 'status', 'start', 'stop', 'restart', 'upgrade', 'check-compat', 'java', 'addon', 'delete', 'service', 'update', 'completion', '--version', '--help')
    $commands | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}
"""
    return ""


def install_shell_completion(target_shell: Optional[str] = None) -> int:
    """Automatically register shell autocompletion."""
    if not target_shell:
        shell_path = os.environ.get("SHELL", "")
        target_shell = Path(shell_path).name if shell_path else ("powershell" if IS_WINDOWS else "bash")

    print(DIVIDER)
    print(f"  {BCYAN}ACTION: Installing Shell Autocompletion ({target_shell}){NC}")
    print(f"{DIVIDER}\n")

    script = generate_completion(target_shell)
    if not script:
        print(f"  {RED}[!] Unsupported shell: {target_shell}{NC}")
        return 1

    if target_shell == "bash":
        rc = USER_HOME / ".bashrc"
        if rc.exists() and "_hadoop_handler_completions" in rc.read_text(encoding="utf-8"):
            print(f"  {YELLOW}[*] Completions already registered in {rc}.{NC}")
        else:
            with open(rc, "a", encoding="utf-8") as f:
                f.write("\n" + script)
            print(f"  {GREEN}[✓] Bash completions added to {rc}!{NC}")
            print(f"      Run: {YELLOW}source {rc}{NC} to activate.")
    elif target_shell == "zsh":
        rc = USER_HOME / ".zshrc"
        if rc.exists() and "_hadoop_handler_completions" in rc.read_text(encoding="utf-8"):
            print(f"  {YELLOW}[*] Completions already registered in {rc}.{NC}")
        else:
            with open(rc, "a", encoding="utf-8") as f:
                f.write("\n" + script)
            print(f"  {GREEN}[✓] Zsh completions added to {rc}!{NC}")
            print(f"      Run: {YELLOW}source {rc}{NC} to activate.")
    elif target_shell == "fish":
        fish_dir = USER_HOME / ".config/fish/completions"
        fish_dir.mkdir(parents=True, exist_ok=True)
        (fish_dir / "hadoop-handler.fish").write_text(script, encoding="utf-8")
        print(f"  {GREEN}[✓] Fish completions saved to {fish_dir}/hadoop-handler.fish!{NC}")
    elif target_shell == "powershell":
        print("  Add the following snippet to your PowerShell $PROFILE:")
        print(script)

    return 0


def diagnose_and_repair() -> int:
    """Diagnose missing dependencies and repair them using native package manager."""
    print(DIVIDER)
    print(f"  {BCYAN}ACTION: System Diagnostics and Auto-Repair{NC}")
    print(f"{DIVIDER}\n")

    checks = [
        ("curl", "Data transfer utility", shutil.which("curl")),
        ("tar", "Archive extraction utility", shutil.which("tar")),
        ("rsync", "File synchronization utility", shutil.which("rsync")),
        ("java", "Java Virtual Machine (JDK)", shutil.which("java")),
        ("ssh", "OpenSSH client", shutil.which("ssh")),
        ("sshd", "OpenSSH daemon / server", shutil.which("sshd") or shutil.which("/usr/sbin/sshd")),
    ]

    missing = []
    print("  Component Check:")
    print("  -----------------------------------------------------------------")
    for name, desc, found in checks:
        if found:
            print(f"  [✓] {name:<10} - {desc:<34} : {GREEN}Found{NC} ({found})")
        else:
            print(f"  [✗] {name:<10} - {desc:<34} : {RED}Missing{NC}")
            missing.append(name)
    print("  -----------------------------------------------------------------")

    if not missing:
        print(f"\n  {GREEN}[✓] All core system utilities are present and verified.{NC}")
        return 0

    print(f"\n  {YELLOW}[!] Missing dependencies detected: {', '.join(missing)}{NC}")
    print("  Attempting automated installation via native package manager...")

    if IS_LINUX:
        if shutil.which("apt-get"):
            pkg_map = {
                "curl": "curl",
                "tar": "tar",
                "rsync": "rsync",
                "java": "openjdk-21-jdk",
                "ssh": "openssh-client",
                "sshd": "openssh-server",
            }
            pkgs = [pkg_map[m] for m in missing if m in pkg_map]
            cmd = ["sudo", "apt-get", "update"]
            subprocess.run(cmd, check=False)
            cmd = ["sudo", "apt-get", "install", "-y"] + pkgs
            res = subprocess.run(cmd, check=False)
            if res.returncode == 0:
                print(f"\n  {GREEN}[✓] Dependencies successfully installed!{NC}")
                return 0
    elif IS_MACOS:
        if shutil.which("brew"):
            for m in missing:
                if m == "java":
                    subprocess.run(["brew", "install", "openjdk@21"], check=False)
                else:
                    subprocess.run(["brew", "install", m], check=False)
            return 0

    print(f"\n  {RED}[!] Please install the missing utilities manually: {', '.join(missing)}{NC}")
    return 1
