"""Failure-signature normalization (the load-bearing component).

Two builds of the *same* bug almost never produce byte-identical error text: line numbers,
timestamps, object ids, temp paths, addresses and other dynamic values differ every time. If the
knowledge base keyed on the raw message nothing would ever match itself and the learning loop would
be dead. So before hashing we **normalize** the error into a stable shape by masking the noisy
parts, while keeping what identifies the bug: the **exception type** and the **top-N stack frames
of our own code**.

The signature = ``test identity + normalized text``; we also store a sha256 **hash** of it for
instant, index-backed exact-recurrence lookup. This module is deliberately small, ordered and
**unit-tested** because it single-handedly defines "the same failure" for recurrence,
prediction and flakiness grouping. The exact mask set is tunable:
too aggressive and distinct bugs collide; too timid and the same bug never recurs.

Medical-data invariant: only this normalized/redacted form is persisted — never the raw text.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

# Frames from *our* code — the Python UT tree (both tracks) and the in-tree test harness. We strip
# the track-specific path prefix so the same failure normalizes identically in ``permanent`` and
# ``permanent_py39`` (identity is test-level; track is only an attribute).
_OUR_FRAME_MARKERS = ("/tests/dev/", "/ls_unittest/", "/release/")
# Drop the volatile leading path so only the stable suffix (package/module) survives.
_TRACK_PREFIX = re.compile(r"^.*?/release/[^/]+/")

# A ``File "...", line N, in func`` traceback frame.
_FRAME = re.compile(r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+), in (?P<func>.+)$')

# The exception line closing a Python traceback: ``pkg.SomeError: message`` or bare ``SomeError``.
_EXC_TYPE = r"[A-Za-z_][\w.]*(?:Error|Exception|Warning|Exit|Interrupt|Timeout)"
_EXC_LINE = re.compile(rf"^(?P<type>{_EXC_TYPE})\b(?:: ?(?P<msg>.*))?$")

# Ordered value masks — MOST specific first so a broad mask never eats a narrow one (a UUID/IP must
# be caught before the bare-number mask turns its digits into ``<NUM>``).
_MASKS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
        ),
        "<UUID>",
    ),
    (
        re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"),
        "<TS>",
    ),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+\b"), "<IP>:<PORT>"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<IP>"),
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<HEX>"),
    (re.compile(r"\b\d+\b"), "<NUM>"),
)


@dataclass(frozen=True)
class NormalizedSignature:
    """The stable shape of a failure: normalized text + the kept exception type."""

    text: str
    exception_type: str | None


def _mask_values(text: str) -> str:
    for pattern, repl in _MASKS:
        text = pattern.sub(repl, text)
    return text


def _is_our_frame(path: str) -> bool:
    return any(marker in path for marker in _OUR_FRAME_MARKERS)


def _short_path(path: str) -> str:
    """Drop the volatile ``…/release/<track>/`` prefix so tracks normalize identically."""
    return _TRACK_PREFIX.sub("", path).lstrip("./")


def normalize(
    error_details: str | None,
    error_stack_trace: str | None,
    *,
    top_frames: int = 5,
) -> NormalizedSignature | None:
    """Normalize one failure into its stable signature, or ``None`` if there's nothing to key on.

    The normalized text is a compact, deterministic join of: the **exception type**, the **masked
    exception message**, and the **top-N frames of our own code** (path suffix + function, line
    masked). Everything dynamic (numbers, hex, timestamps, ips/ports, uuids, line numbers) is
    masked so the same bug hashes identically across builds and tracks.
    """
    stack = error_stack_trace or ""
    details = (error_details or "").strip()

    exc_type: str | None = None
    exc_msg = ""
    frames: list[str] = []

    for raw in stack.splitlines():
        frame = _FRAME.match(raw)
        if frame:
            if _is_our_frame(frame["path"]):
                frames.append(f"{_short_path(frame['path'])}:<LINE> in {frame['func'].strip()}")
            continue
        exc = _EXC_LINE.match(raw.strip())
        if exc:  # keep the LAST exception line — the actual raised type closes the traceback
            exc_type = exc["type"]
            exc_msg = (exc["msg"] or "").strip()

    # Prefer the exception message; fall back to the details field (often just "test failure").
    message = exc_msg or details
    parts: list[str] = []
    if exc_type:
        parts.append(exc_type)
    if message:
        parts.append(_mask_values(message))
    parts.extend(frames[:top_frames])

    if not parts:
        return None
    return NormalizedSignature(text="\n".join(parts), exception_type=exc_type)


def display_message(error_details: str | None, error_stack_trace: str | None) -> str | None:
    """The human-readable one-line failure summary — for **display**, never for keying.

    Returns the traceback's *closing* exception line (``AssertionError: values differ …``) when one
    exists — the same "last exception line wins" rule :func:`normalize` uses, so the snippet and
    the signature always describe the same failure — else the raw details field (JUnit
    ``errorDetails`` is usually just the constant "test failure", which is why the exception line
    is preferred). Unmasked: dynamic values stay readable; nothing derived from this is persisted.
    """
    line: str | None = None
    for raw in (error_stack_trace or "").splitlines():
        if _EXC_LINE.match(raw.strip()):
            line = raw.strip()
    if line:
        return line
    details = (error_details or "").strip()
    return details or None


def compute_hash(identity_name: str, normalized_text: str) -> str:
    """sha256 over ``identity + normalized text`` — the exact-recurrence key (index-backed)."""
    digest = hashlib.sha256()
    digest.update(identity_name.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(normalized_text.encode("utf-8"))
    return digest.hexdigest()
