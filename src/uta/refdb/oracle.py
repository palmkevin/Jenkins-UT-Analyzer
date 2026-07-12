"""Oracle ``ut_ref`` read-only access — the V_TRACKING data-change feed.

``V_TRACKING`` is a consolidated view (author already resolved as ``USRCODE``). Its ``CREDATIM`` is
naive **Europe/Luxembourg** wall-clock, so a UTC app-side window is converted with the fold-safe
:func:`uta.ingest.clock.to_ut_ref_local_window_start` / ``…_window_end`` pair before it becomes a
``CREDATIM BETWEEN`` predicate (a plain conversion would drop rows across the fall-back fold).

The :class:`TrackingFeed` protocol is the seam: production uses :class:`OracleTrackingFeed`
(``oracledb`` thin), the offline suite uses a fixtures-backed fake. ``MODDATA`` is intentionally
**not** selected — it carries raw LIMS/patient data and is never needed for candidate correlation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from uta.ingest.clock import (
    from_ut_ref_local,
    to_ut_ref_local_window_end,
    to_ut_ref_local_window_start,
)

# MODDATA deliberately excluded (raw medical data).
_COLUMNS = (
    "SESSIONLOGID",
    "LXTABLECODE",
    "PKLST",
    "LXTABLECODEREF",
    "PKLSTREF",
    "TYPE",
    "COMPONENTNAME",
    "CREDATIM",
    "UPDDATIM",
    "USRIDCRE",
    "USRCODE",
)

_QUERY = (
    f"SELECT {', '.join(_COLUMNS)} FROM V_TRACKING "  # noqa: S608 - fixed column allowlist
    "WHERE CREDATIM BETWEEN :win_start AND :win_end ORDER BY CREDATIM"
)


@dataclass(frozen=True)
class DataChange:
    session_log_id: int | None
    entity: str  # LXTABLECODE
    pk: str  # PKLST
    entity_ref: str | None
    pk_ref: str | None
    change_type: str  # normalized C / U / D
    component: str | None
    cre_utc: datetime  # aware UTC (converted from naive Europe/Luxembourg CREDATIM)
    upd_utc: datetime | None
    user_id: int | None
    user_code: str | None


class TrackingFeed(Protocol):
    def changes_in_window(self, start_utc: datetime, end_utc: datetime) -> list[DataChange]: ...


def _row_to_change(row: dict) -> DataChange:
    cre = row["CREDATIM"]
    upd = row.get("UPDDATIM")
    return DataChange(
        session_log_id=row.get("SESSIONLOGID"),
        entity="" if row.get("LXTABLECODE") is None else str(row["LXTABLECODE"]),
        pk="" if row.get("PKLST") is None else str(row["PKLST"]),
        entity_ref=row.get("LXTABLECODEREF"),
        pk_ref=None if row.get("PKLSTREF") is None else str(row["PKLSTREF"]),
        change_type="" if row.get("TYPE") is None else str(row["TYPE"]),
        component=row.get("COMPONENTNAME"),
        cre_utc=from_ut_ref_local(cre),
        upd_utc=from_ut_ref_local(upd) if upd is not None else None,
        user_id=row.get("USRIDCRE"),
        user_code=row.get("USRCODE"),
    )


class OracleTrackingFeed:
    """Live read-only feed via ``oracledb`` (thin mode by default)."""

    def __init__(
        self, host: str, port: int, service: str, user: str, password: str, *, thick: bool = False
    ) -> None:
        import oracledb

        if thick:
            oracledb.init_oracle_client()
        self._oracledb = oracledb
        self._dsn = oracledb.makedsn(host, port, service_name=service)
        self._user = user
        self._password = password

    def changes_in_window(self, start_utc: datetime, end_utc: datetime) -> list[DataChange]:
        win_start = to_ut_ref_local_window_start(start_utc)
        win_end = to_ut_ref_local_window_end(end_utc)
        with self._oracledb.connect(
            user=self._user, password=self._password, dsn=self._dsn
        ) as conn:
            cur = conn.cursor()
            cur.execute(_QUERY, win_start=win_start, win_end=win_end)
            col_names = [d[0] for d in cur.description]
            return [_row_to_change(dict(zip(col_names, r, strict=True))) for r in cur.fetchall()]
