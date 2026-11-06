import tempfile
from pathlib import Path

from src.utils import compute_dropbox_content_hash


class FakeResponse:
    def __init__(
        self,
        data: bytes,
        status_code: int = 200,
        headers: dict | None = None,
        fail_after: int | None = None,
        on_chunk=None,
    ):
        self.data = data
        self.status_code = status_code
        self.headers = headers or {}
        self.fail_after = fail_after
        self.on_chunk = on_chunk
        self.closed = False

    def iter_content(self, chunk_size: int = 131072):
        offset = 0
        while offset < len(self.data):
            if self.fail_after is not None and offset >= self.fail_after:
                raise ConnectionError("simulated network drop")
            chunk = self.data[offset : offset + chunk_size]
            offset += len(chunk)
            if self.on_chunk:
                self.on_chunk(offset)
            yield chunk

    def close(self):
        self.closed = True


class FakeMetadata:
    def __init__(self, name: str = "SharedRoot", content_hash: str | None = None):
        self.name = name
        self.content_hash = content_hash


class FakeDbx:
    def __init__(self, handler=None):
        self._headers: dict[str, str] = {}
        self.handler = handler
        self.seen_ranges: list[str | None] = []
        self.responses: list[FakeResponse] = []

    def users_get_current_account(self):
        class _Name:
            display_name = "Test User"

        class _Acc:
            name = _Name()
            email = "test@example.com"

        return _Acc()

    def sharing_get_shared_link_metadata(self, **kwargs):
        return FakeMetadata("SharedRoot")

    def sharing_get_shared_link_file(self, **kwargs):
        rng = self._headers.get("Range")
        self.seen_ranges.append(rng)
        meta, resp = self.handler(rng, kwargs, len(self.seen_ranges))
        self.responses.append(resp)
        return meta, resp


def make_payload(size: int, seed: bytes = b"0123456789ABCDEF") -> tuple[bytes, str]:
    data = (seed * ((size // len(seed)) + 1))[:size]
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(data)
        p = Path(tf.name)
    try:
        content_hash = compute_dropbox_content_hash(p)
    finally:
        p.unlink(missing_ok=True)
    return data, content_hash

