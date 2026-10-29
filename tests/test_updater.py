"""
Unit & Integration Tests for LabVision GitHub Auto-Updater
=========================================================
Verifies:
1. Version parsing and tuple comparison logic (major, minor, patch).
2. Defensive offline failure handling without unhandled exceptions.
3. GitHub Releases API response parsing (assets, URLs, changelog).
4. Chunked stream downloader and progress callback calculation.
5. Installer launch command preparation and process execution.
"""

import io
import os
import sys
import json
import socket
import unittest
import tempfile
import urllib.request
import urllib.error
from unittest.mock import patch, MagicMock

# Ensure LabVision root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.updater import GitHubUpdater


class TestGitHubUpdaterVersionLogic(unittest.TestCase):
    """Test suite for semantic version parsing and comparison."""

    def test_version_tuples(self):
        self.assertEqual(GitHubUpdater.parse_version("0.8.0"), (0, 8, 0))
        self.assertEqual(GitHubUpdater.parse_version("0.9.0"), (0, 9, 0))
        self.assertEqual(GitHubUpdater.parse_version("v0.8.1"), (0, 8, 1))
        self.assertEqual(GitHubUpdater.parse_version("V1.2.3"), (1, 2, 3))
        self.assertEqual(GitHubUpdater.parse_version("1.0"), (1, 0, 0))
        self.assertEqual(GitHubUpdater.parse_version("2"), (2, 0, 0))

    def test_version_comparison_required_scenarios(self):
        # 0.8.0 < 0.9.0
        v_080 = GitHubUpdater.parse_version("0.8.0")
        v_090 = GitHubUpdater.parse_version("0.9.0")
        self.assertLess(v_080, v_090)

        # 0.8.1 > 0.8.0
        v_081 = GitHubUpdater.parse_version("0.8.1")
        self.assertGreater(v_081, v_080)

        # 1.0.0 > 0.9.9
        v_100 = GitHubUpdater.parse_version("1.0.0")
        v_099 = GitHubUpdater.parse_version("0.9.9")
        self.assertGreater(v_100, v_099)

        # v-prefixed comparison
        v_v081 = GitHubUpdater.parse_version("v0.8.1")
        self.assertGreater(v_v081, v_080)
        self.assertEqual(v_v081, v_081)

    def test_version_defensive_fallbacks(self):
        self.assertEqual(GitHubUpdater.parse_version(""), (0, 0, 0))
        self.assertEqual(GitHubUpdater.parse_version(None), (0, 0, 0))
        self.assertEqual(GitHubUpdater.parse_version("invalid_ver"), (0, 0, 0))
        self.assertEqual(GitHubUpdater.parse_version("0.9.0-rc1+build42"), (0, 9, 0))


class TestGitHubUpdaterOfflineSafety(unittest.TestCase):
    """Test suite verifying fault-tolerant offline behavior."""

    @patch("urllib.request.urlopen")
    def test_offline_url_error(self, mock_urlopen):
        # Simulate network down / DNS failure
        mock_urlopen.side_effect = urllib.error.URLError("No route to host")
        result = GitHubUpdater.check_updates(current_version="0.8.0")

        self.assertFalse(result["online"])
        self.assertFalse(result["update_available"])
        self.assertEqual(result["message"], "Modo offline o sin conexión")

    @patch("urllib.request.urlopen")
    def test_offline_socket_timeout(self, mock_urlopen):
        # Simulate 4-second timeout expiration
        mock_urlopen.side_effect = socket.timeout("The read operation timed out")
        result = GitHubUpdater.check_updates(current_version="0.8.0")

        self.assertFalse(result["online"])
        self.assertFalse(result["update_available"])
        self.assertEqual(result["message"], "Modo offline o sin conexión")

    @patch("urllib.request.urlopen")
    def test_http_server_error(self, mock_urlopen):
        # Simulate GitHub 503 or 404
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.github.com",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=None,
        )
        result = GitHubUpdater.check_updates(current_version="0.8.0")

        self.assertFalse(result["online"])
        self.assertFalse(result["update_available"])
        self.assertEqual(result["message"], "Modo offline o sin conexión")

    @patch("urllib.request.urlopen")
    def test_corrupt_json_payload(self, mock_urlopen):
        # Simulate corrupted or incomplete JSON transmission
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"{corrupted_json: incomplete...}"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = GitHubUpdater.check_updates(current_version="0.8.0")
        self.assertFalse(result["online"])
        self.assertFalse(result["update_available"])
        self.assertEqual(result["message"], "Modo offline o sin conexión")


class TestGitHubUpdaterResponseParsing(unittest.TestCase):
    """Test suite for parsing simulated GitHub API release payloads."""

    def _create_mock_response(self, payload_dict, status=200):
        mock_resp = MagicMock()
        mock_resp.status = status
        mock_resp.read.return_value = json.dumps(payload_dict).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        return mock_resp

    @patch("urllib.request.urlopen")
    def test_update_available_with_setup_asset(self, mock_urlopen):
        payload = {
            "tag_name": "v0.9.0",
            "name": "LabVision Universal v0.9.0",
            "body": "## Novedades\n- Soporte para balanza y pH-metro\n- Presets universales",
            "assets": [
                {
                    "name": "source_code.zip",
                    "browser_download_url": "https://github.com/NachoFari/LabVision/releases/download/v0.9.0/source.zip",
                },
                {
                    "name": "LabVision-Setup-v0.9.0.exe",
                    "browser_download_url": "https://github.com/NachoFari/LabVision/releases/download/v0.9.0/LabVision-Setup-v0.9.0.exe",
                },
            ],
        }
        mock_urlopen.return_value = self._create_mock_response(payload)

        result = GitHubUpdater.check_updates(current_version="0.8.0")

        self.assertTrue(result["online"])
        self.assertTrue(result["update_available"])
        self.assertEqual(result["latest_version"], "v0.9.0")
        self.assertIn("Novedades", result["release_notes"])
        self.assertEqual(result["asset_name"], "LabVision-Setup-v0.9.0.exe")
        self.assertEqual(
            result["download_url"],
            "https://github.com/NachoFari/LabVision/releases/download/v0.9.0/LabVision-Setup-v0.9.0.exe",
        )

    @patch("urllib.request.urlopen")
    def test_already_on_latest_version(self, mock_urlopen):
        payload = {
            "tag_name": "v0.8.0",
            "name": "LabVision v0.8.0",
            "body": "Versión actual de laboratorio",
            "assets": [
                {
                    "name": "LabVision-Setup-v0.8.0.exe",
                    "browser_download_url": "https://github.com/download/setup.exe",
                }
            ],
        }
        mock_urlopen.return_value = self._create_mock_response(payload)

        result = GitHubUpdater.check_updates(current_version="0.8.0")

        self.assertTrue(result["online"])
        self.assertFalse(result["update_available"])
        self.assertEqual(result["latest_version"], "v0.8.0")
        self.assertEqual(result["asset_name"], "LabVision-Setup-v0.8.0.exe")

    @patch("urllib.request.urlopen")
    def test_release_without_exe_asset(self, mock_urlopen):
        payload = {
            "tag_name": "v0.9.5",
            "name": "LabVision v0.9.5",
            "body": "No installer asset uploaded yet",
            "assets": [
                {
                    "name": "checksums.txt",
                    "browser_download_url": "https://github.com/checksums.txt",
                }
            ],
        }
        mock_urlopen.return_value = self._create_mock_response(payload)

        result = GitHubUpdater.check_updates(current_version="0.8.0")

        self.assertTrue(result["online"])
        self.assertTrue(result["update_available"])
        self.assertIsNone(result["download_url"])
        self.assertIsNone(result["asset_name"])


class TestGitHubUpdaterStreamingDownload(unittest.TestCase):
    """Test suite for chunked download streaming and progress telemetry."""

    @patch("urllib.request.urlopen")
    def test_download_update_stream_chunks_and_progress(self, mock_urlopen):
        dummy_content = b"LABVISION_BINARY_CHUNK_" * 1000  # ~23 KB
        content_len = len(dummy_content)

        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Length": str(content_len)}
        stream = io.BytesIO(dummy_content)
        mock_resp.read = stream.read
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        progress_records = []

        def callback(pct, downloaded, total):
            progress_records.append((pct, downloaded, total))

        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = os.path.join(tmp_dir, "test_setup.exe")
            saved_path = GitHubUpdater.download_update_stream(
                asset_url="https://github.com/dummy/setup.exe",
                progress_callback=callback,
                dest_path=dest,
                chunk_size=4096,
            )

            self.assertEqual(saved_path, dest)
            self.assertTrue(os.path.exists(dest))
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), dummy_content)

            self.assertTrue(len(progress_records) > 0)
            last_record = progress_records[-1]
            self.assertAlmostEqual(last_record[0], 100.0)
            self.assertEqual(last_record[1], content_len)
            self.assertEqual(last_record[2], content_len)

    @patch("urllib.request.urlopen")
    def test_download_divide_by_zero_safety(self, mock_urlopen):
        # When Content-Length header is missing or 0
        dummy_content = b"DATA_WITHOUT_CONTENT_LENGTH"
        mock_resp = MagicMock()
        mock_resp.headers = {}
        stream = io.BytesIO(dummy_content)
        mock_resp.read = stream.read
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        progress_records = []

        def callback(pct, downloaded, total):
            progress_records.append((pct, downloaded, total))

        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = os.path.join(tmp_dir, "test_no_len.exe")
            # Should not raise ZeroDivisionError
            GitHubUpdater.download_update_stream(
                asset_url="https://github.com/dummy/test.exe",
                progress_callback=callback,
                dest_path=dest,
            )
            self.assertTrue(os.path.exists(dest))
            self.assertEqual(progress_records[-1][0], 0.0)


class TestGitHubUpdaterApplyUpdate(unittest.TestCase):
    """Test suite for command formulation and installer launch."""

    def test_prepare_installer_command(self):
        cmd_standard = GitHubUpdater.prepare_installer_command("C:\\setup.exe", silent=False)
        self.assertEqual(cmd_standard, [os.path.normpath("C:\\setup.exe")])

        cmd_silent = GitHubUpdater.prepare_installer_command("C:\\setup.exe", silent=True)
        self.assertEqual(cmd_silent, [os.path.normpath("C:\\setup.exe"), "/SILENT"])

    @patch("subprocess.Popen")
    def test_apply_update_execution(self, mock_popen):
        # Create a real temporary file as dummy installer
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp_exe:
            tmp_exe.write(b"MOCK_EXE")
            tmp_exe_path = tmp_exe.name

        try:
            cmd = GitHubUpdater.apply_update(
                installer_path=tmp_exe_path,
                silent=True,
                exit_process=False,
            )

            mock_popen.assert_called_once()
            called_args, called_kwargs = mock_popen.call_args
            self.assertEqual(called_args[0], [os.path.normpath(tmp_exe_path), "/SILENT"])
            self.assertEqual(cmd, [os.path.normpath(tmp_exe_path), "/SILENT"])
        finally:
            if os.path.exists(tmp_exe_path):
                os.remove(tmp_exe_path)

    def test_apply_update_missing_file_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            GitHubUpdater.apply_update("non_existent_installer_path_xyz.exe", exit_process=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
