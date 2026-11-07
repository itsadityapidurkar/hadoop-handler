# Hadoop Handler

An interactive, cross-platform command-line tool suite designed to automate the installation, configuration, verification, and management of **Apache Hadoop 3.4.2** Single-Node clusters on **Linux**, **macOS**, and **Windows**.

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

# Direct subcommands
hadoop-handler verify      # Verify Hadoop, Java, and running daemons
hadoop-handler start       # Start HDFS and YARN daemons
hadoop-handler stop        # Stop services
hadoop-handler diagnose    # Check and repair dependencies
hadoop-handler install     # Run automated installation
hadoop-handler delete      # Wipe and uninstall cluster
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

## Menu Features

0. **Diagnose/Repair System Dependencies:** Automatically detects missing utilities (tar, curl, OpenJDK, etc.) and safely installs them using your native package manager.
1. **Install Hadoop:** Auto-installs Java 21, securely downloads and extracts Hadoop 3.4.2 (with resume capabilities), generates passwordless SSH keys, configures firewall ports, formats the NameNode, and configures paths. Installations are fully idempotent (re-running will not wipe your HDFS data blocks).
2. **Verify Hadoop Installation:** Checks environment variables, checks commands (`hadoop`, `java`), and lists active daemons.
3. **Start Hadoop Services:** Automatically starts HDFS (dfs) and YARN services.
4. **Stop Hadoop Services:** Stops YARN resources and HDFS services.
5. **Delete Hadoop Completely:** Stops services, cleans up all Hadoop binaries, HDFS directories, and environment variables.

---

## Windows Daemon Management

On Windows, open a Command Prompt (CMD) as Administrator and run:
- Start HDFS: `start-dfs.cmd`
- Start YARN: `start-yarn.cmd`
- Stop services: `stop-all.cmd` or close the daemon windows.

---

## Repository Structure

- `hadoop_handler/`: The core Python package with cross-platform CLI runner and templates.
  - `cli.py`: Platform-aware launcher for Linux, macOS, and Windows.
  - `scripts/`: Embedded shell scripts (`hadoop-handler`, `install.ps1`).
  - `configs/`: Pre-configured XML templates (`core-site.xml`, `hdfs-site.xml`, `mapred-site.xml`, `yarn-site.xml`, `workers`).
- `pyproject.toml`: Modern PEP 517/621 build configuration for PyPI.
- `setup.sh`: Global setup script for Unix systems.
- `install.sh`: One-liner bootstrap script for Unix systems.
- `install.ps1`: Native PowerShell installer for Windows.
- `configs/`: Fallback cluster templates.

---

## Roadmap / Upcoming Features (TODO)

- [ ] **Self-Updater**: One-command in-place CLI updates (`hadoop-handler self-update`) and PyPI version update notifications.
- [ ] **Desktop Notifications**: Native desktop alerts (Linux `notify-send`, macOS notification center, Windows toast) when large downloads or cluster operations complete.
- [ ] **Multiple Hadoop Version Support**: Side-by-side installations of multiple Hadoop versions (e.g. 3.3.6, 3.4.1, 3.4.2) with instant switching (`hadoop-handler use <version>`).
- [ ] **Cross-Compatibility Checker**: Automated verification of Hadoop $\leftrightarrow$ Java runtime matrix to prevent JVM incompatibilities and JPMS reflection crashes.
- [ ] **In-Place Upgrades & Downgrades**: Upgrade or downgrade Hadoop versions seamlessly while preserving XML configurations and existing HDFS data blocks.

---

## License

Licensed under the [Apache License 2.0](LICENSE).

