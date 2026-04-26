import hashlib
from dataclasses import dataclass
from typing import BinaryIO

class UploadValidationError(ValueError):
    pass


@dataclass
class UploadInfo:
    size: int
    sha256: str


def validate_html_upload(
    *,
    filename: str,
    stream: BinaryIO,
    max_bytes: int,
) -> UploadInfo:
    if not filename.lower().endswith(".html"):
        raise UploadValidationError(
            "invalid extension: only .html is allowed"
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

    stream.seek(0)
    return UploadInfo(size=size, sha256=h.hexdigest())
