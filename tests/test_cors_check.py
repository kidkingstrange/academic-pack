"""
Regression coverage for audit Low #39: CORS_ORIGINS defaults to localhost
only. A startup check now warns (never hard-fails — misconfigured CORS is
disruptive, not a leaked-credential emergency) if production is somehow
still running with only localhost/127.0.0.1 origins allowed.
"""
from types import SimpleNamespace

from backend.main import check_cors_configured_for_production


def test_warns_when_production_has_only_localhost_origins(capsys):
    settings = SimpleNamespace(
        APP_ENV="production",
        cors_origins_list=["http://localhost:3000", "http://127.0.0.1:5500"],
    )
    check_cors_configured_for_production(settings)
    assert "only localhost/127.0.0.1" in capsys.readouterr().out


def test_no_warning_when_production_has_a_real_domain(capsys):
    settings = SimpleNamespace(
        APP_ENV="production",
        cors_origins_list=["http://localhost:3000", "https://academic-pack.onrender.com"],
    )
    check_cors_configured_for_production(settings)
    assert capsys.readouterr().out == ""


def test_no_warning_outside_production(capsys):
    settings = SimpleNamespace(
        APP_ENV="development",
        cors_origins_list=["http://localhost:3000"],
    )
    check_cors_configured_for_production(settings)
    assert capsys.readouterr().out == ""
