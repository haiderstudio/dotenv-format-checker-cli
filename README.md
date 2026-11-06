# dotenv-format-checker-cli

Check .env files are well formed, fail CI on a bad line.

[![CI](https://github.com/haiderstudio/dotenv-format-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/dotenv-format-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`dotenv_format_checker` reads the .env files and folders you name
and checks each line follows the `KEY=VALUE` shape: the key uses
uppercase letters, digits, and underscores only, there are no
spaces around the `=`, no key is empty or repeated, and a value
with spaces must be quoted. Every problem names the file and line.
It exits 1 on any problem, so it can fail a CI run before a broken
.env file ships.

- Blank lines and `#` comment lines are skipped. An `export `
  prefix in front of a key is allowed.
- A key must start with a letter or `_`, and hold only `A-Z`,
  `0-9`, and `_`. A lowercase letter, a hyphen, a dot, or a
  leading digit is a problem.
- A value may be empty, and it may hold `=` signs and URLs. A
  value with a space or a tab must be wrapped in matching single
  or double quotes; a quote that never closes, or text after the
  closing quote, is a problem.
- Folders are walked recursively unless `--no-recursive` is
  given. A folder check looks at `.env` files: `.env` itself,
  dotted variants such as `.env.example` and `.env.local`, and
  files whose name ends in `.env`. `.git` folders are never
  walked, and folder links are never followed. `--exclude
  PATTERN` skips files by glob (repeatable).
- `--json` prints the result as JSON instead of plain text, for
  scripts. The summary line goes to standard error, so standard
  output stays clean JSON.
- A file that cannot be read as UTF-8, or a path that does not
  exist, is reported as a problem, not skipped silently.

## What it does NOT do

- It does not check that the variables in a .env file match the
  variables your code uses. That drift check is the job of
  [env-example-sync-cli](https://github.com/haiderstudio/env-example-sync-cli),
  which compares code against `.env.example`.
- It does not check what a value means — no type checks, no
  format checks on URLs or numbers, no secret scanning. A value
  that is shaped right passes, whatever it says.
- It does not fix or rewrite a file. A bad line is reported, not
  repaired.
- It does not fetch files from the network. Every input is a
  local file or folder.

## Who it is for

Anyone who keeps a .env file around and wants a quick, scriptable
check that it is well formed: a developer adding a CI step that
fails the build on a broken settings file, someone hand-editing
settings before a deploy, or anyone checking a file before
committing it. If the file is clean, you get a plain OK line; if
it is not, the report says exactly which line broke.

## How this differs from similar tools

`.env` checks already exist, but none of them is this exact tool.
The exact name `dotenv-format-checker-cli` matches 0 repositories
on GitHub. The whole field for `dotenv format checker` is one
repo: 0xDaniiel/.env-checker (2 stars), a CLI and API that checks
missing or extra variables, type and format errors, and sensitive
values — broader than this slice, because it also checks drift,
types, and secrets. The wider field is mostly schema and sync
tools: fastify/env-schema (270 stars) validates variables against
a schema, and chempogonzalez/dotenv-checker (21 stars) checks,
generates, and syncs .env files — both different jobs. This tool
does a narrower job: a Python standard-library-only CLI that
checks one file's shape, reports every problem with a file and
line, and exits 1 on a bad line for CI — no install beyond
Python, no drift check, no type checks, no secret scanning, no
network.

## Install

Python standard library only — no packages to download. You need
Python 3.8 or newer. Clone the repo and run it in place:

```
git clone https://github.com/haiderstudio/dotenv-format-checker-cli.git
cd dotenv-format-checker-cli
python3 src/dotenv_format_checker.py examples/good.env
```

```
OK — 1 file(s) checked, .env files are well formed.
```

## Usage

Check one file:

```
python3 src/dotenv_format_checker.py examples/good.env
```

Check several files at once:

```
python3 src/dotenv_format_checker.py examples/good.env examples/bad-format.env
```

```
FAIL examples/bad-format.env:2: spaces around '='
FAIL examples/bad-format.env:2: key 'app_port' has a lowercase letter
FAIL examples/bad-format.env:3: empty key
FAIL examples/bad-format.env:4: unquoted value has a space
FAIL examples/bad-format.env:5: line has no '='
FAIL examples/bad-format.env:6: unterminated quote in value
Checked 2 file(s), 6 problem(s) in 1 file(s).
```

Check a whole folder:

```
python3 src/dotenv_format_checker.py examples/
```

```
FAIL examples/bad-format.env:2: spaces around '='
FAIL examples/bad-format.env:2: key 'app_port' has a lowercase letter
FAIL examples/bad-format.env:3: empty key
FAIL examples/bad-format.env:4: unquoted value has a space
FAIL examples/bad-format.env:5: line has no '='
FAIL examples/bad-format.env:6: unterminated quote in value
FAIL examples/duplicates.env:3: duplicate key 'APP_NAME'
Checked 3 file(s), 7 problem(s) in 2 file(s).
```

Machine-readable output with `--json` (the summary goes to
standard error, so standard output is clean JSON):

```
python3 src/dotenv_format_checker.py examples/good.env --json
```

```
{
  "files": [
    {
      "file": "examples/good.env",
      "ok": true,
      "problems": []
    }
  ],
  "summary": {
    "checked": 1,
    "ok": 1,
    "failed": 0,
    "problems": 0
  }
}
```

Exit codes: 0 when every file is well formed, 1 when any file
has a problem, 2 for a usage problem (no files given, a bad flag).

## Examples

### 1. A bad file — six problems in six lines

`examples/bad-format.env` has one of each format problem:

```
python3 src/dotenv_format_checker.py examples/bad-format.env
```

```
FAIL examples/bad-format.env:2: spaces around '='
FAIL examples/bad-format.env:2: key 'app_port' has a lowercase letter
FAIL examples/bad-format.env:3: empty key
FAIL examples/bad-format.env:4: unquoted value has a space
FAIL examples/bad-format.env:5: line has no '='
FAIL examples/bad-format.env:6: unterminated quote in value
Checked 1 file(s), 6 problem(s) in 1 file(s).
```

### 2. A repeated key

`examples/duplicates.env` is clean except that `APP_NAME`
appears twice:

```
python3 src/dotenv_format_checker.py examples/duplicates.env
```

```
FAIL examples/duplicates.env:3: duplicate key 'APP_NAME'
Checked 1 file(s), 1 problem(s) in 1 file(s).
```

### 3. The bundled examples, all at once

```
sh examples/run-example.sh
```

The script checks the good file (passes), then the bad-format
file and the duplicates file (both fail, on purpose). Its full
output is in `examples/sample-output.txt`. The failing runs exit
1, which is the expected result — the script ends with exit 0 so
it can be run as a demo.

## How it is tested

61 tests, standard library `unittest` only, no packages to install:

```
python3 tests/test_dotenv_format_checker.py
```

The tests cover: clean files, comments and blank lines, the
`export` prefix, quoted values with spaces (single and double
quotes), empty values, values holding `=` signs and URLs, keys
with digits and underscores, files with only comments, spaces
around `=` (before, after, and both sides reported once), lower
and mixed-case keys, hyphens and dots in keys, keys starting
with a digit, empty keys, lines with no `=`, duplicate keys,
unquoted values with spaces and tabs, unterminated quotes,
text after the closing quote, line numbers, missing files,
non-UTF-8 files, CRLF line endings, folder walking (recursive,
`--no-recursive`, `.git` skipped, `--exclude`, only .env files
picked up), `--json` output, `--version`, input files left
unchanged, the bundled examples (sample output compared
byte-for-byte against a fresh run, and the README-quoted outputs
checked against it), and hygiene checks (no placeholder text, no
absolute paths, stdlib imports only, `.env` first in
`.gitignore`).

## Limits

- A value with a quote of the same kind inside it is not
  supported: `"say "hi""` is reported as an unterminated quote.
  Use the other kind of quote for the value instead.
- A trailing space after an unquoted value is not flagged here —
  that is trailing whitespace, which is the job of
  [whitespace-checker-cli](https://github.com/haiderstudio/whitespace-checker-cli).
- An inline comment after a value, such as `KEY=value # note`,
  is read as part of the value and fails as an unquoted value
  with a space. Put comments on their own line.

## Contributing

Small, focused improvements are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool was written from scratch for this repo. The idea of
checking .env files is not new — the similar tools named above
(0xDaniiel/.env-checker, fastify/env-schema,
chempogonzalez/dotenv-checker) are listed in "How this differs"
— but every line of code here is original, and the tool builds
on nothing but Python's standard library. All example values
are fake.
