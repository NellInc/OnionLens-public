"""Local operator commands; the reference server deliberately disables access logs."""
from contextlib import closing
import argparse
import json
import sqlite3
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

from . import Sensor


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        # The reference handler otherwise logs client IPs and raw query strings.
        pass


def demo_app(environ, start_response):
    body = b"OnionLens local sensor. Probe: /_oo/probe; labelled demo: /_oo/demo\n"
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8"),
                              ("Content-Length", str(len(body)))])
    return [] if environ.get("REQUEST_METHOD") == "HEAD" else [body]


def summary(db):
    # Read-only mode avoids silently creating an empty database on a typo.
    uri = Path(db).resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        classes = dict(conn.execute("SELECT traffic_class, COUNT(*) FROM oo_events "
                                    "GROUP BY traffic_class"))
        callbacks = dict(conn.execute("SELECT traffic_class, COUNT(*) FROM oo_events "
                                     "WHERE kind = 'callback' GROUP BY traffic_class"))
        invalid = conn.execute("SELECT COUNT(*) FROM oo_events "
                               "WHERE kind = 'callback_invalid'").fetchone()[0]
    return {"events": {c: classes.get(c, 0) for c in ("unsolicited", "demo")},
            "valid_callbacks": {c: callbacks.get(c, 0) for c in ("unsolicited", "demo")},
            "invalid_callbacks": invalid}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local opt-in WSGI canary sensor")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="run loopback reference demo server")
    serve.add_argument("--db", default="observatory.sqlite3")
    serve.add_argument("--channel", choices=("onion", "clearnet"), required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    report = commands.add_parser("summary", help="print only aggregate local counts")
    report.add_argument("--db", required=True)
    args = parser.parse_args(argv)
    if args.command == "summary":
        try:
            print(json.dumps(summary(args.db), indent=2))
        except sqlite3.Error:
            parser.exit(1, "Cannot read an initialized sensor database.\n")
        return
    app = Sensor(demo_app, args.db, channel=args.channel)
    with make_server(args.host, args.port, app, handler_class=QuietHandler) as server:
        print(f"Sensor listening at http://{args.host}:{server.server_port}; channel={args.channel}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
