# config2py.secret_text

Value-level detection of credentials in free text.

[`config2py.util.looks_like_secret()`](config2py.util.html.md#config2py.util.looks_like_secret) judges a *key name* (`OPENAI_API_KEY`);
[`has_secret()`](#config2py.secret_text.has_secret) judges a *value*: it is for text about to be written somewhere
others can read it (a report, an issue body, a log line), where the credential is
in the text rather than in its label.

### Module Attributes

| [`SECRET_TEXT_PATTERNS`](#config2py.secret_text.SECRET_TEXT_PATTERNS)   | Shapes of a credential in free text (some prefix alternatives here are looser than the matching [`SECRET_RULES`](#config2py.secret_text.SECRET_RULES) entry, kept so no earlier match is lost): a header or cookie line, a secret-named key with a value (any value for a password, secret or key; an opaque one holding a digit for a token, session or auth key), credentials in a URL, a JWT, a known key prefix, or a long opaque string with at least four digits.   |
|-------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`PRIVATE_KEY_PATTERN`](#config2py.secret_text.PRIVATE_KEY_PATTERN)    | PEM's <br/><br/>```<br/>``<br/>```<br/><br/>-----BEGIN .                                                                                                                                                                                                                                                                                                                                                                                                                          |
| [`TOKEN_SHAPES`](#config2py.secret_text.TOKEN_SHAPES)           | the GitHub (`ghp_` and its siblings, `github_pat_`), `sk-` API key, AWS access key, Hugging Face (`hf_`) and Slack (`xoxb-` and its siblings) shapes.                                                                                                                                                                                                                                                                                                                             |
| [`TOKEN_RULES`](#config2py.secret_text.TOKEN_RULES)            | The rule id of each of [`TOKEN_SHAPES`](#config2py.secret_text.TOKEN_SHAPES), in order.                                                                                                                                                                                                                                                                                                                                                                                   |
| [`TOKEN_LITERALS`](#config2py.secret_text.TOKEN_LITERALS)         | The literals every match of each of [`TOKEN_SHAPES`](#config2py.secret_text.TOKEN_SHAPES) contains, in order.                                                                                                                                                                                                                                                                                                                                                             |
| [`SECRET_RULES`](#config2py.secret_text.SECRET_RULES)           | the token shapes and private-key header, then distinctive-prefix rules adapted from gitleaks (the gitleaks id precedes each).                                                                                                                                                                                                                                                                                                                                                     |

### Functions

| [`has_secret`](#config2py.secret_text.has_secret)(text, \*[, rules, word_start, ...])   | Whether `text` looks like it holds a credential.   |
|---------------------------------------------------------------------------------------------------|----------------------------------------------------|

### Classes

| [`SecretRule`](#config2py.secret_text.SecretRule)(rule, pattern[, literals, ...])   | A secret's shape: `rule` names it, `pattern` is its expression.   |
|-----------------------------------------------------------------------------------------------|-------------------------------------------------------------------|

### config2py.secret_text.PRIVATE_KEY_PATTERN *= '-----BEGIN (?:(?:[A-Z0-9]{1,16} ){0,4}PRIVATE KEY|PGP PRIVATE KEY BLOCK)-----'*

PEM’s `-----BEGIN ... PRIVATE KEY-----`, its type’s words
bounded, or PGP’s `-----BEGIN PGP PRIVATE KEY BLOCK-----`.

* **Type:**
  A private key’s first line

### config2py.secret_text.SECRET_RULES *: [tuple](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[SecretRule](#config2py.secret_text.SecretRule), ...]* *= (SecretRule(rule='github-token', pattern='gh[pousr]_[A-Za-z0-9]{20,}', literals=('ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_'), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='github-fine-grained-token', pattern='github_pat_\\\\w{20,}', literals=('github_pat_',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='sk-api-key', pattern='sk-[\\\\w-]{20,}', literals=('sk-',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='aws-access-key', pattern='AKIA[0-9A-Z]{16}\\\\b', literals=('AKIA',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='hugging-face-token', pattern='hf_[A-Za-z0-9]{30,}', literals=('hf_',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='slack-token', pattern='xox[baprs]-[A-Za-z0-9-]{10,}', literals=('xoxb-', 'xoxa-', 'xoxp-', 'xoxr-', 'xoxs-'), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='private-key', pattern='-----BEGIN (?:(?:[A-Z0-9]{1,16} ){0,4}PRIVATE KEY|PGP PRIVATE KEY BLOCK)-----', literals=('-----BEGIN ',), word_start=False, wrappable=False, ignore_case=False), SecretRule(rule='gitlab-token', pattern='glpat-[\\\\w-]{20}', literals=('glpat-',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='google-api-key', pattern='AIza[\\\\w-]{35}', literals=('AIza',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='npm-token', pattern='(?i:npm_[a-z0-9]{36})', literals=('npm_',), word_start=True, wrappable=True, ignore_case=True), SecretRule(rule='pypi-token', pattern='pypi-AgEIcHlwaS5vcmc[\\\\w-]{50,1000}', literals=('pypi-AgEIcHlwaS5vcmc',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='sendgrid-api-key', pattern='SG\\\\.[A-Za-z0-9=_.-]{66}', literals=('SG.',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='age-secret-key', pattern='AGE-SECRET-KEY-1[QPZRY9X8GF2TVDW0S3JN54KHCE6MUA7L]{58}', literals=('AGE-SECRET-KEY-1',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='telegram-bot-token', pattern='[0-9]{5,16}:A[\\\\w-]{34}(?![\\\\w-])', literals=(':A',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='stripe-key', pattern='(?:sk|rk)_(?:test|live|prod)_[A-Za-z0-9]{10,99}', literals=('k_test_', 'k_live_', 'k_prod_'), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='shopify-token', pattern='shpat_[a-fA-F0-9]{32}', literals=('shpat_',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='digitalocean-token', pattern='dop_v1_[a-f0-9]{64}', literals=('dop_v1_',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='slack-webhook', pattern='(?:https?://)?hooks\\\\.slack\\\\.com/(?:services|workflows|triggers)/[A-Za-z0-9+/]{43,56}', literals=('hooks.slack.com/',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='slack-app-token', pattern='(?i:xapp-\\\\d-[A-Z0-9]{1,64}-\\\\d{1,16}-[a-z0-9]{1,128})', literals=('xapp-',), word_start=True, wrappable=True, ignore_case=True), SecretRule(rule='doppler-token', pattern='dp\\\\.pt\\\\.[A-Za-z0-9]{43}', literals=('dp.pt.',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='linear-api-key', pattern='lin_api_[A-Za-z0-9]{40}', literals=('lin_api_',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='hugging-face-org-token', pattern='api_org_[A-Za-z]{34}', literals=('api_org_',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='aws-access-key-id', pattern='(?:A3T[A-Z0-9]|ASIA|ABIA|ACCA)[A-Z2-7]{16}\\\\b', literals=('A3T', 'ASIA', 'ABIA', 'ACCA'), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='postman-api-key', pattern='PMAK-[A-Fa-f0-9]{24}-[A-Fa-f0-9]{34}', literals=('PMAK-',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='grafana-service-account-token', pattern='(?i:glsa_[a-z0-9]{32}_[a-f0-9]{8})', literals=('glsa_',), word_start=True, wrappable=True, ignore_case=True), SecretRule(rule='perplexity-api-key', pattern='pplx-[A-Za-z0-9]{48}', literals=('pplx-',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='sentry-user-token', pattern='sntryu_[a-f0-9]{64}', literals=('sntryu_',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='pulumi-token', pattern='pul-[a-f0-9]{40}', literals=('pul-',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='vault-token', pattern='hvs\\\\.[\\\\w-]{90,120}', literals=('hvs.',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='1password-service-account-token', pattern='ops_eyJ[A-Za-z0-9+/]{250,}={0,3}', literals=('ops_eyJ',), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='jwt', pattern='ey[A-Za-z0-9]{17,4096}\\\\.ey[A-Za-z0-9/\\\\\\\\_-]{17,4096}\\\\.(?:[A-Za-z0-9/\\\\\\\\_-]{10,4096}={0,2})?', literals=('.ey',), word_start=True, wrappable=False, ignore_case=False))*

the token shapes and
private-key header, then distinctive-prefix rules adapted from gitleaks (the gitleaks id
precedes each).

* **Type:**
  The secret rules (liaise’s `secret_detector` scans with them by default)

### config2py.secret_text.SECRET_TEXT_PATTERNS *= (re.compile('(?i)(?<![a-z0-9-])(?:proxy-)?(?:authorization|cookie|set-cookie)\\\\s\*:', re.IGNORECASE), re.compile('(?i)\\\\b(?:bearer|basic)\\\\s+(?=[a-z0-9._~+/=-]{0,512}(?-i:[A-Z0-9]))[a-z0-9._~+/=-]{8,}', re.IGNORECASE), re.compile('(?i)(?<![a-z0-9])(?:[a-z0-9]{1,32}[_.-]|[a-z][a-z0-9]{0,31}(?=(?-i:[A-Z]))){0,4}(?:pass(?:wor)?d|pass|pwd|secret|api[_-]?key|access[_-]?key|private[_-]?key|credentials?)(?:[_.-]?(?:id|key|token))?[\\\\, re.IGNORECASE), re.compile('(?i)(?<![a-z0-9])(?:[a-z0-9]{1,32}[_.-]|[a-z][a-z0-9]{0,31}(?=(?-i:[A-Z]))){0,4}(?:token|session|sid|auth)(?:[_.-]?(?:id|key|token))?[\\\\"\\']?\\\\s\*[=:]\\\\s\*[\\\\"\\']?(?=[^\\\\s\\\\"\\',;]{0,512}\\\\d)[^\\\\s\\\\"\\',, re.IGNORECASE), re.compile('(?i)\\\\b[a-z][a-z0-9+.-]{0,15}://[^/\\\\s:@]{1,64}:[^/\\\\s@]{1,128}@', re.IGNORECASE), re.compile('-----BEGIN [A-Z ]\*PRIVATE KEY-----'), re.compile('\\\\beyJ[a-zA-Z0-9_-]{8,}\\\\.[a-zA-Z0-9_-]{8,}'), re.compile('\\\\b(?:(?:sk|pk|rk)[-_](?:live[-_]|test[-_])?[a-zA-Z0-9]{8,}|sk-[a-zA-Z0-9_-]{20,}|gh[pousr]_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}|whsec_[a-zA-Z0-9]{16,}|glpat-[a-zA-Z0-9_-]{16,}|AIza[a-zA-Z0-), re.compile('(?<![a-zA-Z0-9_-])(?=(?:[a-zA-Z_-]\*\\\\d){4})(?![a-zA-Z0-9_]\*-[a-zA-Z0-9_]\*-[a-zA-Z0-9_]\*-)[a-zA-Z0-9_-]{32,}'))*

Shapes of a credential in free text (some prefix alternatives here are looser than the
matching [`SECRET_RULES`](#config2py.secret_text.SECRET_RULES) entry, kept so no earlier match is lost): a header or cookie line, a secret-named key
with a value (any value for a password, secret or key; an opaque one holding a
digit for a token, session or auth key), credentials in a URL, a JWT, a known key
prefix, or a long opaque string with at least four digits. Errs on the side of
flagging: a false positive keeps a harmless fact out of public text, a false
negative publishes a secret.

### *class* config2py.secret_text.SecretRule(rule, pattern, literals=(), word_start=True, wrappable=True, ignore_case=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A secret’s shape: `rule` names it, `pattern` is its expression.

Data only; the matching engine is the user’s (liaise scans message views with it,
[`has_secret()`](#config2py.secret_text.has_secret) a plain string). `literals`: strings one of which every match
contains (in case-folded text, with `ignore_case`), a cheap pre-filter; empty:
always scan. `word_start`: a match must start a word. `wrappable`: a hint for
engines that also look for the rule in text with line breaks and markup removed (a
token split by them): such a pattern must not fail after an unbounded repetition.
[`has_secret()`](#config2py.secret_text.has_secret) scans the text as given and ignores it.

#### may_match(text)

Whether `text` holds one of `literals`, or the rule has none.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

#### search(text)

Whether the rule matches `text`.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### config2py.secret_text.TOKEN_LITERALS *= (('ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_'), ('github_pat_',), ('sk-',), ('AKIA',), ('hf_',), ('xoxb-', 'xoxa-', 'xoxp-', 'xoxr-', 'xoxs-'))*

The literals every match of each of [`TOKEN_SHAPES`](#config2py.secret_text.TOKEN_SHAPES) contains, in order.

### config2py.secret_text.TOKEN_RULES *= ('github-token', 'github-fine-grained-token', 'sk-api-key', 'aws-access-key', 'hugging-face-token', 'slack-token')*

The rule id of each of [`TOKEN_SHAPES`](#config2py.secret_text.TOKEN_SHAPES), in order.

### config2py.secret_text.TOKEN_SHAPES *= ('gh[pousr]_[A-Za-z0-9]{20,}', 'github_pat_\\\\w{20,}', 'sk-[\\\\w-]{20,}', 'AKIA[0-9A-Z]{16}\\\\b', 'hf_[A-Za-z0-9]{30,}', 'xox[baprs]-[A-Za-z0-9-]{10,}')*

the
GitHub (`ghp_` and its siblings, `github_pat_`), `sk-` API key, AWS access key,
Hugging Face (`hf_`) and Slack (`xoxb-` and its siblings) shapes.

* **Type:**
  The token shapes of liaise’s 0.1 leak scan, each without the word boundary it starts at

### config2py.secret_text.has_secret(text, \*, rules=(SecretRule(rule='github-token', pattern='gh[pousr]_[A-Za-z0-9]{20, }', literals=('ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_'), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='github-fine-grained-token', pattern='github_pat_\\\\w{20, }', literals=('github_pat_', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='sk-api-key', pattern='sk-[\\\\w-]{20, }', literals=('sk-', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='aws-access-key', pattern='AKIA[0-9A-Z]{16}\\\\b', literals=('AKIA', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='hugging-face-token', pattern='hf_[A-Za-z0-9]{30, }', literals=('hf_', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='slack-token', pattern='xox[baprs]-[A-Za-z0-9-]{10, }', literals=('xoxb-', 'xoxa-', 'xoxp-', 'xoxr-', 'xoxs-'), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='private-key', pattern='-----BEGIN (?:(?:[A-Z0-9]{1, 16} ){0, 4}PRIVATE KEY|PGP PRIVATE KEY BLOCK)-----', literals=('-----BEGIN ', ), word_start=False, wrappable=False, ignore_case=False), SecretRule(rule='gitlab-token', pattern='glpat-[\\\\w-]{20}', literals=('glpat-', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='google-api-key', pattern='AIza[\\\\w-]{35}', literals=('AIza', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='npm-token', pattern='(?i:npm_[a-z0-9]{36})', literals=('npm_', ), word_start=True, wrappable=True, ignore_case=True), SecretRule(rule='pypi-token', pattern='pypi-AgEIcHlwaS5vcmc[\\\\w-]{50, 1000}', literals=('pypi-AgEIcHlwaS5vcmc', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='sendgrid-api-key', pattern='SG\\\\.[A-Za-z0-9=_.-]{66}', literals=('SG.', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='age-secret-key', pattern='AGE-SECRET-KEY-1[QPZRY9X8GF2TVDW0S3JN54KHCE6MUA7L]{58}', literals=('AGE-SECRET-KEY-1', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='telegram-bot-token', pattern='[0-9]{5, 16}: A[\\\\w-]{34}(?![\\\\w-])', literals=(':A', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='stripe-key', pattern='(?:sk|rk)_(?:test|live|prod)_[A-Za-z0-9]{10, 99}', literals=('k_test_', 'k_live_', 'k_prod_'), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='shopify-token', pattern='shpat_[a-fA-F0-9]{32}', literals=('shpat_', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='digitalocean-token', pattern='dop_v1_[a-f0-9]{64}', literals=('dop_v1_', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='slack-webhook', pattern='(?:https?://)?hooks\\\\.slack\\\\.com/(?:services|workflows|triggers)/[A-Za-z0-9+/]{43, 56}', literals=('hooks.slack.com/', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='slack-app-token', pattern='(?i:xapp-\\\\d-[A-Z0-9]{1, 64}-\\\\d{1, 16}-[a-z0-9]{1, 128})', literals=('xapp-', ), word_start=True, wrappable=True, ignore_case=True), SecretRule(rule='doppler-token', pattern='dp\\\\.pt\\\\.[A-Za-z0-9]{43}', literals=('dp.pt.', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='linear-api-key', pattern='lin_api_[A-Za-z0-9]{40}', literals=('lin_api_', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='hugging-face-org-token', pattern='api_org_[A-Za-z]{34}', literals=('api_org_', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='aws-access-key-id', pattern='(?:A3T[A-Z0-9]|ASIA|ABIA|ACCA)[A-Z2-7]{16}\\\\b', literals=('A3T', 'ASIA', 'ABIA', 'ACCA'), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='postman-api-key', pattern='PMAK-[A-Fa-f0-9]{24}-[A-Fa-f0-9]{34}', literals=('PMAK-', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='grafana-service-account-token', pattern='(?i:glsa_[a-z0-9]{32}_[a-f0-9]{8})', literals=('glsa_', ), word_start=True, wrappable=True, ignore_case=True), SecretRule(rule='perplexity-api-key', pattern='pplx-[A-Za-z0-9]{48}', literals=('pplx-', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='sentry-user-token', pattern='sntryu_[a-f0-9]{64}', literals=('sntryu_', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='pulumi-token', pattern='pul-[a-f0-9]{40}', literals=('pul-', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='vault-token', pattern='hvs\\\\.[\\\\w-]{90, 120}', literals=('hvs.', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='1password-service-account-token', pattern='ops_eyJ[A-Za-z0-9+/]{250, }={0, 3}', literals=('ops_eyJ', ), word_start=True, wrappable=True, ignore_case=False), SecretRule(rule='jwt', pattern='ey[A-Za-z0-9]{17, 4096}\\\\.ey[A-Za-z0-9/\\\\\\\\_-]{17, 4096}\\\\.(?: [A-Za-z0-9/\\\\\\\\_-]{10, 4096}={0, 2})?', literals=('.ey', ), word_start=True, wrappable=False, ignore_case=False)), patterns=(re.compile('(?i)(?<![a-z0-9-])(?:proxy-)?(?:authorization|cookie|set-cookie)\\\\s\*:', re.IGNORECASE), re.compile('(?i)\\\\b(?: bearer|basic)\\\\s+(? = [a-z0-9._~+/=-]{0, 512}(?-i: [A-Z0-9]))[a-z0-9._~+/ = -]{8, }', re.IGNORECASE), re.compile('(?i)(?<![a-z0-9])(?: [a-z0-9]{1, 32}[_.-]|[a-z][a-z0-9]{0, 31}(?=(?-i:[A-Z]))){0, 4}(?: pass(?:wor)?d|pass|pwd|secret|api[_-]?key|access[_-]?key|private[_-]?key|credentials?)(?:[_.-]?(?:id|key|token))?[\\\\, re.IGNORECASE), re.compile('(?i)(?<![a-z0-9])(?: [a-z0-9]{1, 32}[_.-]|[a-z][a-z0-9]{0, 31}(?=(?-i:[A-Z]))){0, 4}(?: token|session|sid|auth)(?:[_.-]?(?:id|key|token))?[\\\\"\\']?\\\\s\*[ = :]\\\\s\*[\\\\"\\']?(?=[^\\\\s\\\\"\\', ;]{0, 512}\\\\d)[^\\\\s\\\\"\\', re.IGNORECASE), re.compile('(?i)\\\\b[a-z][a-z0-9+.-]{0, 15}: //[^/\\\\s:@]{1, 64}: [^/\\\\s@]{1, 128}@', re.IGNORECASE), re.compile('-----BEGIN [A-Z ]\*PRIVATE KEY-----'), re.compile('\\\\beyJ[a-zA-Z0-9_-]{8, }\\\\.[a-zA-Z0-9_-]{8, }'), re.compile('\\\\b(?: (?:sk|pk|rk)[-_](?:live[-_]|test[-_])?[a-zA-Z0-9]{8, }|sk-[a-zA-Z0-9_-]{20, }|gh[pousr]_[a-zA-Z0-9]{20, }|github_pat_[a-zA-Z0-9_]{20, }|whsec_[a-zA-Z0-9]{16, }|glpat-[a-zA-Z0-9_-]{16, }|AIza[a-zA-Z0-), re.compile('(?<![a-zA-Z0-9_-])(?=(?:[a-zA-Z_-]\*\\\\d){4})(?![a-zA-Z0-9_]\*-[a-zA-Z0-9_]\*-[a-zA-Z0-9_]\*-)[a-zA-Z0-9_-]{32, }')))

Whether `text` looks like it holds a credential.

True when a contextual pattern ([`SECRET_TEXT_PATTERNS`](#config2py.secret_text.SECRET_TEXT_PATTERNS): headers, key=value,
URL credentials, JWTs, long opaque strings) or a distinctive-prefix rule
([`SECRET_RULES`](#config2py.secret_text.SECRET_RULES)) matches. Both are keyword-only seams.

```pycon
>>> [has_secret(t) for t in ("cursor (size=first, cursor=after)", "10000 results",
...                          "needs Cookie: sid=abc", "api_key=a1b2c3d4e5",
...                          "page via ?pageToken=", "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0",
...                          "use glpat-" + "a" * 20)]
[False, False, True, True, False, True, True]
```

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)
