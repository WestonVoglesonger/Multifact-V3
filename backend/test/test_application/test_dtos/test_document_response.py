from datetime import datetime
from typing import Any, Dict
import pytest
from pydantic import ValidationError
from backend.application.dto.ni_document import DocumentResponse
from backend.test.test_application.test_dtos.fixtures import valid_document_data, valid_token_data


def test_document_response_valid(valid_document_data: Dict[str, Any]):
    doc = DocumentResponse(**valid_document_data)
    assert doc.id == 1
    assert doc.content == "Full NI content text"
    assert doc.version == "v1"
    assert doc.created_at == datetime(2023, 1, 1, 10, 0, 0)
    assert doc.updated_at == datetime(2023, 1, 1, 12, 0, 0)
    assert len(doc.tokens) == 1


def test_document_response_missing_id(valid_document_data: Dict[str, Any]):
    data = valid_document_data.copy()
    data.pop("id")
    with pytest.raises(ValidationError) as exc:
        DocumentResponse(**data)
    assert "id" in str(exc.value)


def test_document_response_tokens_empty(valid_document_data: Dict[str, Any]):
    data = valid_document_data.copy()
    data["tokens"] = []
    doc = DocumentResponse(**data)
    assert doc.tokens == []


def test_document_response_invalid_datetime(valid_document_data: Dict[str, Any]):
    data = valid_document_data.copy()
    data["created_at"] = "not-a-datetime"
    with pytest.raises(ValidationError) as exc:
        DocumentResponse(**data)
    assert "created_at" in str(exc.value)
