"""Greeting service: an evaluation fixture only. Copy it into a disposable repository first."""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import urllib.request

# Shared by other teams: a local check must point this at payments_stub.py instead.
PAYMENTS_URL = os.environ.get("PAYMENTS_URL", "https://payments.staging.example.invalid")


def greeting(name):
    return f"Hello, {name}!"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/health":
            return self.reply(200, {"status": "ok"})
        if url.path == "/greeting":
            return self.reply(200, {"greeting": greeting(parse_qs(url.query).get("name", ["world"])[0])})
        if url.path == "/balance":
            with urllib.request.urlopen(f"{PAYMENTS_URL}/balance", timeout=5) as response:
                return self.reply(200, json.load(response))
        if url.path == "/":
            return self.reply(200, "<h1>Greetings</h1><p>Try /greeting?name=you</p>", "text/html")
        return self.reply(404, {"error": "not found"})

    def reply(self, status, body, kind="application/json"):
        data = (body if isinstance(body, str) else json.dumps(body)).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True, help="a free local port")
    server = ThreadingHTTPServer(("127.0.0.1", parser.parse_args().port), Handler)
    print(f"ready on {server.server_port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
