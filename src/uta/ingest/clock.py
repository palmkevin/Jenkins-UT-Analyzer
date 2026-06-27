"""Clock discipline — the single riskiest assumption in the system.

Two source clocks feed the analyzer and they are NOT the same:

* **Jenkins** emits epoch milliseconds in **UTC** (``timestamp``, ``startTimeMillis``).
* **Oracle ut_ref** stores ``CREDATIM`` / ``UPDDATIM`` as **naive local wall-clock**: the server
  OS clock runs on ``Europe/Luxembourg`` (UTC+2 in summer, +1 in winter) while ``DBTIMEZONE`` is
  ``+00:00``. The stored value therefore has no offset and means "local time".

Everything inside the app is stored and compared in **UTC, timezone-aware**. Convert at the edges:

* Jenkins millis  -> :func:`from_jenkins_millis`
* ut_ref naive    -> :func:`from_ut_ref_local`  (DST-aware via the named zone, never a fixed +2)
* app UTC -> ut_ref predicate -> :func:`to_ut_ref_local` (build the ``CREDATIM`` BETWEEN bounds)
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

# The ut_ref server clock. A named, DST-aware zone — deliberately NOT a fixed timedelta(+2),
# because a fixed offset is silently wrong across the DST boundary (e.g. late October / late March).
UT_REF_TZ = ZoneInfo("Europe/Luxembourg")


def from_jenkins_millis(millis: int) -> datetime:
    """Jenkins epoch-millis (UTC) -> timezone-aware UTC datetime."""
    return datetime.fromtimestamp(millis / 1000, tz=UTC)


def from_ut_ref_local(naive_local: datetime) -> datetime:
    """A naive ut_ref ``CREDATIM``/``UPDDATIM`` (Europe/Luxembourg wall-clock) -> aware UTC.

    The input must be naive (no tzinfo); attaching a tz to an already-aware value would be a
    bug, so we reject it loudly rather than silently mis-convert.
    """
    if naive_local.tzinfo is not None:
        raise ValueError("expected a naive ut_ref datetime (no tzinfo), got an aware one")
    return naive_local.replace(tzinfo=UT_REF_TZ).astimezone(UTC)


def to_ut_ref_local(aware_utc: datetime) -> datetime:
    """An aware UTC datetime -> naive Europe/Luxembourg wall-clock.

    Use this to turn an app-side UTC window into the ``CREDATIM`` bounds for an Oracle predicate,
    because ``CREDATIM`` is compared as naive local time.
    """
    if aware_utc.tzinfo is None:
        raise ValueError("expected an aware UTC datetime, got a naive one")
    return aware_utc.astimezone(UT_REF_TZ).replace(tzinfo=None)


def ensure_utc(dt: datetime) -> datetime:
    """Normalize any datetime to aware UTC. Naive input is assumed to already be UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
