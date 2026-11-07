# Hadoop Handler

An interactive, pure Python cross-platform control center and ecosystem addon manager for **Apache Hadoop**, **Apache Spark**, **Apache Hive**, **Apache Kafka**, and **Trino (PrestoSQL)** on **Linux**, **macOS**, and **Windows**.

Developed by **Aditya Pidurkar ([@itsadityap](https://github.com/itsadityapidurkar))**.

---

## Installation & Usage

### Method 1: Install via Pip / PyPI (Recommended)

Install the global CLI directly using Python and `pip`:

```bash
pip install hadoop-handler
```

Launch the interactive control panel from anywhere:
```bash
hadoop-handler
```

You can also run subcommands and flags directly:
```bash
# Check version and help
hadoop-handler --version
hadoop-handler --help

# Hadoop Cluster Commands
hadoop-handler verify                 # Verify Hadoop, Java, and running daemons
hadoop-handler install                # Install Apache Hadoop (defaults to 3.4.2)
hadoop-handler install --version 3.3.6 # Install specific Hadoop version
hadoop-handler upgrade 3.4.2          # In-place upgrade/downgrade preserving HDFS blocks
hadoop-handler check-compat           # Validate Hadoop <-> Java matrix compatibility
hadoop-handler java list              # List all installed Java JDKs
hadoop-handler java switch            # Interactively choose active Java runtime
hadoop-handler java use 21            # Switch active Java runtime for Hadoop
hadoop-handler start                  # Start HDFS and YARN daemons
hadoop-handler stop                   # Stop services
hadoop-handler restart                # Restart cluster daemons
hadoop-handler diagnose               # Check and repair dependencies
hadoop-handler delete                 # Wipe and uninstall cluster

# Ecosystem Addon Commands (Spark, Hive, Kafka, Trino)
hadoop-handler addon list             # List installed and available ecosystem addons
hadoop-handler addon install spark    # Install Apache Spark with HDFS & YARN integration
hadoop-handler addon install hive     # Install Apache Hive data warehouse with Derby metastore
hadoop-handler addon install kafka    # Install Apache Kafka in lightweight KRaft mode
hadoop-handler addon install trino    # Install Trino SQL query engine with Hive connector
hadoop-handler addon status spark     # Check status and open ports for addon
hadoop-handler addon start spark      # Start addon services
hadoop-handler addon stop spark       # Stop addon services
hadoop-handler addon remove spark     # Remove addon and clean environment

# System & Shell Integration
hadoop-handler service enable         # Register cluster as systemd user service
hadoop-handler service status         # Check systemd service status
hadoop-handler update                 # In-place self update via git or pip
hadoop-handler --install-completion   # Install shell autocompletion (bash, zsh, fish, powershell)
```

---

### Method 2: Unix One-Liner (Linux & macOS)

Run this command from any terminal:
```bash
curl -fsSL https://adityapidurkar.in/install.sh | sh
```
*(This clones the repository to `~/.hadoop-handler`, sets up execution permissions, and registers the command globally).*

---

### Method 3: Windows PowerShell One-Liner

Open a PowerShell terminal as Administrator and run:
```powershell
irm https://adityapidurkar.in/install.ps1 | iex
```

---

### Method 4: Manual Clone (Linux & macOS)

```bash
git clone https://github.com/itsadityapidurkar/hadoop-handler.git
cd hadoop-handler
chmod +x setup.sh
./setup.sh
```

---

## Features & Menu Overview

* **Pure Python Native Core:** Built completely on the Python 3 standard library with zero third-party pip dependencies. Eliminates shell script divergence across Linux, macOS, and Windows.
* **Ecosystem Addon Manager:** Automated installation, configuration, daemon supervision, and HDFS/YARN integration for major big data frameworks:
  * **Apache Spark:** Fast in-memory analytics engine with native HDFS classpath and YARN execution.
  * **Apache Hive:** Distributed data warehouse with Derby/HDFS metastore and automatic Guava conflict resolution.
  * **Apache Kafka:** Distributed streaming platform initialized in modern, lightweight KRaft mode (no ZooKeeper needed).
  * **Trino (PrestoSQL):** Interactive distributed SQL engine with built-in Hive connector querying HDFS datasets.
* **Arrow-Key Navigation (TUI Menu):** Navigate menu items effortlessly with `Up` / `Down` arrow keys, Vim keys (`j` / `k`), direct numbers (`0-14`), or `Enter` to select. Zero-flicker in-place terminal redraw.
* **Live Visual Status Badges:** Instant status display at the top of the menu:
  * Hadoop: `[Installed (3.4.2)]` or `[Not Installed]`
  * Java: `[OpenJDK 21]` or `[Missing]`
  * Services: `[5/5 Daemons Running]` or `[Stopped]`
* **Dynamic Hadoop Version Selector:** Choose from modern versions (3.4.2, 3.4.1, 3.3.6, 3.3.5, 3.2.4) or provide a custom version during installation with automatic pre-flight compatibility checks.
* **Java Runtime Detection & Switcher:** Detects all installed JDKs across standard system directories (`/usr/lib/jvm/`, macOS JVM paths, Windows paths) and enables instant active JVM switching for Hadoop (`hadoop-handler java list`, `hadoop-handler java switch`, `hadoop-handler java use <ver>`).
* **Cross-Compatibility Matrix Checker:** Comprehensive matrix checker preventing common JVM reflection and security manager crashes across Hadoop 3.4+, 3.3.x, 3.2.x, and 2.x on Java 8, 11, 17, and 21 (`hadoop-handler check-compat`).
* **In-Place Upgrades & Downgrades:** Upgrade or downgrade Hadoop versions in-place (`hadoop-handler upgrade [version]`) while preserving existing XML configurations and protecting HDFS data blocks from reformatting.
* **Smooth Download Progress Bar:** Live, single-line progress indicator with byte counter, download rate (MB/s), and ETA calculation.
* **Desktop Notifications:** Native desktop alerts via `notify-send` (Linux), Notification Center (macOS), or Toast (Windows) when downloads and cluster tasks complete.
* **System Service Integration (systemd / launchd):** Manage Hadoop daemons via `systemctl --user` on Linux or `launchd` on macOS so services can run automatically on boot.
* **Shell Autocompletion:** Native autocompletion support for `bash`, `zsh`, `fish`, and `powershell`.
* **One-Command Self-Update:** Run `hadoop-handler update` to automatically pull updates from PyPI or git repositories.
* **Version Update Banner:** Non-intrusive cached checks alerting you when a newer version is available.
* **Diagnose / Auto-Repair:** Scans for missing utilities (`curl`, `tar`, `rsync`, OpenJDK, `sshd`) and safely installs them using your native package manager (`apt`, `dnf`, `yum`, `pacman`, `brew`).
* **Idempotent Installation:** Secure downloads, SSH keypair generation, firewall port configuration, and safe NameNode formatting without wiping existing HDFS data blocks.

---

## Windows Daemon Management

On Windows, open a Command Prompt (CMD) or PowerShell and run:
- Start HDFS: `hadoop-handler start`
- Stop services: `hadoop-handler stop`
- Check status: `hadoop-handler verify`

---

## Repository Structure

- `hadoop_handler/`: The core Python package.
  - `cli.py`: Platform-agnostic CLI dispatcher and entry point.
  - `core/`: Core cluster engine and system utilities.
    - `config.py`: Cluster paths, platform constants, and default directories.
    - `system.py`: OS operations, service unit generators, notifications, completions.
    - `downloader.py`: Streaming downloader with live progress bar and mirror fallback.
    - `java.py`: Multi-JDK detection, switcher, and compatibility matrix.
    - `cluster.py`: Hadoop installation, in-place upgrade, daemons, and diagnostics.
    - `tui.py`: Zero-flicker arrow-key menu selector and live badges.
  - `addons/`: Big data ecosystem addon suite.
    - `base.py`: Base class defining addon lifecycle.
    - `manager.py`: Registry and interactive management submenu.
    - `spark.py`: Apache Spark integration with HDFS/YARN.
    - `hive.py`: Apache Hive data warehouse and Derby metastore.
    - `kafka.py`: Apache Kafka in KRaft mode.
    - `trino.py`: Trino (PrestoSQL) distributed query engine.
  - `configs/`: Pre-configured XML templates (`core-site.xml`, `hdfs-site.xml`, `mapred-site.xml`, `yarn-site.xml`, `workers`).
- `pyproject.toml`: Modern PEP 517/621 build configuration for PyPI.
- `setup.sh`: Global setup script for Unix systems.
- `install.sh`: One-liner bootstrap script for Unix systems.
- `install.ps1`: Native PowerShell launcher for Windows.

---

## Roadmap / Completed Features

- [x] **Pure Python Native Core**: Unified standard-library engine deprecating shell script divergence across Linux, macOS, and Windows.
- [x] **Ecosystem Addon Manager**: Full lifecycle management (install, start, stop, status, remove) for Apache Spark, Apache Hive, Apache Kafka, and Trino (PrestoSQL).
- [x] **Arrow-Key Navigation (TUI Menu)**: Interactive navigation with live cluster status badges.
- [x] **Smooth Download Progress Bar**: Single-line progress bar with transfer rate and ETA.
- [x] **Desktop Notifications**: Native desktop alerts for task completion.
- [x] **System Service Integration**: Manage cluster via systemd user units on Linux or launchd on macOS.
- [x] **Shell Autocompletion**: Subcommand autocompletion for Bash, Zsh, Fish, and PowerShell.
- [x] **One-Command Self-Update**: In-place CLI updates (`hadoop-handler update`) and update check banner.
- [x] **Dynamic Hadoop Version Selector**: Dynamic version picking (3.4.2, 3.4.1, 3.3.6, etc.) with pre-flight verification.
- [x] **Java Runtime Detection & Switcher**: Multi-JDK detection and dynamic switching for Hadoop (`hadoop-env.sh`).
- [x] **Cross-Compatibility Matrix Checker**: Automated verification of Hadoop and Java runtime matrix to prevent JVM reflection crashes.
- [x] **In-Place Upgrades & Downgrades**: Upgrade or downgrade Hadoop versions seamlessly while preserving XML configurations and existing HDFS data blocks.

---

## License

Licensed under the [Apache License 2.0](LICENSE).
