"""Tests for dotenv_format_checker — standard library unittest only."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import dotenv_format_checker  # noqa: E402


def write(tmp, name, text, encoding="utf-8"):
    path = Path(tmp) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)
    return path


def run_cli(*args, cwd=None):
    argv = [sys.executable, str(SRC / "dotenv_format_checker.py"), *args]
    return subprocess.run(
        argv, capture_output=True, text=True, cwd=cwd or ROOT
    )


class TestCheckFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def check(self, text):
        path = write(self.tmp.name, ".env", text)
        return dotenv_format_checker.check_file(path)

    def test_clean_file(self):
        self.assertEqual(
            self.check("APP_NAME=fake-app\nAPP_PORT=8080\n"), []
        )

    def test_comments_and_blank_lines_skipped(self):
        self.assertEqual(
            self.check(
                "# a comment\n\n  # indented comment\nAPP_NAME=x\n\n"
            ),
            [],
        )

    def test_export_prefix_allowed(self):
        self.assertEqual(self.check("export APP_NAME=fake-app\n"), [])

    def test_export_prefix_lowercase_key_still_fails(self):
        problems = self.check("export app_name=fake-app\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("lowercase letter", problems[0])

    def test_quoted_value_with_spaces(self):
        self.assertEqual(
            self.check('APP_TITLE="My Fake App"\n'), []
        )

    def test_single_quoted_value_with_spaces(self):
        self.assertEqual(
            self.check("APP_TITLE='My Fake App'\n"), []
        )

    def test_empty_value_allowed(self):
        self.assertEqual(self.check("EMPTY_VALUE=\n"), [])

    def test_value_may_hold_equals(self):
        self.assertEqual(
            self.check("APP_NAME=a=b=c\n"), []
        )

    def test_value_may_hold_url(self):
        self.assertEqual(
            self.check(
                "DATABASE_URL=postgres://fake-user:fake-pass"
                "@localhost:5432/fake-db\n"
            ),
            [],
        )

    def test_key_with_digits_and_underscore(self):
        self.assertEqual(self.check("APP_2_NAME=fake-app\n"), [])

    def test_key_starting_with_underscore(self):
        self.assertEqual(self.check("_PRIVATE=fake-value\n"), [])

    def test_file_with_only_comments_is_clean(self):
        self.assertEqual(
            self.check("# nothing but a comment\n"), []
        )

    def test_empty_file_is_clean(self):
        self.assertEqual(self.check(""), [])

    def test_spaces_before_equals(self):
        problems = self.check("APP_NAME =fake-app\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("spaces around '='", problems[0])
        self.assertIn(":1:", problems[0])

    def test_spaces_after_equals(self):
        problems = self.check("APP_NAME= fake-app\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("spaces around '='", problems[0])

    def test_spaces_both_sides_reported_once(self):
        # One line, one mistake: the message must not repeat.
        problems = self.check("APP_NAME = fake-app\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("spaces around '='", problems[0])

    def test_lowercase_key(self):
        problems = self.check("app_name=fake-app\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("key 'app_name' has a lowercase letter",
                      problems[0])

    def test_mixed_case_key(self):
        problems = self.check("App_Name=fake-app\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("lowercase letter", problems[0])

    def test_key_with_hyphen(self):
        problems = self.check("APP-NAME=fake-app\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("not allowed", problems[0])

    def test_key_with_dot(self):
        problems = self.check("APP.NAME=fake-app\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("not allowed", problems[0])

    def test_key_starting_with_digit(self):
        problems = self.check("2APP=fake-app\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("must start with a letter", problems[0])

    def test_empty_key(self):
        problems = self.check("=no-key\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("empty key", problems[0])

    def test_line_without_equals(self):
        problems = self.check("BROKEN_LINE\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("line has no '='", problems[0])

    def test_duplicate_key(self):
        problems = self.check(
            "APP_NAME=fake-app\nAPP_NAME=again\n"
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("duplicate key 'APP_NAME'", problems[0])
        self.assertIn(":2:", problems[0])

    def test_same_value_twice_is_not_a_duplicate(self):
        self.assertEqual(
            self.check("APP_A=fake\nAPP_B=fake\n"), []
        )

    def test_unquoted_value_with_spaces(self):
        problems = self.check("APP_TITLE=My Fake App\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("unquoted value has a space", problems[0])

    def test_unquoted_value_with_tab(self):
        problems = self.check("APP_TITLE=My\tFake\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("unquoted value has a space", problems[0])

    def test_unterminated_double_quote(self):
        problems = self.check('APP_NOTE="never closed\n')
        self.assertEqual(len(problems), 1)
        self.assertIn("unterminated quote", problems[0])

    def test_unterminated_single_quote(self):
        problems = self.check("APP_NOTE='never closed\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("unterminated quote", problems[0])

    def test_lone_quote_is_unterminated(self):
        problems = self.check('APP_NOTE="\n')
        self.assertEqual(len(problems), 1)
        self.assertIn("unterminated quote", problems[0])

    def test_text_after_closing_quote(self):
        problems = self.check('APP_NOTE="done" junk\n')
        self.assertEqual(len(problems), 1)
        self.assertIn("text after the closing quote", problems[0])

    def test_line_numbers_point_at_the_bad_line(self):
        problems = self.check(
            "APP_NAME=fake-app\nAPP_PORT=8080\nbad_key=x\n"
        )
        self.assertEqual(len(problems), 1)
        self.assertIn(":3:", problems[0])

    def test_missing_file(self):
        problems = dotenv_format_checker.check_file(
            Path(self.tmp.name) / ".env"
        )
        self.assertEqual(len(problems), 1)
        self.assertIn(".env", problems[0])

    def test_non_utf8_file(self):
        path = Path(self.tmp.name) / ".env"
        path.write_bytes(b"APP_NAME=fake\nBAD=\xff\xfe\n")
        problems = dotenv_format_checker.check_file(path)
        self.assertEqual(len(problems), 1)
        self.assertIn("UTF-8", problems[0])

    def test_crlf_line_endings(self):
        self.assertEqual(
            self.check("APP_NAME=fake-app\r\nAPP_PORT=8080\r\n"),
            [],
        )


class TestCollect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_single_file(self):
        path = write(self.tmp.name, ".env", "APP_NAME=x\n")
        files, problems = dotenv_format_checker.collect(
            [str(path)], True, []
        )
        self.assertEqual(files, [path])
        self.assertEqual(problems, [])

    def test_named_file_need_not_be_env_named(self):
        path = write(self.tmp.name, "settings.txt", "APP_NAME=x\n")
        files, _ = dotenv_format_checker.collect(
            [str(path)], True, []
        )
        self.assertEqual(files, [path])

    def test_folder_picks_env_files_only(self):
        write(self.tmp.name, ".env", "APP_NAME=x\n")
        write(self.tmp.name, ".env.example", "APP_NAME=x\n")
        write(self.tmp.name, ".env.local", "APP_NAME=x\n")
        write(self.tmp.name, "notes.txt", "not env\n")
        write(self.tmp.name, "app.py", "APP_NAME = 'x'\n")
        files, problems = dotenv_format_checker.collect(
            [self.tmp.name], True, []
        )
        self.assertEqual(len(files), 3)
        self.assertEqual(problems, [])

    def test_folder_picks_dot_env_suffix_files(self):
        # Files named like good.env end in .env; they count too.
        write(self.tmp.name, "good.env", "APP_NAME=x\n")
        write(self.tmp.name, "bad.env", "bad_key=x\n")
        write(self.tmp.name, "notes.txt", "not env\n")
        files, _ = dotenv_format_checker.collect(
            [self.tmp.name], True, []
        )
        self.assertEqual(
            sorted(f.name for f in files), ["bad.env", "good.env"]
        )

    def test_folder_recursive(self):
        write(self.tmp.name, ".env", "APP_NAME=x\n")
        write(self.tmp.name, "sub/.env", "APP_NAME=x\n")
        files, _ = dotenv_format_checker.collect(
            [self.tmp.name], True, []
        )
        self.assertEqual(len(files), 2)

    def test_folder_no_recursive(self):
        write(self.tmp.name, ".env", "APP_NAME=x\n")
        write(self.tmp.name, "sub/.env", "APP_NAME=x\n")
        files, _ = dotenv_format_checker.collect(
            [self.tmp.name], False, []
        )
        self.assertEqual(len(files), 1)

    def test_git_folder_skipped(self):
        write(self.tmp.name, ".env", "APP_NAME=x\n")
        write(self.tmp.name, ".git/.env", "APP_NAME=x\n")
        files, _ = dotenv_format_checker.collect(
            [self.tmp.name], True, []
        )
        self.assertEqual(len(files), 1)

    def test_exclude_pattern(self):
        write(self.tmp.name, ".env", "APP_NAME=x\n")
        write(self.tmp.name, ".env.local", "APP_NAME=x\n")
        files, _ = dotenv_format_checker.collect(
            [self.tmp.name], True, [".env.local"]
        )
        self.assertEqual([f.name for f in files], [".env"])

    def test_missing_path(self):
        files, problems = dotenv_format_checker.collect(
            [str(Path(self.tmp.name) / ".env")], True, []
        )
        self.assertEqual(files, [])
        self.assertEqual(len(problems), 1)
        self.assertIn("no such file or folder", problems[0])


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_clean_exit_0(self):
        path = write(self.tmp.name, ".env", "APP_NAME=x\n")
        result = run_cli(str(path))
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK — 1 file(s) checked", result.stdout)
        self.assertIn(".env files are well formed", result.stdout)

    def test_bad_exit_1(self):
        path = write(self.tmp.name, ".env", "app_name=x\n")
        result = run_cli(str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL", result.stdout)
        self.assertIn("lowercase letter", result.stdout)

    def test_no_args_exit_2(self):
        result = run_cli()
        self.assertEqual(result.returncode, 2)

    def test_bad_flag_exit_2(self):
        result = run_cli("--nope")
        self.assertEqual(result.returncode, 2)

    def test_version(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0)
        self.assertIn("1.0.0", result.stdout)

    def test_json_output(self):
        path = write(self.tmp.name, ".env", "app_name=x\n")
        result = run_cli(str(path), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["checked"], 1)
        self.assertEqual(payload["summary"]["problems"], 1)
        self.assertIn("lowercase letter",
                      payload["files"][0]["problems"][0])
        # The summary line goes to stderr, stdout stays clean JSON.
        self.assertIn("Checked 1 file(s)", result.stderr)

    def test_json_clean(self):
        path = write(self.tmp.name, ".env", "APP_NAME=x\n")
        result = run_cli(str(path), "--json")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["problems"], 0)

    def test_input_files_unchanged(self):
        text = "app_name=x\n"
        path = write(self.tmp.name, ".env", text)
        run_cli(str(path))
        self.assertEqual(path.read_text(), text)

    def test_folder_argument(self):
        write(self.tmp.name, ".env", "APP_NAME=x\n")
        write(self.tmp.name, ".env.local", "bad_key=x\n")
        result = run_cli(self.tmp.name)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Checked 2 file(s)", result.stdout)

    def test_exclude_flag(self):
        write(self.tmp.name, ".env", "APP_NAME=x\n")
        write(self.tmp.name, ".env.local", "bad_key=x\n")
        result = run_cli(self.tmp.name, "--exclude", ".env.local")
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK — 1 file(s) checked", result.stdout)


class TestExamples(unittest.TestCase):
    def test_sample_output_matches_fresh_run(self):
        result = subprocess.run(
            ["sh", "examples/run-example.sh"],
            capture_output=True, text=True, cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0)
        expected = (ROOT / "examples" / "sample-output.txt").read_text()
        self.assertEqual(result.stdout, expected)

    def test_readme_quoted_outputs(self):
        readme = (ROOT / "README.md").read_text()
        good = run_cli("examples/good.env")
        self.assertEqual(good.returncode, 0)
        self.assertIn(
            "OK — 1 file(s) checked, .env files are well formed.",
            readme,
        )
        bad = run_cli("examples/bad-format.env")
        self.assertEqual(bad.returncode, 1)
        for line in bad.stdout.strip().splitlines():
            self.assertIn(line, readme)
        dupes = run_cli("examples/duplicates.env")
        self.assertEqual(dupes.returncode, 1)
        for line in dupes.stdout.strip().splitlines():
            self.assertIn(line, readme)


class TestHygiene(unittest.TestCase):
    def test_stdlib_only(self):
        import ast

        allowed = {
            "argparse", "fnmatch", "json", "sys", "pathlib",
        }
        test_allowed = allowed | {
            "ast", "subprocess", "tempfile", "unittest",
            "dotenv_format_checker",  # the module under test
        }
        for path, names in [
            (SRC / "dotenv_format_checker.py", allowed),
            (HERE / "test_dotenv_format_checker.py", test_allowed),
        ]:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertIn(alias.name.split(".")[0], names)
                elif isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module.split(".")[0], names)

    def test_no_placeholder_or_secrets(self):
        banned = ["TODO", "FIXME", "coming soon", "lorem",
                  "API_KEY", "api_key", "password="]
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if HERE in path.parents:
                continue  # the test file's own word lists
            if path.suffix == ".pyc":
                continue
            text = path.read_text(errors="ignore")
            for word in banned:
                self.assertNotIn(
                    word, text, f"{word} found in {path}"
                )

    def test_no_absolute_paths(self):
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if HERE in path.parents:
                continue  # the test file's own "/tmp/" literals
            if path.suffix in {".pyc", ".env"}:
                continue
            text = path.read_text(errors="ignore")
            self.assertNotIn("/home/", text, f"absolute path in {path}")
            self.assertNotIn("/tmp/", text, f"absolute path in {path}")

    def test_gitignore_has_env_first(self):
        lines = (ROOT / ".gitignore").read_text().splitlines()
        self.assertEqual(lines[0], ".env")

    def test_fake_git_hooks_todo_does_not_break_scan(self):
        # The Day 21 lesson: a scan that walks .git hits GitHub's own
        # sample hooks containing "TODO". Our scans exclude .git.
        with tempfile.TemporaryDirectory() as tmp:
            hooks = Path(tmp) / ".git" / "hooks"
            hooks.mkdir(parents=True)
            (hooks / "sendemail-validate.sample").write_text(
                "# TODO: fix this\n"
            )
            found = []
            for path in Path(tmp).rglob("*"):
                if not path.is_file():
                    continue
                if ".git" in path.parts or "__pycache__" in path.parts:
                    continue
                if "TODO" in path.read_text(errors="ignore"):
                    found.append(path)
            self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
