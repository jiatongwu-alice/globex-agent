
import pytest

from app.memory import store
from app.memory.middleware import build_memory_context


#`tmp_path` is a temporary directory automatically created by pytest; I place the test database there to avoid contaminating the production `globex.sqlite3` file.

#`monkeypatch` is used to temporarily replace variables.

@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Create an isolated SQLite database for each test."""

    monkeypatch.setattr(
        store,
        "DB_PATH",
        tmp_path / "test.sqlite3"
    )

    store.init_db()

#Brand preferences can be saved and reloaded.
def test_brand_profile(test_db):
    """Verify brand preferences can be saved and loaded."""

    profile = {
        "target_market": "Germany",
        "category": "laptops",
        "budget_usd": 1500
    }

    store.save_brand_profile("brand_001", profile)

    result = store.load_brand_profile("brand_001")

    assert result == profile

#Saved preferences can be updated
def test_brand_profile_update(test_db):
    """Verify an existing brand profile can be updated."""

    store.save_brand_profile(
        "brand_001",
        {"target_market": "Germany"}
    )

    store.save_brand_profile(
        "brand_001",
        {"target_market": "France"}
    )

    result = store.load_brand_profile("brand_001")

    assert result["target_market"] == "France"

#Historical conversations can be read in sequential order.
def test_session_history(test_db):
    """Verify conversation history is saved in order."""

    store.save_message(
        "session_001",
        "user",
        "Research laptops."
    )

    store.save_message(
        "session_001",
        "assistant",
        "Found two laptops."
    )

    messages = store.load_recent_messages("session_001")

    assert len(messages) == 2
    assert messages[0]["content"] == "Research laptops."
    assert messages[1]["content"] == "Found two laptops."

#Memories from the database can enter the Supervisor's input context.
def test_memory_context(test_db):
    """Verify stored memory is included in the agent input."""

    store.save_brand_profile(
        "brand_001",
        {
            "target_market": "Germany",
            "budget_usd": 1500
        }
    )

    store.save_message(
        "session_001",
        "user",
        "Research laptop competitors."
    )

    context = build_memory_context(
        profile_id="brand_001",
        session_id="session_001",
        user_text="Compare their prices."
    )

    assert "Germany" in context
    assert "1500" in context
    assert "Research laptop competitors." in context
    assert "Compare their prices." in context
