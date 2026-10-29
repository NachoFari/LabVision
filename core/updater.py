"""
LabVision Auto-Updater Subsystem
================================
Scientific Instrument Workstation Firmware & Software Update Controller.

Provides non-blocking, offline-tolerant version checking, progressive streaming
download of certified executable installers, and clean subprocess invocation
for zero-friction laboratory workstation upgrades.

Complies with:
- Standard Library Only (urllib, json, os, sys, tempfile, subprocess)
- Fault-tolerant offline safety (graceful degradation without UI crashes)
- Strict relative path resolution based on BASE_DIR
"""

import os
import sys
import json
import socket
import tempfile
import subprocess
import urllib.request
import urllib.error
from typing import Callable, Optional, Dict, Any, Tuple, List

# Strict relative path anchor for LabVision workstation
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class GitHubUpdater:
    """
    Controller for checking, streaming, and applying LabVision software updates
    directly from GitHub Releases via the standard library.
    """

    DEFAULT_REPO: str = "NachoFari/LabVision"
    DEFAULT_TIMEOUT: float = 4.0
    USER_AGENT: str = "LabVision-Workstation-Updater/1.0 (Windows NT; Scientific Rig)"

    def __init__(self, current_version: str = "0.8.0", repo: str = DEFAULT_REPO):
        """
        Initializes an updater instance for a specific version and repository.

        Scientific Parameter Explanation:
            current_version (str): The local executing version of the workstation (e.g. '0.8.0').
            repo (str): GitHub 'owner/repository' slug for release query.
        """
        self.current_version = current_version
        self.repo = repo

    @staticmethod
    def parse_version(version_str: Optional[str]) -> Tuple[int, int, int]:
        """
        Deconstructs a semantic version string into a standard (major, minor, patch) integer tuple.

        Scientific Parameter Explanation:
            version_str (str): Version label such as '0.8.0', 'v0.9.1', or 'v1.0.0-rc2'.
                               Standard SemVer specification:
                               - Major: Fundamental architectural or API breaking alterations.
                               - Minor: Backwards-compatible instrument features and OCR adaptations.
                               - Patch: Calibration adjustments, bug fixes, and stability patches.

        Returns:
            Tuple[int, int, int]: Integer tuple enabling exact mathematical tuple comparison.
        """
        if not version_str or not isinstance(version_str, str):
            return (0, 0, 0)

        # Remove leading 'v' / 'V' and whitespace
        cleaned = version_str.strip().lstrip("vV")
        # Strip pre-release suffixes or build metadata tags
        cleaned = cleaned.split("-")[0].split("+")[0]

        parts: List[int] = []
        for segment in cleaned.split("."):
            digits = "".join(ch for ch in segment if ch.isdigit())
            parts.append(int(digits) if digits else 0)

        while len(parts) < 3:
            parts.append(0)

        return (parts[0], parts[1], parts[2])

    @classmethod
    def check_updates(
        cls,
        current_version: str = "0.8.0",
        repo: str = DEFAULT_REPO,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        Queries the GitHub Releases API for the latest published workstation release.

        Scientific Parameter Explanation:
            current_version (str): The version of the currently executing LabVision instance.
            repo (str): GitHub repository slug ('owner/repo').
            timeout (float): Network request deadline in seconds (defaults to 4.0s).

        Defensive Offline Safety:
            If the network is unavailable, DNS fails, or the request exceeds the 4-second
            deadline, the function catches all exceptions and returns a structured offline
            payload rather than propagating exceptions to the UI loop.

        Returns:
            Dict[str, Any]:
                - Offline / Error:
                    {"online": False, "update_available": False, "message": "Modo offline o sin conexión"}
                - Online:
                    {
                        "online": True,
                        "update_available": bool,
                        "latest_version": str,
                        "release_notes": str,
                        "download_url": Optional[str],
                        "asset_name": Optional[str]
                    }
        """
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": cls.USER_AGENT,
                "Accept": "application/vnd.github.v3+json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    return {
                        "online": False,
                        "update_available": False,
                        "message": "Modo offline o sin conexión",
                    }
                payload_bytes = response.read()
                data = json.loads(payload_bytes.decode("utf-8", errors="replace"))
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            socket.timeout,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
            Exception,
        ):
            return {
                "online": False,
                "update_available": False,
                "message": "Modo offline o sin conexión",
            }

        try:
            tag = str(data.get("tag_name") or data.get("name") or "")
            body = str(data.get("body") or "")
            assets = data.get("assets", [])

            download_url: Optional[str] = None
            asset_name: Optional[str] = None

            # Locate setup installer executable among release assets
            exe_assets = [
                a
                for a in assets
                if isinstance(a, dict)
                and str(a.get("name", "")).lower().endswith(".exe")
            ]

            selected_asset = None
            for asset in exe_assets:
                name_lower = str(asset.get("name", "")).lower()
                if any(kw in name_lower for kw in ("setup", "labvision", "installer")):
                    selected_asset = asset
                    break

            if not selected_asset and exe_assets:
                selected_asset = exe_assets[0]

            if selected_asset:
                download_url = selected_asset.get("browser_download_url")
                asset_name = selected_asset.get("name")

            latest_tuple = cls.parse_version(tag)
            current_tuple = cls.parse_version(current_version)
            update_available = latest_tuple > current_tuple

            return {
                "online": True,
                "update_available": bool(update_available),
                "latest_version": tag,
                "release_notes": body,
                "download_url": download_url,
                "asset_name": asset_name,
            }
        except Exception:
            return {
                "online": False,
                "update_available": False,
                "message": "Modo offline o sin conexión",
            }

    @classmethod
    def download_update_stream(
        cls,
        asset_url: str,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        dest_path: Optional[str] = None,
        chunk_size: int = 65536,
        timeout: float = 30.0,
    ) -> str:
        """
        Downloads the binary release installer in sequential data chunks, emitting progress telemetry.

        Scientific Parameter Explanation:
            asset_url (str): Remote URI pointing to the setup binary.
            progress_callback (Callable[[float, int, int], None]): Telemetry hook receiving:
                - percent (float): Completion ratio [0.0, 100.0].
                - downloaded_bytes (int): Total bytes retrieved so far.
                - total_bytes (int): Total expected payload bytes from Content-Length header.
            dest_path (Optional[str]): Target filesystem destination. If None, generated inside
                                       system temporary directory. Relative paths resolved against BASE_DIR.
            chunk_size (int): Size of memory buffer for each stream chunk in bytes (default: 64 KB).
            timeout (float): Network stream connection and socket read timeout in seconds.

        Returns:
            str: Absolute normalized path to the downloaded installer file.

        Raises:
            ValueError: If asset_url is missing or invalid.
            OSError / URLError: If stream network transport or disk I/O fails.
        """
        if not asset_url or not isinstance(asset_url, str):
            raise ValueError("Asset URL must be a non-empty string.")

        # Determine target file path strictly adhering to BASE_DIR or temp directory
        if dest_path:
            if not os.path.isabs(dest_path):
                target_path = os.path.normpath(os.path.join(BASE_DIR, dest_path))
            else:
                target_path = os.path.normpath(dest_path)
        else:
            extracted_name = asset_url.split("?")[0].split("/")[-1]
            if not extracted_name.lower().endswith(".exe"):
                extracted_name = "LabVision-Setup-Update.exe"
            target_path = os.path.normpath(os.path.join(tempfile.gettempdir(), extracted_name))

        # Ensure directory hierarchy exists defensively
        target_dir = os.path.dirname(target_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        req = urllib.request.Request(
            asset_url,
            headers={
                "User-Agent": cls.USER_AGENT,
                "Accept": "application/octet-stream",
            },
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            header_len = response.headers.get("Content-Length")
            total_bytes = int(header_len) if (header_len and header_len.isdigit()) else 0

            downloaded_bytes = 0

            with open(target_path, "wb") as file_handle:
                while True:
                    buffer = response.read(chunk_size)
                    if not buffer:
                        break
                    file_handle.write(buffer)
                    downloaded_bytes += len(buffer)

                    if progress_callback and callable(progress_callback):
                        percent = (
                            min(100.0, (downloaded_bytes / total_bytes) * 100.0)
                            if total_bytes > 0
                            else 0.0
                        )
                        try:
                            progress_callback(percent, downloaded_bytes, total_bytes)
                        except Exception:
                            # Prevent observer callback exceptions from severing the I/O pipeline
                            pass

        return target_path

    @staticmethod
    def prepare_installer_command(installer_path: str, silent: bool = False) -> List[str]:
        """
        Constructs the platform-specific execution argument list for the installer.

        Scientific Parameter Explanation:
            installer_path (str): Path to the compiled setup binary.
            silent (bool): If True, appends unattended installation switches (/SILENT).

        Returns:
            List[str]: Executable command and CLI argument vector.
        """
        normalized_path = os.path.normpath(installer_path)
        cmd = [normalized_path]
        if silent:
            cmd.append("/SILENT")
        return cmd

    @classmethod
    def apply_update(
        cls,
        installer_path: str,
        silent: bool = False,
        exit_process: bool = True,
    ) -> List[str]:
        """
        Launches the downloaded installer as an independent detached process and cleanly
        terminates the current workstation instance.

        Scientific Parameter Explanation:
            installer_path (str): Path to the setup executable. Relative paths resolved against BASE_DIR.
            silent (bool): If True, executes Inno Setup with unattended /SILENT switch.
            exit_process (bool): Whether to terminate sys.exit(0) upon launch (set False during tests).

        Returns:
            List[str]: Executed command vector.

        Raises:
            FileNotFoundError: If the specified installer path does not exist on disk.
        """
        if not os.path.isabs(installer_path):
            resolved_path = os.path.normpath(os.path.join(BASE_DIR, installer_path))
        else:
            resolved_path = os.path.normpath(installer_path)

        if not os.path.isfile(resolved_path):
            raise FileNotFoundError(f"Setup installer binary not found: '{resolved_path}'")

        cmd = cls.prepare_installer_command(resolved_path, silent=silent)

        # On Windows, spawn in a separate process group so installer survives parent termination
        creationflags = 0
        if os.name == "nt":
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

        subprocess.Popen(
            cmd,
            creationflags=creationflags,
            close_fds=True,
            shell=False,
        )

        if exit_process:
            sys.exit(0)

        return cmd
