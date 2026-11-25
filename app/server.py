"""orders-api: a minimal orders service with a health endpoint (standard library only)."""

import argparse
import http.server
import json
from pathlib import Path

ORDERS = [
    {"id": "ORD-1001", "customer": "ACME SAC", "total": 1250.00, "status": "PAID"},
    {"id": "ORD-1002", "customer": "Andes Retail", "total": 310.50, "status": "PENDING"},
]


def count_by_status(orders):
    """Count orders by status."""
    by_status = {}
    for order in orders:
        by_status[order["status"]] = by_status.get(order["status"], 0) + 1
    return by_status


def paid_total(orders):
    """Add up the amount of the paid orders."""
    paid = sum(order["amount"] for order in orders if order["status"] == "PAID")
    return round(paid, 2)


def order_summary(orders):
    return {"count": len(orders), "byStatus": count_by_status(orders), "paidTotal": paid_total(orders)}


def load_settings(path):
    """Read the optional JSON settings file; returns the settings and a startup error, if any."""
    if path is None:
        return {}, None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return {}, f"configuration file not found: {path}"
    except json.JSONDecodeError as error:
        return {}, f"invalid configuration {path}: {error}"


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.server.startup_error:
            self._send(500, {"status": "DOWN"})
        elif self.path == "/health":
            self._send(200, {"status": "UP"})
        elif self.path == "/orders/summary":
            self._send(200, order_summary(ORDERS))
        else:
            self._send(404, {"error": "not found"})

    def _send(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print(f"[{self.server.name}] {self.address_string()} {fmt % args}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--config", help="optional JSON settings file")
    args = parser.parse_args()
    settings, startup_error = load_settings(args.config)
    if startup_error:
        print(f"[{args.name}] fail: Application startup exception: {startup_error}", flush=True)
    elif args.config:
        print(f"[{args.name}] info: settings loaded from {args.config} "
              f"(environment {settings.get('environment', 'unknown')})", flush=True)
    server = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    server.name = args.name
    server.startup_error = startup_error
    print(f"[{args.name}] listening on http://localhost:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
