"""Core configuration constants and paths for hadoop-handler."""

import os
import platform
import sys
from pathlib import Path

VERSION = "2.0.1"

# ANSI Terminal Colors
RED = "\033[0;31m"
BRED = "\033[1;31m"
GREEN = "\033[0;32m"
BGREEN = "\033[1;32m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
BCYAN = "\033[1;36m"
YELLOW = "\033[1;33m"
GRAY = "\033[90m"
BOLD = "\033[1m"
NC = "\033[0m"

DIVIDER = f"{GRAY}─────────────────────────────────────────────────────────────────{NC}"

# Platform detection
SYSTEM_OS = platform.system()
IS_LINUX = SYSTEM_OS == "Linux"
IS_MACOS = SYSTEM_OS == "Darwin"
IS_WINDOWS = SYSTEM_OS == "Windows"

USER_HOME = Path.home()
PACKAGE_DIR = Path(__file__).resolve().parent.parent
CONFIGS_DIR = PACKAGE_DIR / "configs"
CACHE_DIR = USER_HOME / ".hadoop-handler"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR = USER_HOME / "Downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


def get_default_hadoop_home() -> Path:
    env_home = os.environ.get("HADOOP_HOME")
    if env_home and Path(env_home).exists():
        return Path(env_home)

    if IS_LINUX:
        if Path("/opt/hadoop").exists() or os.access("/opt", os.W_OK) or os.geteuid() == 0:
            return Path("/opt/hadoop")
        return USER_HOME / "hadoop"
    elif IS_MACOS:
        if Path("/Users/Shared/hadoop").exists() or Path("/Users/Shared").exists():
            return Path("/Users/Shared/hadoop")
        return USER_HOME / "hadoop"
    elif IS_WINDOWS:
        if Path("C:/hadoop").exists():
            return Path("C:/hadoop")
        return USER_HOME / "hadoop"
    return USER_HOME / "hadoop"


def get_default_data_dir() -> Path:
    if IS_LINUX:
        if Path("/opt/hadoop_data").exists() or os.access("/opt", os.W_OK) or os.geteuid() == 0:
            return Path("/opt/hadoop_data")
        return USER_HOME / "hadoop_data"
    elif IS_MACOS:
        if Path("/Users/Shared/hadoop_data").exists() or Path("/Users/Shared").exists():
            return Path("/Users/Shared/hadoop_data")
        return USER_HOME / "hadoopdata"
    elif IS_WINDOWS:
        return Path("C:/hadoop_data") if Path("C:/").exists() else USER_HOME / "hadoop_data"
    return USER_HOME / "hadoop_data"


def get_default_tmp_dir() -> Path:
    if IS_LINUX:
        if Path("/opt/hadoop_tmp").exists() or os.access("/opt", os.W_OK) or os.geteuid() == 0:
            return Path("/opt/hadoop_tmp")
        return USER_HOME / "hadoop_tmp"
    elif IS_MACOS:
        if Path("/Users/Shared/hadoop_tmp").exists() or Path("/Users/Shared").exists():
            return Path("/Users/Shared/hadoop_tmp")
        return USER_HOME / "hadooptmp"
    elif IS_WINDOWS:
        return Path("C:/hadoop_tmp") if Path("C:/").exists() else USER_HOME / "hadoop_tmp"
    return USER_HOME / "hadoop_tmp"


def get_default_addon_root() -> Path:
    if IS_LINUX:
        if Path("/opt").exists() and (os.access("/opt", os.W_OK) or os.geteuid() == 0):
            return Path("/opt")
        return USER_HOME / "addons"
    elif IS_MACOS:
        if Path("/Users/Shared").exists():
            return Path("/Users/Shared/addons")
        return USER_HOME / "addons"
    elif IS_WINDOWS:
        return Path("C:/addons") if Path("C:/").exists() else USER_HOME / "addons"
    return USER_HOME / "addons"
