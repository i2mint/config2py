"""Value-level detection of credentials in free text.

:func:`config2py.util.looks_like_secret` judges a *key name* (``OPENAI_API_KEY``);
:func:`has_secret` judges a *value*: it is for text about to be written somewhere
others can read it (a report, an issue body, a log line), where the credential is
in the text rather than in its label.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

#: Before a credential-like key: up to four ``word_``/``word-``/``word.`` or camelCase
#: prefixes (``x-api-key``, ``accessToken``), starting at a word start (so ``outside``
#: is not ``sid``). Bounded, so matching stays linear on long runs.
_KEY_PREFIX = (
    r"(?<![a-z0-9])(?:[a-z0-9]{1,32}[_.-]|[a-z][a-z0-9]{0,31}(?=(?-i:[A-Z]))){0,4}"
)
#: After it: an optional ``id``/``key``/``token`` suffix, a closing quote (JSON), ``=`` or ``:``.
_KEY_TAIL = r"(?:[_.-]?(?:id|key|token))?[\"']?\s*[=:]\s*[\"']?"

#: Shapes of a credential in free text (some prefix alternatives here are looser than the
#: matching :data:`SECRET_RULES` entry, kept so no earlier match is lost): a header or cookie line, a secret-named key
#: with a value (any value for a password, secret or key; an opaque one holding a
#: digit for a token, session or auth key), credentials in a URL, a JWT, a known key
#: prefix, or a long opaque string with at least four digits. Errs on the side of
#: flagging: a false positive keeps a harmless fact out of public text, a false
#: negative publishes a secret.
SECRET_TEXT_PATTERNS = (
    re.compile(r"(?i)(?<![a-z0-9-])(?:proxy-)?(?:authorization|cookie|set-cookie)\s*:"),
    re.compile(
        r"(?i)\b(?:bearer|basic)\s+(?=[a-z0-9._~+/=-]{0,512}(?-i:[A-Z0-9]))"
        r"[a-z0-9._~+/=-]{8,}"
    ),
    re.compile(
        r"(?i)" + _KEY_PREFIX + r"(?:pass(?:wor)?d|pass|pwd|secret|api[_-]?key"
        r"|access[_-]?key|private[_-]?key|credentials?)" + _KEY_TAIL + r"[^\s\"',;]{4,}"
    ),
    re.compile(
        r"(?i)"
        + _KEY_PREFIX
        + r"(?:token|session|sid|auth)"
        + _KEY_TAIL
        + r"(?=[^\s\"',;]{0,512}\d)[^\s\"',;]{8,}"
    ),
    re.compile(r"(?i)\b[a-z][a-z0-9+.-]{0,15}://[^/\s:@]{1,64}:[^/\s@]{1,128}@"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\beyJ[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}"),
    re.compile(
        r"\b(?:(?:sk|pk|rk)[-_](?:live[-_]|test[-_])?[a-zA-Z0-9]{8,}|sk-[a-zA-Z0-9_-]{20,}"
        r"|gh[pousr]_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}|whsec_[a-zA-Z0-9]{16,}"
        r"|glpat-[a-zA-Z0-9_-]{16,}|AIza[a-zA-Z0-9_-]{30,}|(?:AKIA|ASIA)[0-9A-Z]{16}"
        r"|xox[abposr]-[a-zA-Z0-9-]{10,})"
    ),
    re.compile(
        r"(?<![a-zA-Z0-9_-])(?=(?:[a-zA-Z_-]*\d){4})"
        r"(?![a-zA-Z0-9_]*-[a-zA-Z0-9_]*-[a-zA-Z0-9_]*-)[a-zA-Z0-9_-]{32,}"
    ),
)


# ---- distinctive-prefix rules (the SSOT shared with liaise, i2mint/config2py#66) ----

#: How many words may name a private key's type (``ENCRYPTED``, ``OPENSSH``), and how long
#: each may be.
_KEY_TYPE_WORDS_MAX = 4
_KEY_TYPE_WORD_MAX = 16
#: A private key's first line: PEM's ``-----BEGIN ... PRIVATE KEY-----``, its type's words
#: bounded, or PGP's ``-----BEGIN PGP PRIVATE KEY BLOCK-----``.
PRIVATE_KEY_PATTERN = (
    r"-----BEGIN "
    rf"(?:(?:[A-Z0-9]{{1,{_KEY_TYPE_WORD_MAX}}} ){{0,{_KEY_TYPE_WORDS_MAX}}}PRIVATE KEY"
    r"|PGP PRIVATE KEY BLOCK)-----"
)
#: The token shapes of liaise's 0.1 leak scan, each without the word boundary it starts at: the
#: GitHub (``ghp_`` and its siblings, ``github_pat_``), ``sk-`` API key, AWS access key,
#: Hugging Face (``hf_``) and Slack (``xoxb-`` and its siblings) shapes.
TOKEN_SHAPES = (
    r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"github_pat_\w{20,}",
    r"sk-[\w-]{20,}",
    r"AKIA[0-9A-Z]{16}\b",
    r"hf_[A-Za-z0-9]{30,}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}",
)
#: The rule id of each of :data:`TOKEN_SHAPES`, in order.
TOKEN_RULES = (
    "github-token",
    "github-fine-grained-token",
    "sk-api-key",
    "aws-access-key",
    "hugging-face-token",
    "slack-token",
)
#: The literals every match of each of :data:`TOKEN_SHAPES` contains, in order.
TOKEN_LITERALS = (
    ("ghp_", "gho_", "ghu_", "ghs_", "ghr_"),
    ("github_pat_",),
    ("sk-",),
    ("AKIA",),
    ("hf_",),
    ("xoxb-", "xoxa-", "xoxp-", "xoxr-", "xoxs-"),
)


@dataclass(frozen=True)
class SecretRule:
    """A secret's shape: ``rule`` names it, ``pattern`` is its expression.

    Data only; the matching engine is the user's (liaise scans message views with it,
    :func:`has_secret` a plain string). ``literals``: strings one of which every match
    contains (in case-folded text, with ``ignore_case``), a cheap pre-filter; empty:
    always scan. ``word_start``: a match must start a word. ``wrappable``: a hint for
    engines that also look for the rule in text with line breaks and markup removed (a
    token split by them): such a pattern must not fail after an unbounded repetition.
    :func:`has_secret` scans the text as given and ignores it.
    """

    rule: str
    pattern: str
    literals: tuple[str, ...] = ()
    word_start: bool = True
    wrappable: bool = True
    ignore_case: bool = False

    def may_match(self, text: str) -> bool:
        """Whether ``text`` holds one of :attr:`literals`, or the rule has none."""
        if not self.literals:
            return True
        haystack = text.casefold() if self.ignore_case else text
        return any(literal in haystack for literal in self.literals)

    def search(self, text: str) -> bool:
        """Whether the rule matches ``text``."""
        if not self.may_match(text):
            return False
        return bool(re.search(rf"\b{self.pattern}" if self.word_start else self.pattern, text))


# The rules after the token shapes and the private-key header adapt gitleaks' default configuration, under this notice:
#
#   MIT License
#
#   Copyright (c) 2019 Zachary Rice
#
#   Permission is hereby granted, free of charge, to any person obtaining a copy
#   of this software and associated documentation files (the "Software"), to deal
#   in the Software without restriction, including without limitation the rights
#   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#   copies of the Software, and to permit persons to whom the Software is
#   furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in all
#   copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#   SOFTWARE.

#: The secret rules (liaise's ``secret_detector`` scans with them by default): the token shapes and
#: private-key header, then distinctive-prefix rules adapted from gitleaks (the gitleaks id
#: precedes each).
SECRET_RULES: tuple[SecretRule, ...] = (
    *(
        SecretRule(rule, shape, literals)
        for rule, shape, literals in zip(TOKEN_RULES, TOKEN_SHAPES, TOKEN_LITERALS)
    ),
    SecretRule(
        "private-key",
        PRIVATE_KEY_PATTERN,
        ("-----BEGIN ",),
        word_start=False,
        wrappable=False,
    ),
    # gitlab-pat
    SecretRule("gitlab-token", r"glpat-[\w-]{20}", ("glpat-",)),
    # gcp-api-key
    SecretRule("google-api-key", r"AIza[\w-]{35}", ("AIza",)),
    # npm-access-token
    SecretRule("npm-token", r"(?i:npm_[a-z0-9]{36})", ("npm_",), ignore_case=True),
    # pypi-upload-token
    SecretRule(
        "pypi-token", r"pypi-AgEIcHlwaS5vcmc[\w-]{50,1000}", ("pypi-AgEIcHlwaS5vcmc",)
    ),
    # sendgrid-api-token
    SecretRule("sendgrid-api-key", r"SG\.[A-Za-z0-9=_.-]{66}", ("SG.",)),
    # age-secret-key
    SecretRule(
        "age-secret-key",
        r"AGE-SECRET-KEY-1[QPZRY9X8GF2TVDW0S3JN54KHCE6MUA7L]{58}",
        ("AGE-SECRET-KEY-1",),
    ),
    # telegram-bot-api-token, without its context words
    SecretRule("telegram-bot-token", r"[0-9]{5,16}:A[\w-]{34}(?![\w-])", (":A",)),
    # stripe-access-token
    SecretRule(
        "stripe-key",
        r"(?:sk|rk)_(?:test|live|prod)_[A-Za-z0-9]{10,99}",
        ("k_test_", "k_live_", "k_prod_"),
    ),
    # shopify-access-token
    SecretRule("shopify-token", r"shpat_[a-fA-F0-9]{32}", ("shpat_",)),
    # digitalocean-pat
    SecretRule("digitalocean-token", r"dop_v1_[a-f0-9]{64}", ("dop_v1_",)),
    # slack-webhook-url
    SecretRule(
        "slack-webhook",
        r"(?:https?://)?hooks\.slack\.com/(?:services|workflows|triggers)"
        r"/[A-Za-z0-9+/]{43,56}",
        ("hooks.slack.com/",),
    ),
    # slack-app-token
    SecretRule(
        "slack-app-token",
        r"(?i:xapp-\d-[A-Z0-9]{1,64}-\d{1,16}-[a-z0-9]{1,128})",
        ("xapp-",),
        ignore_case=True,
    ),
    # doppler-api-token
    SecretRule("doppler-token", r"dp\.pt\.[A-Za-z0-9]{43}", ("dp.pt.",)),
    # linear-api-key
    SecretRule("linear-api-key", r"lin_api_[A-Za-z0-9]{40}", ("lin_api_",)),
    # huggingface-organization-api-token
    SecretRule("hugging-face-org-token", r"api_org_[A-Za-z]{34}", ("api_org_",)),
    # aws-access-token, less the AKIA prefix the token-shape rule has
    SecretRule(
        "aws-access-key-id",
        r"(?:A3T[A-Z0-9]|ASIA|ABIA|ACCA)[A-Z2-7]{16}\b",
        ("A3T", "ASIA", "ABIA", "ACCA"),
    ),
    # postman-api-token
    SecretRule("postman-api-key", r"PMAK-[A-Fa-f0-9]{24}-[A-Fa-f0-9]{34}", ("PMAK-",)),
    # grafana-service-account-token
    SecretRule(
        "grafana-service-account-token",
        r"(?i:glsa_[a-z0-9]{32}_[a-f0-9]{8})",
        ("glsa_",),
        ignore_case=True,
    ),
    # perplexity-api-key
    SecretRule("perplexity-api-key", r"pplx-[A-Za-z0-9]{48}", ("pplx-",)),
    # sentry-user-token
    SecretRule("sentry-user-token", r"sntryu_[a-f0-9]{64}", ("sntryu_",)),
    # pulumi-api-token
    SecretRule("pulumi-token", r"pul-[a-f0-9]{40}", ("pul-",)),
    # vault-service-token
    SecretRule("vault-token", r"hvs\.[\w-]{90,120}", ("hvs.",)),
    # 1password-service-account-token
    SecretRule(
        "1password-service-account-token",
        r"ops_eyJ[A-Za-z0-9+/]{250,}={0,3}",
        ("ops_eyJ",),
    ),
    # jwt; not wrappable: its bounded parts would still make the unanchored scan slow
    SecretRule(
        "jwt",
        r"ey[A-Za-z0-9]{17,4096}\.ey[A-Za-z0-9/\\_-]{17,4096}"
        r"\.(?:[A-Za-z0-9/\\_-]{10,4096}={0,2})?",
        (".ey",),
        wrappable=False,
    ),
)


def has_secret(
    text: str,
    *,
    rules: Iterable[SecretRule] = SECRET_RULES,
    patterns: Iterable[re.Pattern] = SECRET_TEXT_PATTERNS,
) -> bool:
    """Whether ``text`` looks like it holds a credential.

    True when a contextual pattern (:data:`SECRET_TEXT_PATTERNS`: headers, key=value,
    URL credentials, JWTs, long opaque strings) or a distinctive-prefix rule
    (:data:`SECRET_RULES`) matches. Both are keyword-only seams.

    >>> [has_secret(t) for t in ("cursor (size=first, cursor=after)", "10000 results",
    ...                          "needs Cookie: sid=abc", "api_key=a1b2c3d4e5",
    ...                          "page via ?pageToken=", "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0",
    ...                          "use glpat-" + "a" * 20)]
    [False, False, True, True, False, True, True]
    """
    return any(p.search(text) for p in patterns) or any(r.search(text) for r in rules)
