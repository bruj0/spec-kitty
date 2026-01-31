"""Conversation state management for multi-turn discovery interviews."""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ConversationState:
    """
    Persists state for multi-turn discovery interview sessions.
    
    Each workflow (specify, plan, tasks) has its own interview with specific
    questions. This state tracks which questions have been answered, pending
    questions, and accumulated context across the conversation.
    """
    
    session_id: str
    project_path: Path
    workflow: str  # "specify", "plan", "tasks", etc.
    phase: str  # Current interview phase
    questions_answered: Dict[str, Any] = field(default_factory=dict)
    questions_pending: List[str] = field(default_factory=list)
    accumulated_context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    
    @classmethod
    def create(cls, project_path: Path, workflow: str) -> "ConversationState":
        """
        Create a new conversation state.
        
        Args:
            project_path: Path to Spec Kitty project
            workflow: Workflow identifier (specify, plan, tasks, etc.)
            
        Returns:
            New ConversationState instance
        """
        now = datetime.now(timezone.utc).isoformat()
        session_id = str(uuid.uuid4())
        
        return cls(
            session_id=session_id,
            project_path=project_path,
            workflow=workflow,
            phase="discovery",
            created_at=now,
            updated_at=now
        )
    
    def answer_question(self, question_id: str, answer: Any):
        """
        Record answer to a question.
        
        Args:
            question_id: Question identifier
            answer: User's answer (string, int, list, dict, etc.)
        """
        self.questions_answered[question_id] = answer
        self.updated_at = datetime.now(timezone.utc).isoformat()
        
        # Remove from pending if it was there
        if question_id in self.questions_pending:
            self.questions_pending.remove(question_id)
    
    def add_pending_question(self, question_id: str):
        """
        Add a question to the pending list.
        
        Args:
            question_id: Question identifier
        """
        if question_id not in self.questions_pending:
            self.questions_pending.append(question_id)
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def set_phase(self, phase: str):
        """
        Update current interview phase.
        
        Args:
            phase: Phase identifier (discovery, validation, generation, etc.)
        """
        self.phase = phase
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def add_context(self, key: str, value: Any):
        """
        Add context accumulated during conversation.
        
        Args:
            key: Context key
            value: Context value (must be JSON-serializable)
        """
        self.accumulated_context[key] = value
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def to_json(self) -> str:
        """
        Serialize to JSON string (T011).
        
        Returns:
            JSON string representation
        """
        data = {
            "session_id": self.session_id,
            "project_path": str(self.project_path),  # Convert Path to string
            "workflow": self.workflow,
            "phase": self.phase,
            "questions_answered": self.questions_answered,
            "questions_pending": self.questions_pending,
            "accumulated_context": self.accumulated_context,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        return json.dumps(data, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ConversationState":
        """
        Deserialize from JSON string (T011).
        
        Args:
            json_str: JSON string representation
            
        Returns:
            ConversationState instance
            
        Raises:
            json.JSONDecodeError: If JSON is invalid
            KeyError: If required fields are missing
        """
        data = json.loads(json_str)
        
        return cls(
            session_id=data["session_id"],
            project_path=Path(data["project_path"]),
            workflow=data["workflow"],
            phase=data["phase"],
            questions_answered=data.get("questions_answered", {}),
            questions_pending=data.get("questions_pending", []),
            accumulated_context=data.get("accumulated_context", {}),
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )
    
    def save_to_file(self, session_dir: Path):
        """
        Save state to JSON file (uses atomic write from T012).
        
        Args:
            session_dir: Directory where session files are stored
        """
        from .persistence import atomic_write
        
        file_path = session_dir / f"{self.session_id}.json"
        atomic_write(file_path, self.to_json())
    
    @classmethod
    def load_from_file(cls, session_dir: Path, session_id: str) -> Optional["ConversationState"]:
        """
        Load state from JSON file.
        
        Args:
            session_dir: Directory where session files are stored
            session_id: Session identifier
            
        Returns:
            ConversationState instance or None if file doesn't exist or is corrupt
        """
        file_path = session_dir / f"{session_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r") as f:
                json_str = f.read()
            
            return cls.from_json(json_str)
        except (json.JSONDecodeError, KeyError) as e:
            # Log error but don't crash
            print(f"Warning: Failed to load session {session_id}: {e}")
            return None
    
    @classmethod
    def resume_or_create(
        cls,
        session_dir: Path,
        project_path: Path,
        workflow: str,
        session_id: Optional[str] = None
    ) -> "ConversationState":
        """
        Resume existing session or create new one (T013).
        
        Args:
            session_dir: Directory where session files are stored
            project_path: Path to Spec Kitty project
            workflow: Workflow identifier
            session_id: Optional session ID to resume
            
        Returns:
            ConversationState instance (existing or new)
            
        Raises:
            FileNotFoundError: If session_id provided but file not found
            ValueError: If session workflow doesn't match requested workflow
        """
        if session_id:
            # Try to load existing session
            state = cls.load_from_file(session_dir, session_id)
            
            if state:
                # Validate workflow matches
                if state.workflow != workflow:
                    raise ValueError(
                        f"Session {session_id} is for workflow '{state.workflow}', "
                        f"not '{workflow}'"
                    )
                
                return state
            
            # Session ID provided but file not found
            raise FileNotFoundError(
                f"Session {session_id} not found in {session_dir}"
            )
        
        # No session ID provided, create new session
        return cls.create(project_path, workflow)
