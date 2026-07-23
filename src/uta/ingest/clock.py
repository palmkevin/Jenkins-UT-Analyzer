"""Clock discipline — the single riskiest assumption in the system.

Two source clocks feed the analyzer and they are NOT the same:

* **Jenkins** emits epoch milliseconds in **UTC** (``timestamp``, ``startTimeMillis``).
* **Oracle ut_ref** stores ``CREDATIM`` / ``UPDDATIM`` as **naive local wall-clock**: the server
  OS clock builds on ``Europe/Luxembourg`` (UTC+2 in summer, +1 in winter) while ``DBTIMEZONE`` is
  ``+00:00``. The stored value therefore has no offset and means "local time".

Everything inside the app is stored and compared in **UTC, timezone-aware**. Convert at the edges:

* Jenkins millis  -> :func:`from_jenkins_millis`
* ut_ref naive    -> :func:`from_ut_ref_local`  (DST-aware via the named zone, never a fixed +2)
* app UTC -> ut_ref predicate -> :func:`to_ut_ref_local_window_start` /
  :func:`to_ut_ref_local_window_end` (build the ``CREDATIM`` BETWEEN bounds fold-safely)

**The fall-back fold.** On the last Sunday of October the local wall clock repeats 02:00-03:00
(CEST then CET), so naive local time is non-monotonic in UTC: a row written at 00:40 UTC carries
``CREDATIM`` 02:40 while a *later* instant, 01:25 UTC, reads 02:25. A naive BETWEEN built by plain
conversion would exclude that earlier row. The window helpers below therefore widen the bounds
across the repeated hour — over-inclusion is safe (the caller's tolerance/lookback already widens
the window and correlation ranking tolerates extras); *exclusion* silently loses the culprit
data change.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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

    Two wall times per year need a documented, deterministic reading (``fold=0``, pinned
    explicitly rather than relied on as a default):

    * **Ambiguous** (fall-back night, 02:00-03:00 occurs twice): read as the *first* occurrence
      (CEST), i.e. the earlier UTC instant. Data changes precede the build and the lookback window
      reaches hours back, so erring early keeps a candidate inside its window; erring late could
      push it past the window end and lose it.
    * **Nonexistent** (spring-forward gap, 02:00-03:00 never happens — only possible from clock
      skew or bad data): read with the pre-transition offset (CET), landing just after the gap.
      Deterministic, never raises.
    """
    if naive_local.tzinfo is not None:
        raise ValueError("expected a naive ut_ref datetime (no tzinfo), got an aware one")
    return naive_local.replace(tzinfo=UT_REF_TZ, fold=0).astimezone(UTC)


def to_ut_ref_local(aware_utc: datetime) -> datetime:
    """An aware UTC datetime -> naive Europe/Luxembourg wall-clock (a point, not a bound).

    For ``CREDATIM`` BETWEEN bounds use :func:`to_ut_ref_local_window_start` /
    :func:`to_ut_ref_local_window_end` instead — a plain conversion is non-monotonic across the
    fall-back fold and can silently exclude in-window rows.
    """
    if aware_utc.tzinfo is None:
        raise ValueError("expected an aware UTC datetime, got a naive one")
    return aware_utc.astimezone(UT_REF_TZ).replace(tzinfo=None)


def _fold_gap(local_aware: datetime) -> timedelta:
    """How much wall-clock the fall-back fold repeats at this local time (0 outside it).

    ``astimezone`` output never lands in the spring-forward gap, so for our callers the
    fold-0/fold-1 offset difference is either the repeated hour or zero; the ``max`` guards the
    (unreachable) negative case anyway.
    """
    off_first = local_aware.replace(fold=0).utcoffset() or timedelta(0)
    off_second = local_aware.replace(fold=1).utcoffset() or timedelta(0)
    return max(off_first - off_second, timedelta(0))


def to_ut_ref_local_window_start(aware_utc: datetime) -> datetime:
    """An aware UTC window *start* -> naive local lower bound for a ``CREDATIM`` predicate.

    Identical to :func:`to_ut_ref_local` except during the repeated fall-back hour: a start in
    the first pass (CEST) is widened one hour earlier, because second-pass rows that really
    happened *after* it carry smaller naive values and a plain bound would exclude them.
    Over-inclusion (up to the repeated hour) is safe; exclusion loses candidates.
    """
    if aware_utc.tzinfo is None:
        raise ValueError("expected an aware UTC datetime, got a naive one")
    local = aware_utc.astimezone(UT_REF_TZ)
    naive = local.replace(tzinfo=None)
    if local.fold == 0:
        naive -= _fold_gap(local)  # zero outside the repeated hour
    return naive


def to_ut_ref_local_window_end(aware_utc: datetime) -> datetime:
    """An aware UTC window *end* -> naive local upper bound for a ``CREDATIM`` predicate.

    Identical to :func:`to_ut_ref_local` except during the repeated fall-back hour: an end in
    the second pass (CET) is widened one hour later, because first-pass rows that really happened
    *before* it carry larger naive values and a plain bound would exclude them (the issue-#87
    case: a change 45 minutes before the window end silently dropped).
    """
    if aware_utc.tzinfo is None:
        raise ValueError("expected an aware UTC datetime, got a naive one")
    local = aware_utc.astimezone(UT_REF_TZ)
    naive = local.replace(tzinfo=None)
    if local.fold == 1:
        naive += _fold_gap(local)  # zero outside the repeated hour
    return naive


def ensure_utc(dt: datetime) -> datetime:
    """Normalize any datetime to aware UTC. Naive input is assumed to already be UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
