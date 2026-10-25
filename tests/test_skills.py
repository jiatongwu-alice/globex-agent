
import pytest

from app.memory import store
from app.memory.middleware import build_memory_context


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    monkeypatch.setattr(
        store,
        "DB_PATH",
        tmp_path / "test.sqlite3"
    )
    store.init_db()


def test_save_and_load_skill(test_db):
    store.save_skill(
        "competitor_analysis",
        "Competitor Analysis",
        "Compare prices and positioning."
    )

    skill = store.load_skill("competitor_analysis")

    assert skill["title"] == "Competitor Analysis"
    assert "Compare prices" in skill["instructions"]


def test_skill_update(test_db):
    store.save_skill("skill_1", "Old", "Old workflow")
    store.save_skill("skill_1", "New", "New workflow")

    skill = store.load_skill("skill_1")

    assert skill["title"] == "New"
    assert skill["instructions"] == "New workflow"

#Injecting Skills into Agent Context
def test_skill_context_injection(test_db):
    store.save_skill(
        "competitor_analysis",
        "Competitor Analysis",
        "Identify missing evidence."
    )

    context = build_memory_context(
        profile_id="brand_001",
        session_id="session_001",
        user_text="Analyze two competitors.",
        skill_id="competitor_analysis"
    )

    assert "Identify missing evidence." in context
    assert "Analyze two competitors." in context

#Handling Non-existent Skills
def test_missing_skill(test_db):
    assert store.load_skill("nonexistent") is None

