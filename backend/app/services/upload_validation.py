import hashlib
import re
from dataclasses import dataclass
from typing import BinaryIO

_HTML_SNIFF_RE = re.compile(
    rb"^\s*(<!doctype\s+html|<html|<head|<body|<meta|<script|<svg)",
    re.IGNORECASE,
)


class UploadValidationError(ValueError):
    pass


@dataclass
class UploadInfo:
    size: int
    sha256: str


def validate_html_upload(
    *,
    filename: str,
    content_type: str,
    stream: BinaryIO,
    max_bytes: int,
) -> UploadInfo:
    if not filename.lower().endswith(".html"):
        raise UploadValidationError(
            "invalid extension: only .html is allowed"
        )
    if content_type not in {"text/html", "text/html; charset=utf-8"}:
        raise UploadValidationError(
            f"invalid mime: got {content_type!r}, expect text/html"
        )

    stream.seek(0)
    head = stream.read(512)

    h = hashlib.sha256()
    h.update(head)
    size = len(head)
    if size > max_bytes:
        raise UploadValidationError(
            f"size exceeded: > {max_bytes} bytes"
        )
    while True:
        chunk = stream.read(64 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise UploadValidationError(
                f"size exceeded: > {max_bytes} bytes"
            )
        h.update(chunk)

    if not _HTML_SNIFF_RE.search(head):
        raise UploadValidationError(
            "invalid content: file does not look like HTML"
        )

    stream.seek(0)
    return UploadInfo(size=size, sha256=h.hexdigest())
