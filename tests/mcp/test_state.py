"""Tests for ConversationState."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from specify_cli.mcp.session.state import ConversationState


def test_conversation_state_create(tmp_path):
    """Test that ConversationState.create() initializes correctly."""
    project_path = tmp_path / "project"
    workflow = "specify"
    
    state = ConversationState.create(project_path, workflow)
    
    assert state.session_id  # UUID generated
    assert state.project_path == project_path
    assert state.workflow == workflow
    assert state.phase == "discovery"
    assert state.questions_answered == {}
    assert state.questions_pending == []
    assert state.accumulated_context == {}
    assert state.created_at  # ISO timestamp
    assert state.updated_at  # ISO timestamp


def test_conversation_state_answer_question(tmp_path):
    """Test that answer_question() records answers correctly."""
    state = ConversationState.create(tmp_path, "specify")
    
    state.answer_question("q1", "answer1")
    
    assert state.questions_answered["q1"] == "answer1"


def test_conversation_state_answer_question_updates_timestamp(tmp_path):
    """Test that answer_question() updates timestamp."""
    state = ConversationState.create(tmp_path, "specify")
    original_timestamp = state.updated_at
    
    # Wait a tiny bit to ensure timestamp changes
    import time
    time.sleep(0.01)
    
    state.answer_question("q1", "answer1")
    
    assert state.updated_at > original_timestamp


def test_conversation_state_answer_question_removes_from_pending(tmp_path):
    """Test that answer_question() removes question from pending list."""
    state = ConversationState.create(tmp_path, "specify")
    
    state.add_pending_question("q1")
    assert "q1" in state.questions_pending
    
    state.answer_question("q1", "answer1")
    assert "q1" not in state.questions_pending


def test_conversation_state_add_pending_question(tmp_path):
    """Test that add_pending_question() adds to pending list."""
    state = ConversationState.create(tmp_path, "specify")
    
    state.add_pending_question("q1")
    
    assert "q1" in state.questions_pending


def test_conversation_state_add_pending_question_no_duplicates(tmp_path):
    """Test that add_pending_question() doesn't add duplicates."""
    state = ConversationState.create(tmp_path, "specify")
    
    state.add_pending_question("q1")
    state.add_pending_question("q1")
    
    assert state.questions_pending.count("q1") == 1


def test_conversation_state_set_phase(tmp_path):
    """Test that set_phase() updates phase correctly."""
    state = ConversationState.create(tmp_path, "specify")
    
    state.set_phase("validation")
    
    assert state.phase == "validation"


def test_conversation_state_add_context(tmp_path):
    """Test that add_context() stores context correctly."""
    state = ConversationState.create(tmp_path, "specify")
    
    state.add_context("feature_slug", "042-my-feature")
    state.add_context("mission", "software-dev")
    
    assert state.accumulated_context["feature_slug"] == "042-my-feature"
    assert state.accumulated_context["mission"] == "software-dev"


def test_conversation_state_to_json(tmp_path):
    """Test that to_json() produces valid JSON."""
    state = ConversationState.create(tmp_path / "project", "specify")
    state.answer_question("q1", "answer1")
    state.add_pending_question("q2")
    state.add_context("key", "value")
    
    json_str = state.to_json()
    
    # Should be valid JSON
    data = json.loads(json_str)
    
    assert data["session_id"] == state.session_id
    assert data["project_path"] == str(tmp_path / "project")
    assert data["workflow"] == "specify"
    assert data["questions_answered"] == {"q1": "answer1"}
    assert data["questions_pending"] == ["q2"]
    assert data["accumulated_context"] == {"key": "value"}


def test_conversation_state_from_json(tmp_path):
    """Test that from_json() reconstructs state correctly."""
    original = ConversationState.create(tmp_path / "project", "specify")
    original.answer_question("q1", "answer1")
    original.add_pending_question("q2")
    original.add_context("key", "value")
    
    json_str = original.to_json()
    
    reconstructed = ConversationState.from_json(json_str)
    
    assert reconstructed.session_id == original.session_id
    assert reconstructed.project_path == original.project_path
    assert reconstructed.workflow == original.workflow
    assert reconstructed.phase == original.phase
    assert reconstructed.questions_answered == original.questions_answered
    assert reconstructed.questions_pending == original.questions_pending
    assert reconstructed.accumulated_context == original.accumulated_context


def test_conversation_state_round_trip_serialization(tmp_path):
    """Test that serialization round-trip preserves all data."""
    original = ConversationState.create(tmp_path / "project", "tasks")
    original.answer_question("q1", {"nested": "dict"})
    original.answer_question("q2", ["list", "of", "values"])
    original.add_pending_question("q3")
    original.set_phase("generation")
    original.add_context("feature", "042-test")
    
    # Serialize and deserialize
    json_str = original.to_json()
    reconstructed = ConversationState.from_json(json_str)
    
    # Should be identical
    assert reconstructed.session_id == original.session_id
    assert reconstructed.project_path == original.project_path
    assert reconstructed.workflow == original.workflow
    assert reconstructed.phase == original.phase
    assert reconstructed.questions_answered == original.questions_answered
    assert reconstructed.questions_pending == original.questions_pending
    assert reconstructed.accumulated_context == original.accumulated_context
    assert reconstructed.created_at == original.created_at
    assert reconstructed.updated_at == original.updated_at


def test_conversation_state_save_to_file(tmp_path):
    """Test that save_to_file() writes JSON file correctly."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    
    state = ConversationState.create(tmp_path / "project", "specify")
    state.answer_question("q1", "answer1")
    
    state.save_to_file(session_dir)
    
    file_path = session_dir / f"{state.session_id}.json"
    assert file_path.exists()
    
    # Verify content
    content = file_path.read_text()
    data = json.loads(content)
    assert data["session_id"] == state.session_id


def test_conversation_state_load_from_file(tmp_path):
    """Test that load_from_file() reads JSON file correctly."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    
    # Save state
    original = ConversationState.create(tmp_path / "project", "specify")
    original.answer_question("q1", "answer1")
    original.save_to_file(session_dir)
    
    # Load state
    loaded = ConversationState.load_from_file(session_dir, original.session_id)
    
    assert loaded is not None
    assert loaded.session_id == original.session_id
    assert loaded.questions_answered == {"q1": "answer1"}


def test_conversation_state_load_from_file_missing(tmp_path):
    """Test that load_from_file() returns None for missing file."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    
    loaded = ConversationState.load_from_file(session_dir, "nonexistent-id")
    
    assert loaded is None


def test_conversation_state_load_from_file_corrupt_json(tmp_path):
    """Test that load_from_file() handles corrupt JSON gracefully."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    
    # Write corrupt JSON
    session_id = "corrupt-session"
    file_path = session_dir / f"{session_id}.json"
    file_path.write_text("not valid json {{{")
    
    loaded = ConversationState.load_from_file(session_dir, session_id)
    
    assert loaded is None


def test_conversation_state_resume_or_create_new(tmp_path):
    """Test that resume_or_create() creates new session if no ID provided."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    
    state = ConversationState.resume_or_create(
        session_dir, tmp_path / "project", "specify", session_id=None
    )
    
    assert state.session_id  # UUID generated
    assert state.workflow == "specify"
    assert state.phase == "discovery"


def test_conversation_state_resume_existing(tmp_path):
    """Test that resume_or_create() loads existing session."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    
    # Create and save initial state
    original = ConversationState.create(tmp_path / "project", "specify")
    original.answer_question("q1", "answer1")
    original.save_to_file(session_dir)
    
    # Resume session
    resumed = ConversationState.resume_or_create(
        session_dir, tmp_path / "project", "specify", session_id=original.session_id
    )
    
    assert resumed.session_id == original.session_id
    assert resumed.questions_answered == {"q1": "answer1"}


def test_conversation_state_resume_validates_workflow(tmp_path):
    """Test that resume_or_create() validates workflow matches."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    
    # Create session for "specify" workflow
    original = ConversationState.create(tmp_path / "project", "specify")
    original.save_to_file(session_dir)
    
    # Try to resume as "plan" workflow
    with pytest.raises(ValueError, match="is for workflow 'specify'"):
        ConversationState.resume_or_create(
            session_dir, tmp_path / "project", "plan", session_id=original.session_id
        )


def test_conversation_state_resume_missing_session(tmp_path):
    """Test that resume_or_create() raises error for missing session."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    
    with pytest.raises(FileNotFoundError, match="Session .* not found"):
        ConversationState.resume_or_create(
            session_dir, tmp_path / "project", "specify", session_id="nonexistent"
        )


def test_conversation_state_complex_answer_types(tmp_path):
    """Test that ConversationState handles complex answer types."""
    state = ConversationState.create(tmp_path / "project", "specify")
    
    # Test various data types
    state.answer_question("string", "answer")
    state.answer_question("int", 42)
    state.answer_question("bool", True)
    state.answer_question("list", ["a", "b", "c"])
    state.answer_question("dict", {"key": "value", "nested": {"data": 123}})
    state.answer_question("none", None)
    
    # Serialize and deserialize
    json_str = state.to_json()
    reconstructed = ConversationState.from_json(json_str)
    
    assert reconstructed.questions_answered["string"] == "answer"
    assert reconstructed.questions_answered["int"] == 42
    assert reconstructed.questions_answered["bool"] is True
    assert reconstructed.questions_answered["list"] == ["a", "b", "c"]
    assert reconstructed.questions_answered["dict"] == {"key": "value", "nested": {"data": 123}}
    assert reconstructed.questions_answered["none"] is None


def test_conversation_state_multiple_pending_questions(tmp_path):
    """Test that ConversationState handles multiple pending questions."""
    state = ConversationState.create(tmp_path / "project", "specify")
    
    # Add multiple pending questions
    for i in range(5):
        state.add_pending_question(f"q{i}")
    
    assert len(state.questions_pending) == 5
    
    # Answer some questions
    state.answer_question("q1", "a1")
    state.answer_question("q3", "a3")
    
    # Check pending list updated
    assert "q1" not in state.questions_pending
    assert "q3" not in state.questions_pending
    assert len(state.questions_pending) == 3
