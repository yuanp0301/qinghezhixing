from types import SimpleNamespace
from unittest.mock import patch

from app.oss import storage


class StubBucket:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.deleted: list[str] = []

    def put_object(self, key, data, headers=None):
        body = data.read() if hasattr(data, "read") else data
        ct = (headers or {}).get("Content-Type", "")
        self.objects[key] = (body, ct)
        return SimpleNamespace(etag="etag-" + key, request_id="req-1")

    def get_object(self, key):
        body, _ = self.objects[key]
        return StubObject(body)

    def delete_object(self, key):
        self.deleted.append(key)
        self.objects.pop(key, None)


class StubObject:
    def __init__(self, body: bytes) -> None:
        self._body = body
        self._pos = 0
        self.closed = False

    def read(self, n: int = -1) -> bytes:
        if n < 0 or n >= len(self._body) - self._pos:
            chunk = self._body[self._pos:]
            self._pos = len(self._body)
        else:
            chunk = self._body[self._pos:self._pos + n]
            self._pos += n
        return chunk

    def close(self) -> None:
        self.closed = True


def test_put_object_returns_etag():
    bucket = StubBucket()
    with patch("app.oss.storage.make_bucket", return_value=bucket):
        import io

        result = storage.put_object(
            "contents/2026/04/x.html",
            io.BytesIO(b"<html></html>"),
            "text/html; charset=utf-8",
        )
    assert result["etag"] == "etag-contents/2026/04/x.html"
    assert result["request_id"] == "req-1"
    body, ct = bucket.objects["contents/2026/04/x.html"]
    assert body == b"<html></html>"
    assert ct == "text/html; charset=utf-8"


def test_stream_object_yields_chunks_and_closes():
    bucket = StubBucket()
    bucket.objects["k.html"] = (b"abcdef", "text/html")
    with patch("app.oss.storage.make_bucket", return_value=bucket):
        chunks = list(storage.stream_object("k.html"))
    assert b"".join(chunks) == b"abcdef"


def test_stream_object_large_body_chunked():
    bucket = StubBucket()
    body = b"x" * (64 * 1024 * 2 + 10)
    bucket.objects["big.html"] = (body, "text/html")
    with patch("app.oss.storage.make_bucket", return_value=bucket):
        chunks = list(storage.stream_object("big.html"))
    assert b"".join(chunks) == body
    assert len(chunks) >= 3


def test_delete_object():
    bucket = StubBucket()
    bucket.objects["k.html"] = (b"x", "text/html")
    with patch("app.oss.storage.make_bucket", return_value=bucket):
        storage.delete_object("k.html")
    assert "k.html" in bucket.deleted
    assert "k.html" not in bucket.objects


def test_put_object_accepts_bytes_like():
    bucket = StubBucket()
    with patch("app.oss.storage.make_bucket", return_value=bucket):
        import io

        storage.put_object(
            "y.html", io.BytesIO(b"hello"), "text/html"
        )
    body, _ = bucket.objects["y.html"]
    assert body == b"hello"
