from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs


class RequestLogger(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        error_code = params.get("error_code", [None])[0]
        # Handle error param
        error_messages = {
            "E1001": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "E2002": "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "E3003": "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
            "E4004": "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum.",
        }
        if error_code in error_messages:
            message = error_messages[error_code]
            print(f"Matched {error_code}: {message}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"{error_code} : {message}".encode("utf-8"))
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        self._handle(parsed, params)

    def do_POST(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

        self._handle(parsed, params)

    def _handle(self, parsed, params):
        print(f"\n--- {self.command} {parsed.path} ---")
        print("Query params:", params)
        print("Headers:")
        print(self.headers)

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            print("Body:")
            print(body.decode("utf-8", errors="replace"))


if __name__ == "__main__":
    port = 4000
    server = HTTPServer(("127.0.0.1", port), RequestLogger)
    print(f"Listening on port {port}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n Shutting down")
        server.server_close()
