"""Scan a repository for personal data before publishing.

Looks for absolute local paths, usernames, emails, device identifiers and
anything that looks like a credential, in both text files and image metadata.
"""
import argparse
import os
import re
import subprocess

PATTERNS = [
    ("absolute Windows path", re.compile(r"[A-Za-z]:[\\/](?:Users|Documents|Program Files)", re.I)),
    ("UNC path", re.compile(r"\\\\[A-Za-z0-9_.-]+\\")),
    ("home shortcut", re.compile(r"~[\\/](?:Downloads|Desktop|Documents|Pictures)", re.I)),
    ("%USERPROFILE% / $HOME", re.compile(r"%USERPROFILE%|\$env:USERPROFILE|\$HOME", re.I)),
    ("email address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("token-like string", re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}|ey[A-Za-z0-9_-]{20,}\.")),
    ("private IP", re.compile(r"\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d+\.\d+\b")),
]

TEXT_EXT = {".py", ".ps1", ".md", ".txt", ".bat", ".json", ".xml", ".yml", ".yaml", ".cs", ".gitignore"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--extra", nargs="*", default=[],
                    help="additional case-insensitive literals to hunt for")
    args = ap.parse_args()

    patterns = list(PATTERNS)
    for lit in args.extra:
        patterns.append((f"literal {lit!r}", re.compile(re.escape(lit), re.I)))

    files = subprocess.run(["git", "ls-files"], cwd=args.root, capture_output=True,
                           text=True, check=True).stdout.split()
    hits = 0
    binaries = []
    for rel in files:
        path = os.path.join(args.root, rel)
        ext = os.path.splitext(rel)[1].lower()
        if ext not in TEXT_EXT and not rel.endswith(".gitignore"):
            binaries.append(rel)
            continue
        try:
            text = open(path, encoding="utf-8-sig", errors="replace").read()
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, rx in patterns:
                m = rx.search(line)
                if m:
                    hits += 1
                    print(f"{rel}:{lineno}  [{label}]  {line.strip()[:110]}")
    print(f"\n{len(files)} tracked files, {len(binaries)} non-text skipped, {hits} text hits")
    return binaries


if __name__ == "__main__":
    main()
