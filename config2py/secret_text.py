"""Value-level detection of credentials in free text.

:func:`config2py.util.looks_like_secret` judges a *key name* (``OPENAI_API_KEY``);
:func:`has_secret` judges a *value*: it is for text about to be written somewhere
others can read it (a report, an issue body, a log line), where the credential is
in the text rather than in its label.
"""

import re

#: Before a credential-like key: up to four ``word_``/``word-``/``word.`` or camelCase
#: prefixes (``x-api-key``, ``accessToken``), starting at a word start (so ``outside``
#: is not ``sid``). Bounded, so matching stays linear on long runs.
_KEY_PREFIX = (
    r"(?<![a-z0-9])(?:[a-z0-9]{1,32}[_.-]|[a-z][a-z0-9]{0,31}(?=(?-i:[A-Z]))){0,4}"
)
#: After it: an optional ``id``/``key``/``token`` suffix, a closing quote (JSON), ``=`` or ``:``.
_KEY_TAIL = r"(?:[_.-]?(?:id|key|token))?[\"']?\s*[=:]\s*[\"']?"

#: Shapes of a credential in free text: a header or cookie line, a secret-named key
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


def has_secret(text: str) -> bool:
    """Whether ``text`` looks like it holds a credential (see :data:`SECRET_TEXT_PATTERNS`).

    >>> [has_secret(t) for t in ("cursor (size=first, cursor=after)", "10000 results",
    ...                          "needs Cookie: sid=abc", "api_key=a1b2c3d4e5",
    ...                          "page via ?pageToken=", "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0")]
    [False, False, True, True, False, True]
    """
    return any(p.search(text) for p in SECRET_TEXT_PATTERNS)
