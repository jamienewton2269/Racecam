#!/usr/bin/env python3
"""Isolated receiver pairing regression tests. Never touches a running receiver."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from urllib import request, error
from http.server import ThreadingHTTPServer

SOURCE = Path(__file__).with_name("receiver.py")


class PairingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["RACECAM_DB"] = str(Path(self.tmp.name) / "test.sqlite3")
        os.environ["RACECAM_ADMIN_TOKEN"] = "integration-test-only"
        os.environ["RACECAM_PUBLIC_URL"] = "https://racecam.example.test"
        spec = importlib.util.spec_from_file_location("racecam_receiver_under_test", SOURCE)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.mod.DB = os.environ["RACECAM_DB"]
        self.mod.ADMIN = os.environ["RACECAM_ADMIN_TOKEN"]
        self.mod.PUBLIC = os.environ["RACECAM_PUBLIC_URL"]
        self.mod.ATTEMPTS.clear()
        self.mod.db().close()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.mod.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.tmp.cleanup()

    def post(self, path, data, admin=False):
        headers = {"Content-Type": "application/json"}
        if admin:
            headers["Authorization"] = "Bearer integration-test-only"
        req = request.Request(
            f"http://127.0.0.1:{self.server.server_port}{path}",
            data=json.dumps(data).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=5) as response:
                return response.status, json.load(response)
        except error.HTTPError as exc:
            return exc.code, json.load(exc)

    def invite(self):
        code, payload = self.post("/admin/pairings", {}, admin=True)
        self.assertEqual(code, 201)
        return payload["payload"]["token"]

    def test_admin_authentication(self):
        code, _ = self.post("/admin/pairings", {})
        self.assertEqual(code, 403)
        self.assertTrue(self.invite())

    def test_replay_and_revocation(self):
        token = self.invite()
        code, camera = self.post("/api/pair", {"token": token})
        self.assertEqual(code, 201)
        code, _ = self.post("/api/pair", {"token": token})
        self.assertEqual(code, 403)
        auth = {"action": "publish", "protocol": "srt", "user": camera["camera_id"],
                "password": camera["credential"], "path": camera["camera_id"]}
        self.assertEqual(self.post("/api/mediamtx/auth", auth)[0], 200)
        self.assertEqual(self.post("/admin/cameras/revoke",
                                   {"camera_id": camera["camera_id"]}, admin=True)[0], 200)
        self.assertEqual(self.post("/api/mediamtx/auth", auth)[0], 403)

    def test_expired_invitation(self):
        token = self.invite()
        with sqlite3.connect(self.mod.DB) as conn:
            conn.execute("UPDATE sessions SET expires=0 WHERE digest=?", (self.mod.digest(token),))
        self.assertEqual(self.post("/api/pair", {"token": token})[0], 403)

    def test_concurrent_redemption(self):
        from concurrent.futures import ThreadPoolExecutor
        token = self.invite()
        with ThreadPoolExecutor(max_workers=6) as executor:
            codes = list(executor.map(
                lambda _: self.post("/api/pair", {"token": token})[0], range(6)))
        self.assertEqual(codes.count(201), 1)
        self.assertEqual(codes.count(403), 5)

    def test_invalid_publisher(self):
        self.assertEqual(self.post("/api/mediamtx/auth",
                                   {"action": "read", "protocol": "srt",
                                    "user": "none", "password": "none", "path": "none"})[0], 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
