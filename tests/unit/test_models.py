import pytest

from mycmd.core.models import ValidationError, validate


def test_url_control_characters_are_rejected():
    with pytest.raises(ValidationError):
        validate(
            "certificates",
            {"name": "Name", "issuer": "Issuer", "credential_url": "https://example.com/\x00bad"},
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"title": ""},
        {"status": "fake"},
        {"slug": "../bad"},
        {"links": ["javascript:alert(1)"]},
        {"started_at": "2026-02-30"},
        {"started_at": "2026-02-02", "finished_at": "2025-01-01"},
        {"owner_id": "injected"},
        {"title": 123},
        {"title": "x" * 201},
        {"technologies": None},
    ],
)
def test_project_invalid(changes):
    with pytest.raises(ValidationError):
        validate("projects", {"slug": "valid", "title": "Title", "status": "active"} | changes)


def test_milestone_completion_and_certificate_dates():
    with pytest.raises(ValidationError):
        validate("milestones", {"title": "Ship", "priority": "high", "status": "completed"})
    with pytest.raises(ValidationError):
        validate(
            "certificates",
            {
                "name": "Name",
                "issuer": "Issuer",
                "issued_at": "2026-01-01",
                "expires_at": "2025-01-01",
            },
        )
