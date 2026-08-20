# Hadoop Handler

An interactive, cross-platform command-line tool suite designed to automate the installation, configuration, verification, and management of **Apache Hadoop 3.4.2** Single-Node clusters on **Linux**, **macOS**, and **Windows**.

Developed by **Aditya Pidurkar ([@itsadityap](https://github.com/itsadityapidurkar))**.

---

## Repository Structure

- `setup.sh`: Global setup script for Unix systems (Linux & macOS) to register the tool globally.
- `hadoop-handler`: Rebranded interactive CLI control panel for Linux and macOS.
- `install.ps1`: PowerShell auto-installer for Windows (including native DLL and winutils setup).
- `configs/`: A folder containing pre-downloaded configuration files for single-node cluster mapping (`core-site.xml`, `hdfs-site.xml`, `mapred-site.xml`, `yarn-site.xml`, `workers`).

---

## Unix Installation & Usage (Linux & macOS)

### 1. Quick One-Liner Install
Run this command from any terminal:
```bash
curl -fsSL https://adityapidurkar.in/install.sh | sh
```
*(This automatically clones the repository to `~/.hadoop-handler`, sets up execution permissions, and registers the command globally).*

### 2. Manual Clone Install (Alternative)
```bash
git clone https://github.com/itsadityapidurkar/hadoop-handler.git
cd hadoop-handler
chmod +x setup.sh
./setup.sh
```

### 3. Run the Tool
Once installed, you can start the interactive control panel from any directory by typing:
```bash
hadoop-handler
```

### Menu Features
0. **Diagnose/Repair System Dependencies:** Automatically detects missing utilities (tar, curl, Visual C++, etc.) and safely installs them using your native package manager.
1. **Install Hadoop:** Auto-installs Java 21, downloads and extracts Hadoop 3.4.2, generates passwordless SSH keys, configures paths, and formats the NameNode.
2. **Verify Hadoop Installation:** Checks environment variables, checks commands (`hadoop`, `java`), and lists active daemons.
3. **Start Hadoop Services:** Automatically starts HDFS (dfs) and YARN services.
4. **Stop Hadoop Services:** Stops YARN resources and HDFS services.
5. **Delete Hadoop Completely:** Stops services, cleans up all Hadoop binaries, HDFS directories, and environment variables.

---

## Windows Installation & Usage

### 1. Quick One-Liner Install
Open a PowerShell terminal as Administrator and run:
```powershell
irm https://adityapidurkar.in/install.ps1 | iex
```

### 2. Manual Install (Alternative)
Clone this repository, open a PowerShell terminal as Administrator in the repository directory, and run:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\install.ps1
```

### 2. Start & Stop Daemons
On Windows, open a new Command Prompt (CMD) as Administrator and run:
- Start HDFS: `start-dfs.cmd`
- Start YARN: `start-yarn.cmd`
- Stop services: `stop-all.cmd` or close the windows.
