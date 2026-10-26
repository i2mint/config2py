"""Tests for ``has_secret``, the value-level credential detector (moved from scraped)."""

import time

import pytest

from config2py import SECRET_RULES, has_secret


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
    "sk-ant-api03-abcdefghijklmnopqrstuvwxyz",
    "sk-proj-abcdefghijklmnopqrstuvwxyz",
    "github_pat_11ABCDEFG0abcdefghijkl_mnop",
    "AKIAABCDEFGHIJKLMNOP",
    "ASIAABCDEFGHIJKLMNOP",
    "AIza" + "a" * 35,
    "xoxb-1234567890-abcdefgh",
    "glpat-abcdefghijklmnop12",
    "sk_live_abcdefgh12345678",
    "whsec_abcdefghijklmnop1234",
    "-----BEGIN RSA PRIVATE KEY-----",
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


# Each rule's sample at its bound, and a near miss one character short (from liaise's tests,
# where the table lived before i2mint/config2py#66).
SECRET_SAMPLES = {
    "github-token": ("ghp_" + "a" * 20, "ghp_" + "a" * 19),
    "github-fine-grained-token": ("github_pat_" + "a" * 20, "github_pat_" + "a" * 19),
    "sk-api-key": ("sk-" + "a" * 20, "sk-" + "a" * 19),
    "aws-access-key": ("AKIA" + "A" * 16, "AKIA" + "A" * 15),
    "hugging-face-token": ("hf_" + "a" * 30, "hf_" + "a" * 29),
    "slack-token": ("xoxb-" + "1" * 10, "xoxb-" + "1" * 9),
    "private-key": ("-----BEGIN " + "RSA PRIVATE KEY" + "-----", "-----BEGIN " + "RSA PUBLIC KEY" + "-----"),
    "gitlab-token": ("glpat-" + "a" * 20, "glpat-" + "a" * 19),
    "google-api-key": ("AIza" + "a" * 35, "AIza" + "a" * 34),
    "npm-token": ("npm_" + "a" * 36, "npm_" + "a" * 35),
    "pypi-token": ("pypi-" + "AgEIcHlwaS5vcmc" + "a" * 50, "pypi-" + "AgEIcHlwaS5vcmc" + "a" * 49),
    "sendgrid-api-key": ("SG." + "a" * 66, "SG." + "a" * 65),
    "age-secret-key": ("AGE-SECRET-KEY-" + "1" + "Q" * 58, "AGE-SECRET-KEY-" + "1" + "Q" * 57),
    "telegram-bot-token": ("12345:" + "A" + "a" * 34, "12345:" + "A" + "a" * 33),
    "stripe-key": ("sk_" + "test_" + "a" * 10, "sk_" + "test_" + "a" * 9),
    "shopify-token": ("shpat_" + "a" * 32, "shpat_" + "a" * 31),
    "digitalocean-token": ("dop_v1_" + "a" * 64, "dop_v1_" + "a" * 63),
    "slack-webhook": ("https://hooks.slack.com/services/" + "A" * 43, "https://hooks.slack.com/services/" + "A" * 42),
    "slack-app-token": ("xapp-1-A-1-" + "a", "xapp-1-A-1-"),
    "doppler-token": ("dp.pt." + "a" * 43, "dp.pt." + "a" * 42),
    "linear-api-key": ("lin_api_" + "a" * 40, "lin_api_" + "a" * 39),
    "hugging-face-org-token": ("api_org_" + "a" * 34, "api_org_" + "a" * 33),
    "aws-access-key-id": ("ASIA" + "A" * 16, "ASIA" + "A" * 15),
    "postman-api-key": ("PMAK-" + "a" * 24 + "-" + "a" * 34, "PMAK-" + "a" * 24 + "-" + "a" * 33),
    "grafana-service-account-token": ("glsa_" + "a" * 32 + "_" + "a" * 8, "glsa_" + "a" * 32 + "_" + "a" * 7),
    "perplexity-api-key": ("pplx-" + "a" * 48, "pplx-" + "a" * 47),
    "sentry-user-token": ("sntryu_" + "a" * 64, "sntryu_" + "a" * 63),
    "pulumi-token": ("pul-" + "a" * 40, "pul-" + "a" * 39),
    "vault-token": ("hvs." + "a" * 90, "hvs." + "a" * 89),
    "1password-service-account-token": ("ops_" + "eyJ" + "a" * 250, "ops_" + "eyJ" + "a" * 249),
    "jwt": ("ey" + "a" * 17 + ".ey" + "a" * 17 + ".", "ey" + "a" * 16 + ".ey" + "a" * 17 + "."),
}


def test_every_secret_rule_has_a_sample():
    assert set(SECRET_SAMPLES) == {rule.rule for rule in SECRET_RULES}
    assert len(SECRET_RULES) == len(SECRET_SAMPLES)  # no two rules share an id


@pytest.mark.parametrize("rule", SECRET_RULES, ids=lambda r: r.rule)
def test_each_rule_matches_its_sample_but_not_the_near_miss(rule):
    sample, near_miss = SECRET_SAMPLES[rule.rule]
    assert rule.search("Use " + sample + " now.")
    assert not rule.search("Use " + near_miss + " now.")
    assert has_secret("Use " + sample + " now.")


def test_the_rule_and_pattern_seams_are_independent():
    token = "npm_" + "a" * 36  # only the rule table knows npm tokens
    assert has_secret(token)
    assert not has_secret(token, rules=())
    assert not has_secret(token, patterns=(), rules=())
    assert has_secret("password: hunter2", rules=())
    assert not has_secret("password: hunter2", patterns=())
