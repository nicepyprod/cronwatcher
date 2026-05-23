"""Tests for JobDependencyStore and DependencyChecker."""

import pytest
from unittest.mock import MagicMock

from cronwatcher.job_dependencies import DependencyViolation, JobDependencyStore
from cronwatcher.dependency_checker import DependencyChecker


@pytest.fixture()
def store() -> JobDependencyStore:
    return JobDependencyStore()  # in-memory SQLite


# ---------------------------------------------------------------------------
# JobDependencyStore
# ---------------------------------------------------------------------------

class TestJobDependencyStore:
    def test_add_and_get_dependency(self, store):
        store.add_dependency("job_b", "job_a")
        assert store.get_dependencies("job_b") == ["job_a"]

    def test_get_dependencies_empty_when_none(self, store):
        assert store.get_dependencies("job_x") == []

    def test_add_is_idempotent(self, store):
        store.add_dependency("job_b", "job_a")
        store.add_dependency("job_b", "job_a")
        assert len(store.get_dependencies("job_b")) == 1

    def test_multiple_dependencies(self, store):
        store.add_dependency("job_c", "job_a")
        store.add_dependency("job_c", "job_b")
        deps = store.get_dependencies("job_c")
        assert set(deps) == {"job_a", "job_b"}

    def test_remove_dependency(self, store):
        store.add_dependency("job_b", "job_a")
        store.remove_dependency("job_b", "job_a")
        assert store.get_dependencies("job_b") == []

    def test_get_dependents(self, store):
        store.add_dependency("job_b", "job_a")
        store.add_dependency("job_c", "job_a")
        assert set(store.get_dependents("job_a")) == {"job_b", "job_c"}

    def test_all_dependencies(self, store):
        store.add_dependency("job_b", "job_a")
        store.add_dependency("job_c", "job_a")
        all_deps = store.all_dependencies()
        assert "job_b" in all_deps
        assert "job_c" in all_deps


# ---------------------------------------------------------------------------
# DependencyChecker
# ---------------------------------------------------------------------------

def _make_checker(dep_store, latest_run_map):
    run_store = MagicMock()
    run_store.latest_run.side_effect = lambda name: latest_run_map.get(name)
    return DependencyChecker(dep_store, run_store)


class TestDependencyChecker:
    def test_no_violations_when_no_deps(self, store):
        checker = _make_checker(store, {})
        assert checker.check("job_a") == []
        assert checker.is_satisfied("job_a") is True

    def test_violation_when_dep_never_run(self, store):
        store.add_dependency("job_b", "job_a")
        checker = _make_checker(store, {})
        violations = checker.check("job_b")
        assert len(violations) == 1
        assert "never run" in violations[0].reason

    def test_violation_when_dep_still_running(self, store):
        store.add_dependency("job_b", "job_a")
        checker = _make_checker(store, {"job_a": {"status": "running", "finished_at": None}})
        violations = checker.check("job_b")
        assert any("still running" in v.reason for v in violations)

    def test_violation_when_dep_failed(self, store):
        store.add_dependency("job_b", "job_a")
        checker = _make_checker(store, {"job_a": {"status": "failure", "finished_at": "2024-01-01"}})
        violations = checker.check("job_b")
        assert any("failure" in v.reason for v in violations)

    def test_no_violation_when_dep_succeeded(self, store):
        store.add_dependency("job_b", "job_a")
        checker = _make_checker(store, {"job_a": {"status": "success", "finished_at": "2024-01-01"}})
        assert checker.check("job_b") == []
        assert checker.is_satisfied("job_b") is True

    def test_violation_str(self, store):
        v = DependencyViolation("job_b", "job_a", "upstream job has never run")
        assert "job_b" in str(v)
        assert "job_a" in str(v)
