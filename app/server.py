"""orders-api: a minimal orders service with a health endpoint (standard library only)."""

import argparse
import http.server
import json

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
    paid = sum(order["total"] for order in orders if order["status"] == "PAID")
    return round(paid, 2)


def order_summary(orders):
    return {"count": len(orders), "byStatus": count_by_status(orders), "paidTotal": paid_total(orders)}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
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
    args = parser.parse_args()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    server.name = args.name
    print(f"[{args.name}] listening on http://localhost:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
