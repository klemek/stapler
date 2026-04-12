import http.server
import http
import tarfile
import re
import io
import os

from . import project, params, registry, data_dir


class StaplerRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/2.0"
    server_version = "StaplerServer/" + project.get_version()
    CERTBOT_CHALLENGE_PATH = "/.well-known/acme-challenge"

    def __init__(
        self, *args, params: params.Parameters, registry: registry.Registry, **kwargs
    ):
        self.default_host = params.host
        self.token = params.token
        self.data_dir = data_dir.DataDir(params.data_dir)
        self.max_size_bytes = params.max_size_bytes
        self.registry = registry
        self.certbot_www = os.path.realpath(params.certbot_www)
        super().__init__(*args, directory=params.data_dir, **kwargs)

    def list_directory(self, *_, **__):
        """Disable default directory listing"""
        self.send_error(http.HTTPStatus.NOT_FOUND, "File not found")

    def translate_path(self, path: str) -> str:
        if path.startswith(self.CERTBOT_CHALLENGE_PATH):
            return self.certbot_www + path.removeprefix(self.CERTBOT_CHALLENGE_PATH)
        if (page := self.registry.get_from_host(self.get_host())) is not None:
            path = f"/{page.path}" + path
        path = super().translate_path(path)
        if os.path.basename(path).startswith("."):  # hidden files
            return ""
        return path

    def do_GET(self):
        if self.path == "/" and self.get_host() == self.default_host:
            return self.server_index()
        super().do_GET()

    def do_PUT(self):
        if self.headers["X-Token"] != self.token:
            return self.send_error(http.HTTPStatus.UNAUTHORIZED, "Invalid token")
        if (sub_path := self.get_subpath()) is None:
            return self.send_error(http.HTTPStatus.BAD_REQUEST, "Invalid path")
        content_length = int(self.headers["Content-Length"])
        if content_length == 0:
            return self.send_error(http.HTTPStatus.LENGTH_REQUIRED, "No body found")
        if content_length > self.max_size_bytes:
            return self.send_error(
                http.HTTPStatus.CONTENT_TOO_LARGE, "Archive too large"
            )
        try:
            file_bytes = io.BytesIO(self.rfile.read(content_length))
            self.data_dir.extract_tar_bytes(sub_path, file_bytes)
        except tarfile.TarError:
            return self.send_error(http.HTTPStatus.BAD_REQUEST, "Invalid tar archive")
        except Exception as e:
            return self.send_error(http.HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
        self.send_status_only(http.HTTPStatus.CREATED, f"Resource /{sub_path}/ updated")
        if self.headers["X-Host"]:
            self.registry.set_host(sub_path, self.headers["X-Host"])
        self.registry.add(sub_path)

    def do_DELETE(self):
        if self.headers["X-Token"] != self.token:
            return self.send_error(http.HTTPStatus.UNAUTHORIZED, "Invalid token")
        if (sub_path := self.get_subpath()) is None:
            return self.send_error(http.HTTPStatus.BAD_REQUEST, "Invalid path")
        if not self.data_dir.exists(sub_path):
            return self.send_error(http.HTTPStatus.NOT_FOUND, "Not found")
        try:
            self.data_dir.remove(sub_path)
        except Exception as e:
            return self.send_error(http.HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
        self.send_status_only(
            http.HTTPStatus.NO_CONTENT, f"Resource /{sub_path}/ removed"
        )
        self.registry.remove(sub_path)

    def get_subpath(self) -> str | None:
        if (match := re.match(r"^\/([\w-]+)\/$", self.path)) is not None:
            return match.group(1)
        return None

    def get_host(self) -> str:
        return self.headers["Host"].split(":")[0]

    def server_index(self):
        self.send_basic_body(self.server_version + "\n")

    def send_basic_body(
        self,
        body: str,
        content_type: str = "text/plain",
        code: int = http.HTTPStatus.OK,
        message: str | None = None,
    ):
        encoded: bytes = body.encode()
        self.send_response(code, message)
        self.send_header("Content-type", f"{content_type}; charset=UTF-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_status_only(self, code: int, message: str | None = None):
        self.send_response(code, message)
        self.send_header("Content-Length", "0")
        self.end_headers()
