"""Check .env files are well formed.

Reads one or more .env files and checks each line follows the
KEY=VALUE shape: the key uses uppercase letters, digits and
underscores only, there are no spaces around the `=`, no key is
empty or repeated, and a value with spaces must be quoted. Every
problem names the file and line; exits 1 on any problem, so it can
fail a CI run, and 0 when every file is clean.

Report-only: it never writes to an input file.
Standard library only — no packages to install.
"""

import argparse
import fnmatch
import json
import sys
from pathlib import Path

VERSION = "1.0.0"


def _key_problems(key):
    """Problems with one key, not counting duplicates."""
    problems = []
    if key == "":
        return ["empty key"]
    for char in key:
        if not (char.isalnum() or char == "_"):
            return [
                "key "
                f"{key!r} has a character that is not allowed "
                "(use A-Z, 0-9 and _)"
            ]
    if key[0].isdigit():
        problems.append(
            f"key {key!r} must start with a letter or '_'"
        )
    if any(char.islower() for char in key):
        problems.append(f"key {key!r} has a lowercase letter")
    return problems


def _check_value_quoted(value):
    """Check one value and return its problems.

    A value that starts with a quote must end with the same quote,
    and nothing but spaces may follow the closing quote. An
    unquoted value must not hold a space or a tab.
    """
    problems = []
    if value == "":
        return problems
    if value[0] in "\"'":
        quote = value[0]
        stripped = value.rstrip()
        if len(stripped) < 2:
            problems.append("unterminated quote in value")
        else:
            closing = stripped.rfind(quote, 1)
            if closing == -1:
                problems.append("unterminated quote in value")
            elif closing != len(stripped) - 1:
                problems.append("text after the closing quote")
            elif quote in stripped[1:closing]:
                problems.append("unterminated quote in value")
    else:
        if " " in value or "\t" in value:
            problems.append("unquoted value has a space")
    return problems


def check_file(path):
    """Check one .env file.

    Returns a list of "path:line: message" problem strings; an empty
    list means the file is well formed.
    """
    problems = []
    try:
        handle = open(path, encoding="utf-8")
    except OSError as exc:
        return [f"{path}: {exc.strerror or exc}"]
    with handle:
        try:
            lines = handle.readlines()
        except UnicodeDecodeError:
            return [f"{path}: file is not valid UTF-8"]
    seen = {}
    for number, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n").rstrip("\r")
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue  # blank line or comment
        if stripped.startswith("export "):
            stripped = stripped[len("export "):].lstrip()
        if "=" not in stripped:
            problems.append(f"{path}:{number}: line has no '='")
            continue
        key_part, value = stripped.split("=", 1)
        if key_part != key_part.strip() or value.startswith(
            (" ", "\t")
        ):
            problems.append(
                f"{path}:{number}: spaces around '='"
            )
        key = key_part.strip()
        for message in _key_problems(key):
            problems.append(f"{path}:{number}: {message}")
        if key and key in seen:
            problems.append(
                f"{path}:{number}: duplicate key {key!r}"
            )
        elif key:
            seen[key] = number
        for message in _check_value_quoted(value.strip()):
            problems.append(f"{path}:{number}: {message}")
    return problems


def is_env_file(path):
    """True for a file that holds .env settings: `.env` itself, a
    dotted variant such as `.env.example` or `.env.local`, or a
    file whose name ends in `.env` such as `good.env`."""
    name = path.name
    return (
        name == ".env"
        or name.startswith(".env.")
        or name.endswith(".env")
    )


def collect(paths, recursive, excludes):
    """Turn the named files and folders into a list of .env files.

    Returns (files, problems) where problems are fatal
    "path: message" strings for inputs that do not exist.
    """
    files = []
    problems = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            if recursive:
                found_list = sorted(path.rglob("*"))
            else:
                found_list = sorted(path.iterdir())
            for found in found_list:
                if (
                    found.is_file()
                    and ".git" not in found.parts
                    and is_env_file(found)
                    and not _excluded(found, excludes)
                ):
                    files.append(found)
        else:
            problems.append(f"{raw}: no such file or folder")
    return files, problems


def _excluded(path, excludes):
    return any(
        fnmatch.fnmatch(path.name, pattern)
        or fnmatch.fnmatch(str(path), pattern)
        for pattern in excludes
    )


def run(argv=None):
    """Run the checker. Returns an exit code: 0 clean, 1 problems,
    2 usage error."""
    parser = argparse.ArgumentParser(
        prog="dotenv_format_checker",
        description="Check .env files are well formed.",
    )
    parser.add_argument("paths", nargs="*", help=".env files or folders")
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="do not walk folders below the top level",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help="skip files matching this glob (repeatable)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the result as JSON instead of plain text",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {VERSION}"
    )
    args = parser.parse_args(argv)
    if not args.paths:
        parser.error("no files or folders given")
    files, collect_problems = collect(
        args.paths, not args.no_recursive, args.exclude
    )
    results = []
    for path in files:
        found = check_file(path)
        results.append((str(path), found))
    all_problems = collect_problems + [
        problem for _, found in results for problem in found
    ]
    failed = [name for name, found in results if found]
    if args.json:
        payload = {
            "files": [
                {"file": name, "ok": not found, "problems": found}
                for name, found in results
            ],
            "summary": {
                "checked": len(results),
                "ok": len(results) - len(failed),
                "failed": len(failed),
                "problems": len(all_problems),
            },
        }
        if collect_problems:
            payload["errors"] = collect_problems
        print(json.dumps(payload, indent=2))
        print(
            f"Checked {len(results)} file(s), "
            f"{len(all_problems)} problem(s).",
            file=sys.stderr,
        )
    else:
        for problem in all_problems:
            print(f"FAIL {problem}")
        if all_problems:
            print(
                f"Checked {len(results)} file(s), "
                f"{len(all_problems)} problem(s) in "
                f"{len(failed) + len(collect_problems)} "
                f"file(s)."
            )
        else:
            print(
                f"OK — {len(results)} file(s) checked, "
                f".env files are well formed."
            )
    return 1 if all_problems else 0


def main(argv=None):
    try:
        return run(argv)
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
