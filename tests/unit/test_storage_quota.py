import pytest
from app.core.exceptions import AppError
from app.services.storage.storage_quota import validate_quota


def test_quota_accepts_available_space():
    validate_quota(10, 20, 31)


def test_quota_rejects_overflow():
    with pytest.raises(AppError) as exc:
        validate_quota(10, 22, 31)
    assert exc.value.code == "STORAGE_QUOTA_EXCEEDED"
