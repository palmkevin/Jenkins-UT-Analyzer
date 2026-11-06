"""Process-wide logging tweaks shared by the CLI entrypoints and the web app factory."""

from __future__ import annotations

import logging

#: Third-party loggers pinned to WARNING. ``httpx`` logs ``HTTP Request: POST <full URL>`` at INFO
#: on every request — and the Teams webhook URL carries its auth token in the ``sig=`` query
#: parameter, so at INFO (``uta poll`` / ``uta web`` set the root there) every alert would write
#: the secret to the logs. ``httpcore`` is pinned alongside it for the same reason (its DEBUG/INFO
#: traces can echo request lines too).
_QUIETED_LOGGERS = ("httpx", "httpcore")


def quiet_http_client_loggers() -> None:
    """Raise the HTTP-client loggers to WARNING so request URLs (and secrets) are not logged."""
    for name in _QUIETED_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
