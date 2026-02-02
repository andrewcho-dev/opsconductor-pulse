import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class WebhookHandler(BaseHTTPRequestHandler):
    def _write(self, code: int, body: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        if body:
            self.wfile.write(body.encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        body = raw.decode("utf-8", errors="replace")
        print(f"[webhook] path={self.path} body={body}")
        self._write(200, "ok\n")

    def do_GET(self):
        self._write(200, "ok\n")

    def log_message(self, format, *args):
        return


def main() -> None:
    port = int(os.getenv("PORT", "9999"))
    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    print(f"[webhook] listening on :{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
