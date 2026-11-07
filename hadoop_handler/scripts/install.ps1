# ==============================================================================
#  Hadoop Handler v2.0.0 — Pure Python Windows Launcher (PowerShell)
#  Developer: Aditya Pidurkar (github.com/itsadityapidurkar)
# ==============================================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONPATH = "$ScriptDir;$env:PYTHONPATH"

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m hadoop_handler.cli $args
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    & python3 -m hadoop_handler.cli $args
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -m hadoop_handler.cli $args
} else {
    Write-Error "[!] Error: Python 3 is required to run hadoop-handler v2.0."
    exit 1
}
