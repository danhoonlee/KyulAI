"""Opening prefixes for a public demonstration must stay narrow and metered.

Two properties matter. The open set is decided by path prefix, not by
entitlement, because `module.laminate` gates the RAG assistant as well as the
laminate API and the assistant spends money per question. And a request that
arrives with no session still has to hit a rate limit, because before this
change anonymous requests returned no rules at all -- they were never reached,
since the entitlement check rejected them first.
"""

from __future__ import annotations

import pytest
from fastapi import Request

from src.backend.security import module_access, request_limits

LAMINATE = "/api/v1/dd-laminate"
INJECTION = "/api/v1/simple-injection"
RAG = "/api/v1/rag"


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(module_access.PUBLIC_DEMO_PATHS_ENV, raising=False)
    monkeypatch.delenv(module_access.PUBLIC_DEMO_HOSTS_ENV, raising=False)
    monkeypatch.setenv(module_access.ENVIRONMENT_ENV, "production")
    yield


DEMO_HOST = "laminate.imperialax.com"
FRONT_DOOR = "ai.imperialax.com"


def _request(path: str, method: str = "POST", host: str = DEMO_HOST) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", host.encode())],
            "client": ("203.0.113.9", 12345),
            "server": (host, 443),
        }
    )


def test_closed_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the variable unset nothing is public."""
    assert module_access.public_demo_paths() == ()
    for path in (LAMINATE, INJECTION, RAG):
        assert module_access.is_public_demo_path(path) is False
    denial = module_access.module_access_denial(
        _request(f"{LAMINATE}/predict/response"), "module.laminate", "Laminate"
    )
    assert denial is not None
    assert denial.status_code == 401


def test_only_listed_prefixes_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(module_access.PUBLIC_DEMO_PATHS_ENV, f"{LAMINATE},{INJECTION}")
    monkeypatch.setenv(module_access.PUBLIC_DEMO_HOSTS_ENV, DEMO_HOST)

    for path in (f"{LAMINATE}/predict/response", f"{INJECTION}/predict"):
        assert (
            module_access.module_access_denial(_request(path), "module.laminate", "Laminate")
            is None
        )

    # Same entitlement, different prefix: the assistant stays closed.
    denial = module_access.module_access_denial(
        _request(f"{RAG}/ask"), "module.laminate", "Laminate Assistant"
    )
    assert denial is not None
    assert denial.status_code == 401


def test_the_front_door_stays_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """One process answers for both names; only the demo host may skip the check."""
    monkeypatch.setenv(module_access.PUBLIC_DEMO_PATHS_ENV, LAMINATE)
    monkeypatch.setenv(module_access.PUBLIC_DEMO_HOSTS_ENV, DEMO_HOST)
    path = f"{LAMINATE}/predict/response"

    assert (
        module_access.module_access_denial(
            _request(path, host=DEMO_HOST), "module.laminate", "Laminate"
        )
        is None
    )
    denial = module_access.module_access_denial(
        _request(path, host=FRONT_DOOR), "module.laminate", "Laminate"
    )
    assert denial is not None
    assert denial.status_code == 401
    assert request_limits._rules_for_request(_request(path, host=FRONT_DOOR)) == []


def test_paths_without_hosts_open_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Half the configuration is not a half-open door."""
    monkeypatch.setenv(module_access.PUBLIC_DEMO_PATHS_ENV, LAMINATE)
    denial = module_access.module_access_denial(
        _request(f"{LAMINATE}/predict/response"), "module.laminate", "Laminate"
    )
    assert denial is not None
    assert denial.status_code == 401


def test_whitespace_and_empty_entries_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(module_access.PUBLIC_DEMO_PATHS_ENV, f" {LAMINATE} , ,{INJECTION}, ")
    monkeypatch.setenv(module_access.PUBLIC_DEMO_HOSTS_ENV, f" {DEMO_HOST} , , ")
    assert module_access.public_demo_paths() == (LAMINATE, INJECTION)
    assert module_access.public_demo_hosts() == frozenset({DEMO_HOST})


def test_open_prefixes_are_rate_limited_without_a_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The gap this change had to close: anonymous requests used to get no rules."""
    monkeypatch.setenv(module_access.PUBLIC_DEMO_PATHS_ENV, LAMINATE)
    monkeypatch.setenv(module_access.PUBLIC_DEMO_HOSTS_ENV, DEMO_HOST)
    rules = request_limits._rules_for_request(_request(f"{LAMINATE}/predict/response"))
    assert rules, "an open prefix must still be metered"
    names = {rule.name for rule, _identity in rules}
    assert names == {"public-demo-burst", "public-demo-hourly"}
    assert all(rule.identity == "ip" for rule, _identity in rules)
    assert all(identity == "203.0.113.9" for _rule, identity in rules)


def test_unopened_paths_get_no_anonymous_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unchanged behaviour elsewhere: the entitlement check rejects first."""
    monkeypatch.setenv(module_access.PUBLIC_DEMO_PATHS_ENV, LAMINATE)
    monkeypatch.setenv(module_access.PUBLIC_DEMO_HOSTS_ENV, DEMO_HOST)
    assert request_limits._rules_for_request(_request(f"{RAG}/ask")) == []


def test_production_guard_on_the_blanket_bypass_is_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The narrow switch must not become a way around the blunt one."""
    monkeypatch.setenv(module_access.LOCAL_AUTH_BYPASS_ENV, "1")
    with pytest.raises(RuntimeError):
        module_access.local_auth_bypass_enabled()
