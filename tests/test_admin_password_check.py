"""
Regression coverage for audit High #14: ADMIN_PASSWORD was left at its
shipped default in the live environment. A startup check now refuses to
boot in production with the default still set, and warns loudly otherwise.
"""
import pytest
from types import SimpleNamespace

from backend.main import check_admin_password_rotated
from backend.config import DEFAULT_ADMIN_PASSWORD


def test_refuses_to_start_in_production_with_default_password():
    settings = SimpleNamespace(ADMIN_PASSWORD=DEFAULT_ADMIN_PASSWORD, APP_ENV="production")
    with pytest.raises(RuntimeError):
        check_admin_password_rotated(settings)


def test_only_warns_in_development_with_default_password(capsys):
    settings = SimpleNamespace(ADMIN_PASSWORD=DEFAULT_ADMIN_PASSWORD, APP_ENV="development")
    check_admin_password_rotated(settings)  # must not raise
    assert "still the shipped default" in capsys.readouterr().out


def test_no_warning_once_password_is_rotated(capsys):
    settings = SimpleNamespace(ADMIN_PASSWORD="a-real-unique-password", APP_ENV="production")
    check_admin_password_rotated(settings)  # must not raise
    assert capsys.readouterr().out == ""
