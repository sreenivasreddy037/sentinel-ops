import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas import ApprovalDecision, TicketInput


def test_mock_modes_are_explicit():
    settings = Settings(_env_file=None, mock_llm=True, openai_api_key=None)
    assert settings.retrieval_backend == "mock"
    assert settings.qdrant_mode == "local"


def test_real_mode_requires_a_key():
    with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
        Settings(_env_file=None, mock_llm=False, openai_api_key=None)


def test_approval_cannot_coerce_strings_or_extra_fields():
    with pytest.raises(ValidationError):
        ApprovalDecision(approved="false")
    with pytest.raises(ValidationError):
        ApprovalDecision(approved=True, command="arbitrary")
    with pytest.raises(ValidationError):
        TicketInput(text="    " * 3)
