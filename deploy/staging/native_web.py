"""Loopback-only HTTPS/SPA harness for testing the built Vite app; not a host."""
from pathlib import Path
import functools
import http.client
import http.server
import os
import ssl
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".staging"

class StagingHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "public,max-age=31536000,immutable" if self.path.startswith("/assets/") else "no-store")
        super().end_headers()

    def proxy(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1048576:
            self.send_error(413)
            return
        body = self.rfile.read(length) if length else None
        headers = {key: value for key, value in self.headers.items()
                   if key.lower() not in ("host", "connection", "transfer-encoding", "content-length")}
        try:
            connection = http.client.HTTPConnection("127.0.0.1", 18888, timeout=30)
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            payload = response.read()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in ("connection", "transfer-encoding", "content-length"):
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            connection.close()
        except OSError:
            self.send_error(502, "Local staging API unavailable")

    def do_GET(self):
        if self.path.startswith("/api/") or self.path in ("/health", "/ready"):
            return self.proxy()
        if self.path == "/metrics":
            return self.send_error(404)
        path = self.path.split("?", 1)[0]
        if "." not in Path(path).name:
            self.path = "/index.html"
        return super().do_GET()

    def write_request(self):
        if self.path.startswith("/api/v1/"):
            return self.proxy()
        return self.send_error(404)

    do_POST = write_request
    do_PATCH = write_request
    do_DELETE = write_request
    do_OPTIONS = write_request

if "--serve" in sys.argv:
    handler = functools.partial(StagingHandler, directory=str(ROOT / "frontend/dist"))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 18443), handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(STATE / "local.crt", STATE / "local.key")
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()
else:
    if not ((STATE / "local.key").exists() and (STATE / "local.crt").exists()):
        config = STATE / "openssl-local.cnf"
        config.write_text("[req]\ndistinguished_name=subject\n[subject]\nCN=staging.footballheritage.test\n")
        subprocess.run([r"C:\Program Files\Git\usr\bin\openssl.exe", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                        "-config", str(config),
                        "-days", "7", "-keyout", str(STATE / "local.key"), "-out", str(STATE / "local.crt"),
                        "-subj", "/CN=staging.footballheritage.test",
                        "-addext", "subjectAltName=DNS:staging.footballheritage.test,DNS:localhost"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with (STATE / "native-web.log").open("w") as log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--serve"], stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    (STATE / "native-web.pid").write_text(str(process.pid))
    print("Started loopback HTTPS staging harness on 18443; certificate is local and untrusted.")
