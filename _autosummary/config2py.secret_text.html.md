# config2py.secret_text

Value-level detection of credentials in free text.

[`config2py.util.looks_like_secret()`](config2py.util.html.md#config2py.util.looks_like_secret) judges a *key name* (`OPENAI_API_KEY`);
[`has_secret()`](#config2py.secret_text.has_secret) judges a *value*: it is for text about to be written somewhere
others can read it (a report, an issue body, a log line), where the credential is
in the text rather than in its label.

### Module Attributes

| [`SECRET_TEXT_PATTERNS`](#config2py.secret_text.SECRET_TEXT_PATTERNS)   | a header or cookie line, a secret-named key with a value (any value for a password, secret or key; an opaque one holding a digit for a token, session or auth key), credentials in a URL, a JWT, a known key prefix, or a long opaque string with at least four digits.   |
|-------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

### Functions

| [`has_secret`](#config2py.secret_text.has_secret)(text)   | Whether `text` looks like it holds a credential (see [`SECRET_TEXT_PATTERNS`](#config2py.secret_text.SECRET_TEXT_PATTERNS)).   |
|---------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|

### config2py.secret_text.SECRET_TEXT_PATTERNS *= (re.compile('(?i)(?<![a-z0-9-])(?:proxy-)?(?:authorization|cookie|set-cookie)\\\\s\*:', re.IGNORECASE), re.compile('(?i)\\\\b(?:bearer|basic)\\\\s+(?=[a-z0-9._~+/=-]{0,512}(?-i:[A-Z0-9]))[a-z0-9._~+/=-]{8,}', re.IGNORECASE), re.compile('(?i)(?<![a-z0-9])(?:[a-z0-9]{1,32}[_.-]|[a-z][a-z0-9]{0,31}(?=(?-i:[A-Z]))){0,4}(?:pass(?:wor)?d|pass|pwd|secret|api[_-]?key|access[_-]?key|private[_-]?key|credentials?)(?:[_.-]?(?:id|key|token))?[\\\\, re.IGNORECASE), re.compile('(?i)(?<![a-z0-9])(?:[a-z0-9]{1,32}[_.-]|[a-z][a-z0-9]{0,31}(?=(?-i:[A-Z]))){0,4}(?:token|session|sid|auth)(?:[_.-]?(?:id|key|token))?[\\\\"\\']?\\\\s\*[=:]\\\\s\*[\\\\"\\']?(?=[^\\\\s\\\\"\\',;]{0,512}\\\\d)[^\\\\s\\\\"\\',, re.IGNORECASE), re.compile('(?i)\\\\b[a-z][a-z0-9+.-]{0,15}://[^/\\\\s:@]{1,64}:[^/\\\\s@]{1,128}@', re.IGNORECASE), re.compile('-----BEGIN [A-Z ]\*PRIVATE KEY-----'), re.compile('\\\\beyJ[a-zA-Z0-9_-]{8,}\\\\.[a-zA-Z0-9_-]{8,}'), re.compile('\\\\b(?:(?:sk|pk|rk)[-_](?:live[-_]|test[-_])?[a-zA-Z0-9]{8,}|sk-[a-zA-Z0-9_-]{20,}|gh[pousr]_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}|whsec_[a-zA-Z0-9]{16,}|glpat-[a-zA-Z0-9_-]{16,}|AIza[a-zA-Z0-), re.compile('(?<![a-zA-Z0-9_-])(?=(?:[a-zA-Z_-]\*\\\\d){4})(?![a-zA-Z0-9_]\*-[a-zA-Z0-9_]\*-[a-zA-Z0-9_]\*-)[a-zA-Z0-9_-]{32,}'))*

a header or cookie line, a secret-named key
with a value (any value for a password, secret or key; an opaque one holding a
digit for a token, session or auth key), credentials in a URL, a JWT, a known key
prefix, or a long opaque string with at least four digits. Errs on the side of
flagging: a false positive keeps a harmless fact out of public text, a false
negative publishes a secret.

* **Type:**
  Shapes of a credential in free text

### config2py.secret_text.has_secret(text)

Whether `text` looks like it holds a credential (see [`SECRET_TEXT_PATTERNS`](#config2py.secret_text.SECRET_TEXT_PATTERNS)).

```pycon
>>> [has_secret(t) for t in ("cursor (size=first, cursor=after)", "10000 results",
...                          "needs Cookie: sid=abc", "api_key=a1b2c3d4e5",
...                          "page via ?pageToken=", "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0")]
[False, False, True, True, False, True]
```

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)
