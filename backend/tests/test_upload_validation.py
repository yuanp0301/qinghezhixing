from io import BytesIO

import pytest

from app.services.upload_validation import (
    UploadValidationError,
    validate_html_upload,
)


def _bytes_io(b: bytes) -> BytesIO:
    s = BytesIO(b)
    return s


def test_accept_minimal_html():
    body = b"<!DOCTYPE html><html><body>ok</body></html>"
    info = validate_html_upload(
        filename="a.html",
        stream=_bytes_io(body),
        max_bytes=10_000,
    )
    assert info.size == len(body)
    assert info.sha256 and len(info.sha256) == 64


def test_reject_wrong_extension():
    with pytest.raises(UploadValidationError, match="extension"):
        validate_html_upload(
            filename="a.pdf",
            stream=_bytes_io(b"<html></html>"),
            max_bytes=1000,
        )


def test_accept_any_content_bytes_if_extension_ok():
    info = validate_html_upload(
        filename="a.html",
        stream=_bytes_io(b"%PDF-1.4 fake fake"),
        max_bytes=1000,
    )
    assert info.size > 0


def test_reject_too_large():
    with pytest.raises(UploadValidationError, match="size"):
        validate_html_upload(
            filename="a.html",
            stream=_bytes_io(b"x" * 2000),
            max_bytes=1000,
        )
