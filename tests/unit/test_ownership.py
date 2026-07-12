"""Owner = main developer, resolved from SVN blame (issue #114).

Covers the resolver in isolation (``resolve_for_cases`` with plain objects, ``resolve_all`` over a
seeded store) and its wiring into the ingest pipeline — all with a fake blame client, no `svn`.
"""

from __future__ import annotations

from sqlalchemy import select

from tests.fakes import FakeJenkinsClient, FakeSvnBlameClient
from uta.analyze.ownership import resolve_all, resolve_for_cases
from uta.db import session_scope
from uta.ingest.pipeline import ingest_build
from uta.ingest.ut_report import TestCaseResult
from uta.models import TestIdentity, TestResult


def _case(class_name: str, name: str, status: str, file_path: str | None) -> TestCaseResult:
    return TestCaseResult(
        track="permanent",
        suite_name="nose2-junit",
        class_name=class_name,
        name=name,
        status=status,
        duration=0.1,
        age=0,
        failed_since=0,
        error_details=None,
        error_stack_trace=None,
        file_path=file_path,
    )


def test_resolve_for_cases_sets_only_failing_tests_and_caches_per_file():
    a = TestIdentity(canonical_name="pkg.A.test_x")
    b = TestIdentity(canonical_name="pkg.B.test_y")
    identities = {"pkg.A.test_x": a, "pkg.B.test_y": b}
    cases = [
        _case("pkg.A", "test_x", "FAILED", "/opt/ls/release/permanent/tests/dev/pkg/a.py"),
        # a passing test carries no source path -> not blameable
        _case("pkg.B", "test_y", "PASSED", None),
        # a second failing test in the SAME file -> must not trigger a second blame call
        _case("pkg.A", "test_x2", "FAILED", "/opt/ls/release/permanent/tests/dev/pkg/a.py"),
    ]
    client = FakeSvnBlameClient(default="Dev One")

    resolved = resolve_for_cases(identities, cases, client)

    assert resolved == 1
    assert a.main_developer == "Dev One"
    assert b.main_developer is None
    # Cached per repo path: one blame for a.py despite two failing tests in it.
    assert client.calls == ["tests/dev/pkg/a.py"]


def test_resolve_for_cases_respects_existing_owner_unless_refresh():
    a = TestIdentity(canonical_name="pkg.A.test_x", main_developer="Old Owner")
    cases = [_case("pkg.A", "test_x", "FAILED", "/opt/ls/release/permanent/tests/dev/pkg/a.py")]
    client = FakeSvnBlameClient(default="New Owner")

    assert resolve_for_cases({"pkg.A.test_x": a}, cases, client) == 0
    assert a.main_developer == "Old Owner"
    assert client.calls == []  # already owned -> not re-blamed

    assert resolve_for_cases({"pkg.A.test_x": a}, cases, client, refresh=True) == 1
    assert a.main_developer == "New Owner"


def test_resolve_all_backfills_from_stored_source_paths(session_factory):
    ingest_build(FakeJenkinsClient(), session_factory, 1702, expected_shards=2)

    with session_scope(session_factory) as s:
        resolved = resolve_all(s, FakeSvnBlameClient(default="Blamed Dev"))
        assert resolved > 0
        # A failing test (source path known) is now owned; nothing was invented for path-less ones.
        owned = s.scalars(
            select(TestIdentity).where(TestIdentity.main_developer.is_not(None))
        ).all()
        assert owned
        assert all(o.main_developer == "Blamed Dev" for o in owned)
        # Every owned identity has at least one failing result with a source path.
        for o in owned:
            paths = s.scalars(
                select(TestResult.file_path).where(TestResult.test_identity_id == o.id)
            ).all()
            assert any(p for p in paths)

    # Idempotent: a second pass (only-missing) resolves nothing new.
    with session_scope(session_factory) as s:
        assert resolve_all(s, FakeSvnBlameClient(default="Blamed Dev")) == 0


def test_ingest_populates_main_developer_and_keeps_zephyr_owner():
    """Pipeline fills main_developer via blame while ZEPHYR owner stays honest ZEPHYR metadata."""
    from uta.db import Base, make_engine, make_session_factory

    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)

    ingest_build(
        FakeJenkinsClient(),
        factory,
        1702,
        expected_shards=2,
        svn_blame_client=FakeSvnBlameClient(default="A. Developer"),
    )

    with session_scope(factory) as s:
        # The known ZEPHYR-owned failing test: owner is now the (blamed) developer, and the ZEPHYR
        # author is preserved separately — not conflated into "owner".
        ident = s.scalar(
            select(TestIdentity).where(
                TestIdentity.canonical_name.like("%test_inpmode_alternativ_debitor_at_cust")
            )
        )
        assert ident is not None
        assert ident.main_developer == "A. Developer"
        assert ident.zephyr_owner == "kam"


def test_ingest_without_blame_client_leaves_owner_unresolved(session_factory):
    ingest_build(FakeJenkinsClient(), session_factory, 1702, expected_shards=2)
    with session_scope(session_factory) as s:
        assert (
            s.scalars(select(TestIdentity).where(TestIdentity.main_developer.is_not(None))).first()
            is None
        )
