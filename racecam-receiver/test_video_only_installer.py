#!/usr/bin/env python3
"""Enforce the video-only receiver boundary without touching live services."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
INSTALLER = ROOT / "install-loopback.sh"

class VideoOnlyInstallerTests(unittest.TestCase):
    def test_installer_has_no_telemetry_dependencies(self):
        script = INSTALLER.read_text()
        forbidden = (
            "telemetry.py", "status.py", "racecam-telemetry.service",
            "racecam-status.service", "8788", "8789", "/api/telemetry",
            "/api/race/positions",
        )
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, script)

    def test_installer_only_installs_pairing_service(self):
        script = INSTALLER.read_text()
        self.assertIn("receiver.py", script)
        self.assertIn("racecam-pairing.service", script)
        self.assertIn("127.0.0.1", script)
        self.assertNotIn("mediamtx.yml", script)

if __name__ == "__main__":
    unittest.main()
