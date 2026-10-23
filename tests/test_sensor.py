import io
import os
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
import contextlib
import threading
import urllib.request
from wsgiref.simple_server import make_server
from wsgiref.util import setup_testing_defaults

from onion_observatory import Sensor, TOKEN_TTL
from onion_observatory.cli import QuietHandler, main, summary


class SensorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "sensor.sqlite3"
        self.responses = []

        def original(environ, start_response):
            start_response("201 Created", [("Content-Encoding", "gzip"), ("X-App", "original")])
            self.iterable = iter([b"opaque", b"bytes"])
            return self.iterable

        self.original = original
        self.sensor = Sensor(original, self.db, channel="onion")

    def request(self, path, query="", **extra):
        env = {}
        setup_testing_defaults(env)
        env.update(PATH_INFO=path, QUERY_STRING=query)
        env.update(extra)
        result = {}

        def start(status, headers, exc_info=None):
            result.update(status=status, headers=headers)

        iterable = self.sensor(env, start)
        result["body"] = b"".join(iterable)
        if hasattr(iterable, "close"):
            iterable.close()
        return result

    def token(self, endpoint="/_oo/probe"):
        response = self.request(endpoint)
        return re.search(rb"\?t=([A-Za-z0-9_-]{43})", response["body"])[1].decode()

    def rows(self):
        with contextlib.closing(sqlite3.connect(self.db)) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute("SELECT * FROM oo_events ORDER BY id")]

    def test_valid_callback_and_persisted_origin(self):
        token = self.token()
        self.sensor = Sensor(self.original, self.db, channel="onion")
        response = self.request("/_oo/callback", "t=" + token)
        self.assertEqual(response["status"], "200 OK")
        probe, callback = self.rows()
        self.assertEqual(callback["kind"], "callback")
        self.assertEqual(callback["origin_token"], probe["origin_token"])
        self.assertGreaterEqual(callback["read_to_act_seconds"], 0)
        self.assertEqual(callback["traffic_class"], "unsolicited")
        self.assertEqual(callback["channel"], "onion")

    def test_invalid_and_expired_callback(self):
        token = self.token()
        self.assertEqual(self.request("/_oo/callback", "t=invalid")["status"], "400 Bad Request")
        with contextlib.closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("UPDATE oo_tokens SET issued_at = issued_at - ?", (TOKEN_TTL + 1,))
        self.assertEqual(self.request("/_oo/callback", "t=" + token)["status"], "400 Bad Request")
        for row in self.rows()[1:]:
            self.assertEqual(row["kind"], "callback_invalid")
            self.assertIsNone(row["origin_token"])
            self.assertEqual(row["traffic_class"], "unsolicited")

    def test_demo_class_carried_only_by_valid_token(self):
        token = self.token("/_oo/demo")
        self.request("/_oo/callback", "t=" + token)
        self.request("/ordinary", "demo=1", HTTP_X_OO_TEST="1", HTTP_USER_AGENT="test bot")
        self.request("/_oo/callback", "t=invalid&demo=1", HTTP_X_OO_TEST="1")
        self.assertEqual([r["traffic_class"] for r in self.rows()],
                         ["demo", "demo", "unsolicited", "unsolicited"])
        result = summary(self.db)
        self.assertEqual(result["events"], {"demo": 2, "unsolicited": 2})
        self.assertEqual(result["valid_callbacks"], {"demo": 1, "unsolicited": 0})
        self.assertEqual(result["invalid_callbacks"], 1)

    def test_secret_inputs_are_never_logged_or_read(self):
        class Unreadable:
            def read(self, *args):
                raise AssertionError("body was read")
        self.request("/ordinary", "secret-query-value", REQUEST_METHOD="POST",
                     **{"wsgi.input": Unreadable(), "HTTP_AUTHORIZATION": "secret-auth-value",
                        "HTTP_COOKIE": "secret-cookie-value", "REMOTE_ADDR": "192.0.2.77",
                        "HTTP_REFERER": "secret-referrer-value"})
        raw = self.db.read_bytes()
        for forbidden in (b"secret-query-value", b"secret-auth-value", b"secret-cookie-value",
                          b"192.0.2.77", b"secret-referrer-value"):
            self.assertNotIn(forbidden, raw)
        self.assertEqual(self.rows()[0]["kind"], "request")

    def test_original_encoded_stream_preserved(self):
        env = {}
        setup_testing_defaults(env)
        env["PATH_INFO"] = "/original"
        captured = []
        result = self.sensor(env, lambda status, headers: captured.append((status, headers)))
        self.assertIs(result, self.iterable)
        self.assertEqual(captured, [("201 Created", [("Content-Encoding", "gzip"), ("X-App", "original")])])
        self.assertEqual(list(result), [b"opaque", b"bytes"])

    def test_bounds_and_private_file(self):
        self.request("/" + "p" * 2000, HTTP_USER_AGENT="u" * 1000 + "\n")
        row = self.rows()[0]
        self.assertEqual(len(row["path"]), 1024)
        self.assertEqual(len(row["user_agent"]), 512)
        self.assertEqual(self.db.stat().st_mode & 0o777, 0o600)

    def test_loopback_http_roundtrip_without_access_log(self):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            server = make_server("127.0.0.1", 0, self.sensor, handler_class=QuietHandler)
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                with urllib.request.urlopen(base + "/_oo/demo") as response:
                    probe = response.read()
                token = re.search(rb"\?t=([A-Za-z0-9_-]{43})", probe)[1].decode()
                with urllib.request.urlopen(base + "/_oo/callback?t=" + token) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.read(), b"Callback recorded.\n")
                # http.client sends header text as latin-1, so this is UTF-8 on the wire.
                request = urllib.request.Request(base + "/caf%C3%A9/%FF",
                                                 headers={"User-Agent": "Bot/1 \xc2\xa9"})
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status, 201)
            finally:
                server.shutdown()
                thread.join()
                server.server_close()
        self.assertEqual(errors.getvalue(), "")
        self.assertEqual(self.rows()[-2]["traffic_class"], "demo")
        self.assertEqual((self.rows()[-1]["path"], self.rows()[-1]["user_agent"]),
                         ("/café/\\xff", "Bot/1 ©"))

    def test_duplicate_tokens_and_test_markers_cannot_validate(self):
        token = self.token()
        response = self.request("/_oo/callback", f"t={token}&t={token}&test=true")
        self.assertEqual(response["status"], "400 Bad Request")
        self.assertEqual(self.rows()[-1]["traffic_class"], "unsolicited")

    def test_callback_path_includes_mount_point(self):
        root = self.request("/_oo/probe")["body"]
        self.assertIn(b"the same-origin path /_oo/callback?t=", root)
        for mount in ("/app", "/app/"):
            body = self.request("/_oo/demo", SCRIPT_NAME=mount)["body"]
            self.assertIn(b"the same-origin path /app/_oo/callback?t=", body)
        # PEP 3333 latin-1 form of a UTF-8 mount; spaces and query syntax stay inert.
        body = self.request("/_oo/demo", SCRIPT_NAME="/caf\xc3\xa9 x?y")["body"]
        self.assertIn(b"the same-origin path /caf%C3%A9%20x%3Fy/_oo/callback?t=", body)
        token = re.search(rb"\?t=([A-Za-z0-9_-]{43})", body)[1].decode()
        response = self.request("/_oo/callback", "t=" + token, SCRIPT_NAME="/caf\xc3\xa9 x?y")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(self.rows()[-1]["traffic_class"], "demo")

    def test_utf8_paths_and_user_agents_are_decoded(self):
        self.request("/caf\xc3\xa9/\xe6\x9d\xb1\xe4\xba\xac", HTTP_USER_AGENT="Bot/1 \xc2\xa9")
        self.request("/\xff\xc0\xaf", HTTP_USER_AGENT="a\x1b[31m‮b")
        first, second = self.rows()
        self.assertEqual((first["path"], first["user_agent"]), ("/café/東京", "Bot/1 ©"))
        self.assertEqual(second["path"], "/\\xff\\xc0\\xaf")
        self.assertEqual(second["user_agent"], "a [31m b")
        self.request("/" + "\xe6\x9d\xb1" * 2000)
        self.assertEqual(self.rows()[-1]["path"], "/" + "東" * 1023)

    def test_memory_database_is_rejected_without_creating_a_file(self):
        cwd = os.getcwd()
        os.chdir(self.tmp.name)
        self.addCleanup(os.chdir, cwd)
        for db in (":memory:", ""):
            with self.assertRaises(ValueError):
                Sensor(self.original, db, channel="onion")
        self.assertFalse(os.path.exists(":memory:"))

    def test_dangling_symlink_target_is_created_private(self):
        target = Path(self.tmp.name) / "data" / "sensor.sqlite3"
        target.parent.mkdir()
        link = Path(self.tmp.name) / "link.sqlite3"
        link.symlink_to(target)
        existing = Path(self.tmp.name) / "existing.sqlite3"
        existing.touch(mode=0o640)
        existing.chmod(0o640)
        previous = os.umask(0o022)
        try:
            Sensor(self.original, link, channel="onion")
            Sensor(self.original, existing, channel="onion")
        finally:
            os.umask(previous)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertTrue(link.is_symlink())
        self.assertEqual(existing.stat().st_mode & 0o777, 0o640)

    def test_serve_reports_bad_options_without_traceback(self):
        missing = Path(self.tmp.name) / "missing" / "x.sqlite3"
        for argv, code, message in (
                (["--port", "70000"], 2, "port must be 0-65535"),
                (["--db", str(missing), "--port", "0"], 1, "Cannot open sensor database"),
                (["--db", ":memory:", "--port", "0"], 1, "db must be a filesystem path")):
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors), self.assertRaises(SystemExit) as raised:
                main(["serve", "--channel", "onion", *argv])
            self.assertEqual(raised.exception.code, code)
            self.assertIn(message, errors.getvalue())
            self.assertNotIn("Traceback", errors.getvalue())
        self.assertFalse(missing.parent.exists())


if __name__ == "__main__":
    unittest.main()
