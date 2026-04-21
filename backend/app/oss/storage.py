from collections.abc import Iterator
from typing import BinaryIO

from app.oss.client import make_bucket


def put_object(
    object_key: str, data: BinaryIO, content_type: str
) -> dict:
    bucket = make_bucket()
    headers = {"Content-Type": content_type}
    resp = bucket.put_object(object_key, data, headers=headers)
    return {
        "etag": resp.etag,
        "request_id": resp.request_id,
    }


def stream_object(object_key: str) -> Iterator[bytes]:
    bucket = make_bucket()
    obj = bucket.get_object(object_key)
    try:
        while True:
            chunk = obj.read(64 * 1024)
            if not chunk:
                break
            yield chunk
    finally:
        obj.close()


def delete_object(object_key: str) -> None:
    bucket = make_bucket()
    bucket.delete_object(object_key)
