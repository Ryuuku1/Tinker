"""Local stand-in for the shared payments service, for isolated checks of the fixture app."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = json.dumps({"balance": 0, "source": "local stub"}).encode("utf-8")
        self.send_response(200 if self.path == "/balance" else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    server = ThreadingHTTPServer(("127.0.0.1", parser.parse_args().port), Handler)
    print(f"stub ready on {server.server_port}", flush=True)
    server.serve_forever()
