"""ctypes bridge to the native .ink parser (native/libinkparser.so)."""
import ctypes
import os

from flask import current_app


class InkError(Exception):
    pass


class InkMeta(ctypes.Structure):
    # Must mirror ink_meta_t in native/ink_parser.h exactly.
    _fields_ = [
        ("title", ctypes.c_char * 64),
        ("is_published", ctypes.c_int32),
        ("author_id", ctypes.c_int32),
        ("tags", ctypes.c_char * 128),
    ]


_ERRORS = {
    -1: "Not a valid .ink file.",
    -2: "Title is too long (max 63 bytes).",
    -3: "Tags field is too long or malformed.",
}

_lib_cache = {}


def _load():
    path = current_app.config["NATIVE_LIB"]
    if path in _lib_cache:
        return _lib_cache[path]
    if not os.path.exists(path):
        raise InkError("Native parser is not built. Run: make -C native")
    lib = ctypes.CDLL(path)
    lib.ink_parse.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int32, ctypes.POINTER(InkMeta)]
    lib.ink_parse.restype = ctypes.c_int
    _lib_cache[path] = lib
    return lib


def parse_ink(data: bytes, uploader_id: int):
    """Return (meta_dict, body_text) or raise InkError."""
    lib = _load()
    meta = InkMeta()
    buf = ctypes.create_string_buffer(data, len(data))
    rc = lib.ink_parse(buf, len(data), uploader_id, ctypes.byref(meta))
    if rc < 0:
        raise InkError(_ERRORS.get(rc, f"Parser error {rc}."))
    result = {
        "title": meta.title.decode("utf-8", "replace").strip(),
        "tags": meta.tags.decode("utf-8", "replace").strip(),
        "is_published": int(meta.is_published),
        "author_id": int(meta.author_id),
    }
    body = data[rc:].decode("utf-8", "replace")
    return result, body
