"""Tests for job_priority module."""
import pytest

from cronwatcher.job_priority import JobPriorityStore, Priority


@pytest.fixture
def store() -> JobPriorityStore:
    return JobPriorityStore(db_path=":memory:")


class TestPriorityEnum:
    def test_from_string_valid(self):
        assert Priority.from_string("high") == Priority.HIGH
        assert Priority.from_string("CRITICAL") == Priority.CRITICAL
        assert Priority.from_string("  low  ") == Priority.LOW

    def test_from_string_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown priority"):
            Priority.from_string("urgent")

    def test_ordering(self):
        assert Priority.LOW < Priority.NORMAL < Priority.HIGH < Priority.CRITICAL

    def test_label(self):
        assert Priority.CRITICAL.label() == "Critical"
        assert Priority.LOW.label() == "Low"


class TestJobPriorityStore:
    def test_default_priority_is_normal(self, store):
        assert store.get_priority("backup") == Priority.NORMAL

    def test_set_and_get(self, store):
        store.set_priority("deploy", Priority.CRITICAL)
        assert store.get_priority("deploy") == Priority.CRITICAL

    def test_overwrite_priority(self, store):
        store.set_priority("cleanup", Priority.HIGH)
        store.set_priority("cleanup", Priority.LOW)
        assert store.get_priority("cleanup") == Priority.LOW

    def test_all_entries_sorted_by_priority_desc(self, store):
        store.set_priority("a", Priority.LOW)
        store.set_priority("b", Priority.CRITICAL)
        store.set_priority("c", Priority.NORMAL)
        entries = store.all_entries()
        priorities = [e.priority for e in entries]
        assert priorities == sorted(priorities, reverse=True)

    def test_sorted_by_priority_orders_correctly(self, store):
        store.set_priority("low_job", Priority.LOW)
        store.set_priority("crit_job", Priority.CRITICAL)
        store.set_priority("norm_job", Priority.NORMAL)
        result = store.sorted_by_priority(["low_job", "crit_job", "norm_job"])
        assert result[0] == "crit_job"
        assert result[-1] == "low_job"

    def test_sorted_by_priority_unknown_job_defaults_to_normal(self, store):
        store.set_priority("high_job", Priority.HIGH)
        result = store.sorted_by_priority(["unknown_job", "high_job"])
        assert result[0] == "high_job"
