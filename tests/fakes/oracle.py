"""Fixtures-backed fake implementing the TrackingFeed protocol.

Mirrors the real feed's contract: it filters on the naive Europe/Luxembourg ``CREDATIM`` after
converting the aware-UTC window via :func:`uta.ingest.clock.to_ut_ref_local`, exactly as Oracle
would. The fixture rows carry no ``MODDATA`` (never committed).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from uta.ingest.clock import to_ut_ref_local
from uta.refdb.oracle import DataChange, _row_to_change

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "oracle" / "v_tracking_sample.json"


class FakeTrackingFeed:
    def __init__(self, fixture: Path = _FIXTURE) -> None:
        data = json.loads(fixture.read_text())
        self._rows: list[dict] = []
        for row in data["rows"]:
            r = dict(row)
            r["CREDATIM"] = datetime.fromisoformat(r["CREDATIM"])
            if r.get("UPDDATIM"):
                r["UPDDATIM"] = datetime.fromisoformat(r["UPDDATIM"])
            self._rows.append(r)

    def changes_in_window(self, start_utc: datetime, end_utc: datetime) -> list[DataChange]:
        lo = to_ut_ref_local(start_utc)
        hi = to_ut_ref_local(end_utc)
        rows = [r for r in self._rows if lo <= r["CREDATIM"] <= hi]
        rows.sort(key=lambda r: r["CREDATIM"])
        return [_row_to_change(r) for r in rows]
