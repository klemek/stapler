import http.server
import http
import tarfile
import re
import io
import os
import shutil

from . import project, params


class StaplerRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/2.0"
    server_version = "StaplerServer/" + project.get_version()

    def __init__(self, *args, params: params.Parameters, **kwargs):
        self.default_host = params.host
        self.token = params.token
        self.data_dir = params.data_dir
        self.max_size_bytes = params.max_size_bytes
        super().__init__(*args, directory=params.data_dir, **kwargs)

    def list_directory(self, *_, **__):
        """Disable default directory listing"""
        self.send_error(http.HTTPStatus.NOT_FOUND, "File not found")

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
            target_path = os.path.join(self.data_dir, sub_path)
            with tarfile.open(fileobj=file_bytes) as tar_file:
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)
                tar_file.extractall(os.path.join(self.data_dir, sub_path))
        except tarfile.TarError:
            return self.send_error(http.HTTPStatus.BAD_REQUEST, "Invalid tar archive")
        except Exception as e:
            return self.send_error(http.HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
        self.send_status_only(http.HTTPStatus.CREATED, f"Resource /{sub_path}/ updated")

    def do_DELETE(self):
        if self.headers["X-Token"] != self.token:
            return self.send_error(http.HTTPStatus.UNAUTHORIZED, "Invalid token")
        if (sub_path := self.get_subpath()) is None:
            return self.send_error(http.HTTPStatus.BAD_REQUEST, "Invalid path")
        target_path = os.path.join(self.data_dir, sub_path)
        try:
            shutil.rmtree(target_path)
        except Exception as e:
            return self.send_error(http.HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
        self.send_status_only(
            http.HTTPStatus.NO_CONTENT, f"Resource /{sub_path}/ deleted"
        )

    def get_subpath(self) -> str | None:
        if (match := re.match(r"^\/(\w+)\/$", self.path)) is not None:
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
