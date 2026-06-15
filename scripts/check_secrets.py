"""Pre-commit hook: detect accidentally staged secrets."""

import re
import subprocess
import sys

PATTERNS = [
    (r"(?i)aws_secret_access_key\s*=\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?", "AWS secret key"),
    (r"(?i)api_key\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]", "API key"),
    (r"sk-[A-Za-z0-9]{48}", "OpenAI/Anthropic API key"),
    (r"(?i)password\s*=\s*['\"][^'\"]{8,}['\"]", "Hardcoded password"),
]

ALLOWLIST = [
    "minioadmin",  # Local dev default, not a real secret
    "kyulai",      # Local dev postgres password
]


def get_staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )
    return [f for f in result.stdout.splitlines() if f.endswith(".py")]


def check_file(path: str) -> list[str]:
    violations = []
    try:
        with open(path) as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return violations

    for pattern, label in PATTERNS:
        for match in re.finditer(pattern, content):
            value = match.group()
            if any(allowed in value for allowed in ALLOWLIST):
                continue
            line_num = content[: match.start()].count("\n") + 1
            violations.append(f"{path}:{line_num} — possible {label}: {value[:40]}...")

    return violations


def main() -> int:
    files = get_staged_files()
    all_violations = []
    for f in files:
        all_violations.extend(check_file(f))

    if all_violations:
        print("Possible secrets detected — review before committing:")
        for v in all_violations:
            print(f"  {v}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
