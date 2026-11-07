"""Streaming downloader with live single-line progress bar, transfer rate, and ETA."""

import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from hadoop_handler.core.config import (
    CACHE_DIR,
    DOWNLOADS_DIR,
    GREEN,
    NC,
    RED,
    USER_HOME,
    VERSION,
    YELLOW,
)


def find_cached_archive(filename: str, min_size: int = 50_000_000) -> Optional[Path]:
    """Search for existing valid cached archive across filesystem to prevent redundant downloads."""
    search_dirs = [
        DOWNLOADS_DIR,
        CACHE_DIR,
        Path("/tmp"),
        USER_HOME,
        Path("/opt"),
    ]
    for d in search_dirs:
        candidate = d / filename
        if candidate.exists() and candidate.is_file():
            try:
                sz = candidate.stat().st_size
                if sz >= min_size:
                    return candidate
            except Exception:
                pass
    return None


def resolve_apache_url(
    project: str,
    filename: str,
    subpath: Optional[str] = None,
) -> str:
    """Resolve active download URL using Apache CDN with fallback to archive."""
    sub = f"/{subpath}" if subpath else ""
    mirror_url = f"https://downloads.apache.org/{project}{sub}/{filename}"
    archive_url = f"https://archive.apache.org/dist/{project}{sub}/{filename}"

    req = urllib.request.Request(
        mirror_url,
        headers={"User-Agent": f"Hadoop-Handler/{VERSION}"},
        method="HEAD",
    )
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status in (200, 302):
                return mirror_url
    except Exception:
        pass
    return archive_url


def resolve_hadoop_url(version: str) -> str:
    """Resolve download URL for specific Hadoop version."""
    tar_name = f"hadoop-{version}.tar.gz"
    return resolve_apache_url("hadoop/common", tar_name, f"hadoop-{version}")


def download_file(url: str, dest_path: Path, title: str = "Downloading") -> bool:
    """Download a remote URL to local destination with live progress bar."""
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": f"Hadoop-Handler/{VERSION}"}
    resume_byte_pos = 0
    if dest.exists():
        resume_byte_pos = dest.stat().st_size

    req = urllib.request.Request(url, headers=headers)
    if resume_byte_pos > 0:
        req.add_header("Range", f"bytes={resume_byte_pos}-")

    print(f"        {title}...")
    try:
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            content_length = resp.headers.get("Content-Length")
            if resp.status == 206:
                total_size = resume_byte_pos + int(content_length) if content_length else 0
                mode = "ab"
                downloaded = resume_byte_pos
            else:
                total_size = int(content_length) if content_length else 0
                mode = "wb"
                downloaded = 0

            start_time = time.time()
            chunk_size = 131072
            bar_width = 24

            with open(dest, mode) as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    elapsed = time.time() - start_time
                    speed = (downloaded - resume_byte_pos) / elapsed if elapsed > 0 else 0

                    if total_size > 0:
                        pct = min(100.0, (downloaded / total_size) * 100)
                        filled = int(bar_width * downloaded // total_size)
                        bar = "█" * filled + "░" * (bar_width - filled)
                        eta = (total_size - downloaded) / speed if speed > 0 else 0
                        eta_str = f"{int(eta // 60):02d}:{int(eta % 60):02d}"
                        line = (
                            f"\r        [{bar}] {pct:5.1f}% "
                            f"({downloaded / (1024 * 1024):.1f}/{total_size / (1024 * 1024):.1f} MB) "
                            f"{speed / (1024 * 1024):.1f} MB/s ETA {eta_str}"
                        )
                    else:
                        line = (
                            f"\r        Downloaded: {downloaded / (1024 * 1024):.1f} MB "
                            f"({speed / (1024 * 1024):.1f} MB/s)"
                        )
                    sys.stdout.write(line)
                    sys.stdout.flush()
            print()
            return True
    except Exception as e:
        print(f"\n        {RED}[!] Download error: {e}{YELLOW}")
        return False
