"""The full Information model (PLAN.md §"Information model").

One module per concern; everything is re-exported here so callers can ``from uta.models import X``
and so importing this package registers every mapper on ``Base.metadata`` (Alembic autogenerate and
``create_all`` rely on that). The DB-level decisions:

- **Identity** is test-level; ``track`` is an attribute on the result (CLAUDE.md invariant).
- **actor** is a plain string on every human action (acknowledged_by / validated_by / entered_by /
  causing_person) — Phase-1 self-declared, Phase-2 Keycloak swaps the value with no model change;
  there is intentionally no ``users`` table.
- **Failure history** (§3) is the ``test_results`` rows across runs, not a separate table.
- Candidate **signals** are run-windowed (link to a run), not per-test, in v1.
"""

from __future__ import annotations

from uta.models.attribution import Attribution
from uta.models.classification import Classification
from uta.models.control import IngestJob, PollerHeartbeat, SettingOverride
from uta.models.enums import (
    AliasState,
    ChangeType,
    ErrorType,
    IngestJobStatus,
    LifecycleState,
    PredictedCause,
    Provenance,
    TriageStatus,
)
from uta.models.identity import TestIdentity
from uta.models.kb import FailureSignature
from uta.models.lifecycle import FailureEpisode, TestLifecycle
from uta.models.result import TestResult
from uta.models.run import Run, RunShard
from uta.models.signals import CodeChangeCandidate, DataChangeCandidate

__all__ = [
    # entities
    "Run",
    "RunShard",
    "TestIdentity",
    "TestResult",
    "TestLifecycle",
    "FailureEpisode",
    "Attribution",
    "Classification",
    "CodeChangeCandidate",
    "DataChangeCandidate",
    "FailureSignature",
    # operational (control panel, issue #16)
    "SettingOverride",
    "IngestJob",
    "PollerHeartbeat",
    # enums
    "AliasState",
    "ChangeType",
    "ErrorType",
    "IngestJobStatus",
    "LifecycleState",
    "PredictedCause",
    "Provenance",
    "TriageStatus",
]
