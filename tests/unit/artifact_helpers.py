from __future__ import annotations

import importlib
import io
import tarfile


def make_tar_zst(files: dict[str, str | bytes]) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as archive:
        for name, payload in files.items():
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
    return compress_zstd(tar_buffer.getvalue())


def compress_zstd(payload: bytes) -> bytes:
    try:
        zstd_module = importlib.import_module("compression.zstd")
    except ImportError:
        import zstandard

        return zstandard.ZstdCompressor().compress(payload)
    return zstd_module.compress(payload)
