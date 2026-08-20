# Managing Hadoop Without the Headache: Introducing Hadoop Handler

Setting up Apache Hadoop locally for the first time is a rite of passage. If you've ever tried to build a Single-Node cluster, you probably spent hours copying XML files, configuring `JAVA_HOME`, fighting with SSH key prompts, and trying to decipher why your NameNode won't start.

Whether you're a student running Big Data assignments, an instructor standardizing a lab environment, or a developer running MapReduce tests, spending hours on infrastructure setup isn't fun.

That's why **Hadoop Handler** was created.

---

## What is Hadoop Handler?

**Hadoop Handler** is an interactive, cross-platform command-line tool suite that fully automates the installation, configuration, verification, and management of an **Apache Hadoop 3.4.2** Single-Node cluster.

It works natively across:
- **Linux** (Ubuntu/Debian, Fedora/RHEL, Arch)
- **macOS**
- **Windows** (via PowerShell)

With a single interactive menu, you can bootstrap a fresh Hadoop environment in under two minutes.

---

## Features

### 1. The Diagnose-and-Repair System
Have you ever run an install script only for it to fail halfway through because you didn't have `wget`, or on Windows because you lacked the Visual C++ Redistributable?

Hadoop Handler solves this with a **"Diagnose/Repair System Dependencies"** feature. 
Running this option scans your system for required utilities (like `tar`, `curl`, `ssh`, or VC++ runtimes). It then prints a clear report of exactly what is missing and what commands it plans to run. 

You remain in total control: it only installs the dependencies when you explicitly hit `y`, and it natively supports `apt`, `dnf`, `yum`, `pacman`, and `brew`.

### 2. Painless Cross-Platform Installation
Hadoop Handler takes the pain out of path resolution. It dynamically detects your OS, finds where your Java 21 is installed, generates passwordless SSH keys (on Unix systems), correctly patches your `.bashrc` or `.zshrc`, and injects the correct configuration files (like `core-site.xml` and `hdfs-site.xml`). 

**Idempotent & Safe**: If your internet drops, running the installer again seamlessly resumes the download. If you run the installer on an existing cluster, the tool detects it and avoids reformatting the NameNode, keeping your HDFS data blocks perfectly safe!

**Automated Firewalling**: Hadoop requires specific ports to function. The installer now detects if you're running `ufw`, `firewalld`, or `Windows Defender Firewall` and offers to seamlessly punch holes for the NameNode, HDFS, and YARN UI.

### 3. Integrated Start, Stop, and Verification
Forget manually navigating to `/sbin` to run startup scripts. The tool features built-in verification checks. A single menu option allows you to:
- Verify that your paths are set properly.
- List active daemons using `jps`.
- Start or stop your HDFS and YARN clusters with zero friction.

### 4. Flawless Uninstallation
Made a mistake or just need to clean up your system? The "Delete Hadoop Completely" option safely shuts down daemons, clears HDFS data directories, and unlinks variables from your system profiles.

---

## How to Get Started

### For Linux & macOS
Just paste this one-liner into your terminal. It will clone the repository, run the global setup script, and launch the control panel.
```bash
curl -fsSL https://adityapidurkar.in/install.sh | sh
```
Later on, simply type `hadoop-handler` in your terminal to bring the menu back up.

### For Windows
Open **PowerShell as Administrator** and paste:
```powershell
irm https://adityapidurkar.in/install.ps1 | iex
```

### Try it out!
Gone are the days of manual Hadoop installations. Whether you're debugging missing DLLs on Windows or configuring `brew` environments on a Mac, **Hadoop Handler** provides a fast, transparent, and resilient solution for your local Big Data infrastructure. 

Check out the [source code on GitHub](https://github.com/itsadityapidurkar/hadoop-handler) and take your Hadoop setup from hours to minutes!
