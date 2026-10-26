"""Tests for ``has_secret``, the value-level credential detector (moved from scraped)."""

import time

import pytest

from config2py import has_secret


@pytest.mark.parametrize("text", [
    "send Cookie: sid=9f8e7d6c5b4a",
    "worked with Authorization: Bearer abc123def456",
    "api_key=a1b2c3d4e5f6 in query",
    "jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0",
    "api (session_id=7f3a9c2e11)",
    "ghp_abcdefghijklmnopqrstuvwxyz0123",
    "id 3f9a2b7c8d1e4f5a6b7c8d9e0f1a2b3c",
    "login via https://user:pw1234@host/x",
    '{"api_key": "a1b2c3d4e5f6g7"}',
    "password: hunter2",
    "x-api-key: abcdefghijklmnop",
    "accessToken=ab12cd34ef56",
    "Basic dXNlcjpwYXNz",
])
def test_credential_shaped_text_is_flagged(text):
    assert has_secret(text)


@pytest.mark.parametrize("text", [
    "cursor (size=variables.first, cursor=variables.after)", "deep paging capped",
    "page via ?pageToken=", "basic pagination", "token pagination", "cookie banner blocks the DOM",
    "10000 results", "state blob in __NEXT_DATA__", "outside: 2024-10-01 snapshot", "author: 12345678",
    "persisted-query-hash-sha256-in-extensions-field", "session: 30 minutes", "sid=123",
])
def test_ordinary_text_is_not_mistaken_for_a_secret(text):
    assert not has_secret(text)


@pytest.mark.parametrize("unit", ["a", "a-", "a_", "aB", "x:", "a."])
def test_the_detector_stays_fast_on_long_runs(unit):
    text = unit * (50_000 // len(unit))
    start = time.perf_counter()
    has_secret(text)
    assert time.perf_counter() - start < 1
