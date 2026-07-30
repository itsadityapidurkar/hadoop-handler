# ==============================================================================
#  Hadoop Handler — Single-Node Cluster Control Panel (Windows)
#  Developer: Aditya Pidurkar (github.com/itsadityapidurkar)
# ==============================================================================

# 1. Administrator Check
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "This script must be run as Administrator. Please reopen PowerShell as Administrator."
    Exit
}

# Set Locations
$HadoopDest = "C:\hadoop"
$JavaDest = "C:\java\jdk-21"
$CacheDir = "C:\hadoop_cache"
$Divider = "─────────────────────────────────────────────────────────────────"

function load_env {
    # Check environment variables
    if (-not $env:JAVA_HOME) {
        $env:JAVA_HOME = [Environment]::GetEnvironmentVariable("JAVA_HOME", "Machine")
    }
    if (-not $env:HADOOP_HOME) {
        $env:HADOOP_HOME = [Environment]::GetEnvironmentVariable("HADOOP_HOME", "Machine")
    }
    # Ensure active process Path inherits the machine variables immediately
    if ($env:Path -notlike "*C:\hadoop\bin*") {
        $env:Path = "$env:Path;C:\hadoop\bin;C:\java\jdk-21\bin"
    }
}

function pause_screen {
    Write-Host "`n$Divider" -ForegroundColor DarkGray
    Read-Host "  Press [Enter] to return to the main menu..."
}

# Option 1: Install Hadoop
function Install-Hadoop {
    Clear-Host
    Write-Host $Divider -ForegroundColor DarkGray
    Write-Host "  ACTION: Installing Apache Hadoop 3.4.2" -ForegroundColor Cyan
    Write-Host $Divider -ForegroundColor DarkGray
    Write-Host ""

    # Release any active file locks from running daemons or previous failed runs
    Get-Process -Name java -ErrorAction SilentlyContinue | Stop-Process -Force

    # Create directories
    Write-Host "  [1/8] Creating required system directories..." -ForegroundColor DarkGray
    New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
    New-Item -ItemType Directory -Force -Path "C:\java" | Out-Null
    New-Item -ItemType Directory -Force -Path "$HadoopDest\data\namenode" | Out-Null
    New-Item -ItemType Directory -Force -Path "$HadoopDest\data\datanode" | Out-Null
    New-Item -ItemType Directory -Force -Path "$HadoopDest\temp" | Out-Null

    # Download Java
    $JavaZip = "$CacheDir\openjdk-21.zip"
    $JavaUrl = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jdk_x64_windows_hotspot_21.0.2_13.zip"
    $UserDownloadsJava = "C:\Users\$env:USERNAME\Downloads\OpenJDK21U-jdk_x64_windows_hotspot_21.0.2_13.zip"

    Write-Host "`n  [2/8] Fetching OpenJDK 21..." -ForegroundColor DarkGray
    if (-not (Test-Path "$JavaDest\bin\java.exe")) {
        if (-not (Test-Path $JavaZip)) {
            if (Test-Path $UserDownloadsJava) {
                Write-Host "        Found Java zip in your Downloads folder. Copying to cache..." -ForegroundColor Green
                Copy-Item -Path $UserDownloadsJava -Destination $JavaZip -Force
            } else {
                Write-Host "        Downloading OpenJDK 21..." -ForegroundColor Green
                Invoke-WebRequest -Uri $JavaUrl -OutFile $JavaZip
            }
        } else {
            Write-Host "        Using cached OpenJDK 21 zip..." -ForegroundColor Green
        }
        if (Test-Path $JavaDest) { cmd.exe /c "rmdir /s /q `"$JavaDest`"" }
        Write-Host "        Extracting OpenJDK 21 to C:\java..."
        Expand-Archive -Path $JavaZip -DestinationPath "C:\java"
        $extractedDir = Get-ChildItem "C:\java" | Where-Object { $_.Name -like "*jdk-21*" -and $_.PSIsContainer }
        if ($extractedDir) {
            Rename-Item -Path $extractedDir.FullName -NewName "jdk-21"
        }
    } else {
        Write-Host "        Java 21 already installed at $JavaDest." -ForegroundColor Green
    }

    # Download Hadoop
    $HadoopTar = "$CacheDir\hadoop-3.4.2.tar.gz"
    $HadoopUrl = "https://archive.apache.org/dist/hadoop/common/hadoop-3.4.2/hadoop-3.4.2.tar.gz"
    $UserDownloadsHadoop = "C:\Users\$env:USERNAME\Downloads\hadoop-3.4.2.tar.gz"

    Write-Host "`n  [3/8] Fetching Apache Hadoop 3.4.2..." -ForegroundColor DarkGray
    # Always perform a clean install if HADOOP_HOME/etc/hadoop configuration files are missing or incomplete
    if (-not (Test-Path "$HadoopDest\etc\hadoop\core-site.xml")) {
        if (-not (Test-Path $HadoopTar)) {
            if (Test-Path $UserDownloadsHadoop) {
                Write-Host "        Found Hadoop tarball in your Downloads folder. Copying to cache..." -ForegroundColor Green
                Copy-Item -Path $UserDownloadsHadoop -Destination $HadoopTar -Force
            } else {
                Write-Host "        Downloading Apache Hadoop 3.4.2..." -ForegroundColor Green
                Invoke-WebRequest -Uri $HadoopUrl -OutFile $HadoopTar
            }
        } else {
            Write-Host "        Using cached Hadoop tarball..." -ForegroundColor Green
        }
        Write-Host "        Performing a clean extraction to C:\..." -ForegroundColor Green
        if (Test-Path $HadoopDest) { cmd.exe /c "rmdir /s /q `"$HadoopDest`"" }
        if (Test-Path "C:\hadoop-3.4.2") { cmd.exe /c "rmdir /s /q C:\hadoop-3.4.2" }
        tar -xf $HadoopTar -C "C:\"
        Rename-Item -Path "C:\hadoop-3.4.2" -NewName "hadoop"
    } else {
        Write-Host "        Hadoop already installed at $HadoopDest." -ForegroundColor Green
    }

    # Native Windows Binaries
    Write-Host "`n  [4/8] Integrating native Windows binaries (winutils & hadoop.dll)..." -ForegroundColor DarkGray
    $WinutilsUrl = "https://github.com/cdarlint/winutils/raw/master/hadoop-3.3.6/bin/winutils.exe"
    $HadoopDllUrl = "https://github.com/cdarlint/winutils/raw/master/hadoop-3.3.6/bin/hadoop.dll"
    Invoke-WebRequest -Uri $WinutilsUrl -OutFile "$HadoopDest\bin\winutils.exe"
    Invoke-WebRequest -Uri $HadoopDllUrl -OutFile "$HadoopDest\bin\hadoop.dll"
    Copy-Item -Path "$HadoopDest\bin\hadoop.dll" -Destination "C:\Windows\System32" -Force
    Write-Host "        Native binaries configured." -ForegroundColor Green

    # Environment Variables
    Write-Host "`n  [5/8] Configuring System Environment Variables..." -ForegroundColor DarkGray
    [Environment]::SetEnvironmentVariable("JAVA_HOME", $JavaDest, "Machine")
    [Environment]::SetEnvironmentVariable("HADOOP_HOME", $HadoopDest, "Machine")
    $env:JAVA_HOME = $JavaDest
    $env:HADOOP_HOME = $HadoopDest

    $SystemPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($SystemPath -notlike "*%HADOOP_HOME%\bin*") {
        $NewPath = "$SystemPath;%HADOOP_HOME%\bin;%JAVA_HOME%\bin"
        [Environment]::SetEnvironmentVariable("Path", $NewPath, "Machine")
        Write-Host "        Added HADOOP_HOME\bin and JAVA_HOME\bin to PATH." -ForegroundColor Green
    }

    # Configuration Files
    Write-Host "`n  [6/8] Building cluster configuration XML files..." -ForegroundColor DarkGray
    $ConfDir = "$HadoopDest\etc\hadoop"
    $CoreSite = @"
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://127.0.0.1:9000</value>
    </property>
    <property>
        <name>hadoop.tmp.dir</name>
        <value>C:/hadoop/temp</value>
    </property>
</configuration>
"@
    Set-Content -Path "$ConfDir\core-site.xml" -Value $CoreSite

    $HdfsSite = @"
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>C:/hadoop/data/namenode</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>C:/hadoop/data/datanode</value>
    </property>
</configuration>
"@
    Set-Content -Path "$ConfDir\hdfs-site.xml" -Value $HdfsSite

    $MapredSite = @"
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>mapreduce.framework.name</name>
        <value>yarn</value>
    </property>
</configuration>
"@
    Set-Content -Path "$ConfDir\mapred-site.xml" -Value $MapredSite

    $YarnSite = @"
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>yarn.nodemanager.aux-services</name>
        <value>mapreduce_shuffle</value>
    </property>
</configuration>
"@
    Set-Content -Path "$ConfDir\yarn-site.xml" -Value $YarnSite

    # configure hadoop-env.cmd
    Write-Host "`n  [7/8] Updating hadoop-env.cmd profile..." -ForegroundColor DarkGray
    $HadoopEnvCmd = "$ConfDir\hadoop-env.cmd"
    $Content = Get-Content $HadoopEnvCmd
    $Content = $Content -replace 'set JAVA_HOME=.*', "set JAVA_HOME=$JavaDest"
    Set-Content -Path $HadoopEnvCmd -Value $Content

    # Format NameNode
    Write-Host "`n  [8/8] Formatting HDFS NameNode system..." -ForegroundColor DarkGray
    cmd.exe /c "$HadoopDest\bin\hdfs.cmd namenode -format -force"

    Write-Host "`n  [✓] Installation completed successfully!" -ForegroundColor Green
    Write-Host "      Please open a NEW terminal session to load path variables."
}

# Option 2: Verify
function Verify-Hadoop {
    Clear-Host
    load_env
    Write-Host $Divider -ForegroundColor DarkGray
    Write-Host "  ACTION: Verifying Hadoop System Status" -ForegroundColor Cyan
    Write-Host $Divider -ForegroundColor DarkGray
    Write-Host ""

    if (-not (Test-Path $HadoopDest)) {
        Write-Host "  [!] Error: Hadoop is not installed." -ForegroundColor Red
        return
    }
    Write-Host "  HADOOP_HOME: $HadoopDest" -ForegroundColor Green

    # Check commands
    Write-Host "`n  Checking binaries in Path..." -ForegroundColor DarkGray
    $javaPath = where.exe java 2>$null
    $hadoopPath = where.exe hadoop 2>$null

    if ($javaPath) { Write-Host "  Java binary:   Available ($($javaPath | Select-Object -First 1))" -ForegroundColor Green }
    else { Write-Host "  Java binary:   Not found in PATH" -ForegroundColor Red }

    if ($hadoopPath) { Write-Host "  Hadoop binary: Available ($($hadoopPath | Select-Object -First 1))" -ForegroundColor Green }
    else { Write-Host "  Hadoop binary: Not found in PATH (Requires new console session)" -ForegroundColor Red }

    # Check processes
    Write-Host "`n  Active Cluster Daemons (jps):" -ForegroundColor DarkGray
    Write-Host "  $Divider" -ForegroundColor DarkGray
    if (Test-Path "$env:JAVA_HOME\bin\jps.exe") {
        & "$env:JAVA_HOME\bin\jps.exe" | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-Host "  jps.exe is not available. Verify JAVA_HOME is configured." -ForegroundColor Red
    }
}

# Option 3: Start
function Start-Services {
    Clear-Host
    load_env
    Write-Host $Divider -ForegroundColor DarkGray
    Write-Host "  ACTION: Starting Hadoop Services (HDFS & YARN)" -ForegroundColor Cyan
    Write-Host $Divider -ForegroundColor DarkGray
    Write-Host ""

    if (-not (Test-Path "$HadoopDest\sbin\start-dfs.cmd")) {
        Write-Host "  [!] Error: Hadoop is not installed." -ForegroundColor Red
        return
    }

    Write-Host "  [1/2] Invoking start-dfs.cmd..." -ForegroundColor DarkGray
    Start-Process cmd.exe -ArgumentList "/k `"$HadoopDest\sbin\start-dfs.cmd`"" -Verb RunAs

    Write-Host "  [2/2] Invoking start-yarn.cmd..." -ForegroundColor DarkGray
    Start-Process cmd.exe -ArgumentList "/k `"$HadoopDest\sbin\start-yarn.cmd`"" -Verb RunAs

    Write-Host "`n  [✓] Startup commands triggered in separate console windows." -ForegroundColor Green
}

# Option 4: Stop
function Stop-Services {
    Clear-Host
    load_env
    Write-Host $Divider -ForegroundColor DarkGray
    Write-Host "  ACTION: Stopping Hadoop Services (YARN & HDFS)" -ForegroundColor Cyan
    Write-Host $Divider -ForegroundColor DarkGray
    Write-Host ""

    if (-not (Test-Path "$HadoopDest\sbin\stop-all.cmd")) {
        Write-Host "  [!] Error: Hadoop is not installed." -ForegroundColor Red
        return
    }

    Write-Host "  Stopping all daemons..." -ForegroundColor DarkGray
    Start-Process cmd.exe -ArgumentList "/c `"$HadoopDest\sbin\stop-all.cmd`"" -Verb RunAs -Wait

    Write-Host "`n  [✓] Shutdown commands completed." -ForegroundColor Green
}

# Option 5: Delete
function Delete-Hadoop {
    Clear-Host
    Write-Host $Divider -ForegroundColor DarkGray
    Write-Host "  ACTION: Completely Uninstalling Hadoop" -ForegroundColor Red
    Write-Host $Divider -ForegroundColor DarkGray
    Write-Host ""

    Write-Host "  [!] WARNING: This will permanently delete your Hadoop installation," -ForegroundColor Red
    Write-Host "      HDFS data storage directories, and path profiles.`n" -ForegroundColor Red
    
    $confirm = Read-Host "  Are you sure you want to proceed? (y/N)"
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        Write-Host "`n  [1/3] Terminating any running daemons..." -ForegroundColor DarkGray
        Stop-Services > $null 2>&1
        Get-Process -Name java -ErrorAction SilentlyContinue | Stop-Process -Force

        Write-Host "  [2/3] Deleting Hadoop folders..." -ForegroundColor DarkGray
        if (Test-Path $HadoopDest) { cmd.exe /c "rmdir /s /q `"$HadoopDest`"" }

        Write-Host "  [3/3] Clearing Environment Variables..." -ForegroundColor DarkGray
        [Environment]::SetEnvironmentVariable("HADOOP_HOME", $null, "Machine")
        $env:HADOOP_HOME = $null

        # Remove PATH variables
        $Path = [Environment]::GetEnvironmentVariable("Path", "Machine")
        if ($Path -like "*%HADOOP_HOME%\bin*") {
            $Path = $Path -replace ';%HADOOP_HOME%\\bin', ''
            $Path = $Path -replace '%HADOOP_HOME%\\bin;', ''
            [Environment]::SetEnvironmentVariable("Path", $Path, "Machine")
        }

        Write-Host "`n  [✓] Uninstall completed successfully." -ForegroundColor Green
    } else {
        Write-Host "      Uninstall cancelled."
    }
}

# Main Loop
while ($true) {
    Clear-Host
    Write-Host "█ █  ███  ██   ███  ███  ███    █ █  ███  ██ █  ██   █    ███  ███" -ForegroundColor Cyan
    Write-Host "███  █ █  █ █  █ █  █ █  ███    ███  █ █  █ ██  █ █  █    ██   ███" -ForegroundColor Cyan
    Write-Host "█ █  █ █  ██   ███  ███  █      █ █  █ █  █  █  ██   ███  ███  █ █" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Developer: Aditya Pidurkar (github.com/itsadityapidurkar)" -ForegroundColor Cyan
    Write-Host "  Scope:     Apache Hadoop 3.4.2 Single-Node Control Center (Windows)" -ForegroundColor DarkGray
    Write-Host $Divider -ForegroundColor DarkGray
    Write-Host "  1. Install Hadoop" -ForegroundColor Cyan
    Write-Host "  2. Verify Hadoop Installation" -ForegroundColor Cyan
    Write-Host "  3. Start Hadoop Services (HDFS & YARN)" -ForegroundColor Cyan
    Write-Host "  4. Stop Hadoop Services" -ForegroundColor Cyan
    Write-Host "  5. Delete Hadoop Completely" -ForegroundColor Cyan
    Write-Host "  6. Exit" -ForegroundColor Cyan
    Write-Host $Divider -ForegroundColor DarkGray

    $choice = Read-Host "  Select an option [1-6]"
    switch ($choice) {
        "1" { Install-Hadoop; pause_screen }
        "2" { Verify-Hadoop; pause_screen }
        "3" { Start-Services; pause_screen }
        "4" { Stop-Services; pause_screen }
        "5" { Delete-Hadoop; pause_screen }
        "6" { Clear-Host; Write-Host "`n  Exiting Hadoop Handler. Goodbye!"; Exit }
        default { Write-Host "  [!] Invalid choice. Select [1-6]." -ForegroundColor Red; Start-Sleep -Seconds 1.5 }
    }
}
