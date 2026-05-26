#!/usr/bin/env python3

"""
todo.py v0.1.5
https://github.com/simon-danielsson/todo.py

Copyright © 2026 Simon Danielsson

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files, to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import stat, subprocess, sys
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Generator

# constants -------------------------------------------------------------------

FALLBACK_DATETIME: datetime = datetime.now()
CD = Path.cwd()

BLACKLIST: list[str] = [
        "LICENSE",
        "CMakeFiles/",
        ".dSYM",
        "Cargo",
        "package",
        "aarch",
        "x86_64",
        "target/",
        "nob.h",
        ".png",
        ".jpg",
        ".gif",
        ".zip",
        ".gz",
        ".psd",
        ".a",
        ".toml",
        ".TAG",
        ".conf",
        ".json",
        "todo.py",
        "license",
        ".git",
        "README",
        ".html",
        ".sample",
        ".log",
        "git",
        ]

# program ---------------------------------------------------------------------

def get_time_created(f: Path, l: int) -> timedelta | None:
    if l < 1:
        l = 1
    try:
        process = subprocess.run(
                [
                    "git",
                    "blame",
                    "--line-porcelain",
                    "-L",
                    f"{l},{l}",
                    str(f.relative_to(Path.cwd())),
                    ],
                capture_output=True,
                text=True,
                check=True,
                timeout=0.01,
                )
    except subprocess.TimeoutExpired:
        return None
    except subprocess.CalledProcessError:
        return None
    except UnicodeDecodeError:
        return None
    for line in process.stdout.splitlines():
        if line.startswith("author-time "):
            created = datetime.fromtimestamp(int(line.split()[1]))
            return datetime.now() - created

@dataclass
class Todo:
    path: Path
    line: int
    created: timedelta = field(default=timedelta(0))
    found_created: bool = False
    content_lines: list[str] = field(default_factory=list)

    def print(self, args: Args) -> None:
        ansi_blue: str = "\033[1;34m"
        ansi_key: str = "\033[4;34m"
        ansi_rese: str = "\033[0m"
        if not args.colors:
            ansi_blue = ""
            ansi_key = ""
            ansi_rese = ""
        months = self.created.days // 30
        days = self.created.days % 30
        print(f"{ansi_blue}")
        created_text = ""
        if self.found_created:
            if months == 0 and days == 0:
                created_text = "@ today"
            elif months < 1:
                created_text = f"@ {days}d ago"
            else:
                created_text = f"@ {months}mo {days}d ago"

        print(
                f"./{self.path.relative_to(Path.cwd())}:{self.line} {created_text}{ansi_rese}"
                )

        preceding_space_to_cut: int = 0

        for l in self.content_lines:
            i = l.find(args.keyword)
            if i == -1:
                continue
            i_end = i + len(args.keyword)
            l = l[:i] + ansi_key + l[i:i_end] + ansi_rese + l[i_end:]
            preceding_space_to_cut = len(l) - len(l.lstrip(" "))
            print(f"    {l[preceding_space_to_cut:]}")

    def __post_init__(self) -> None:
        created = get_time_created(f=self.path, l=self.line)
        if created != None:
            self.found_created = True
            self.created = created

def scan_file(f: Path, kw: str) -> Generator[Todo]:
    lines = f.open(errors="ignore", encoding="utf-8").readlines()
    for i, l in enumerate(lines):
        if kw in l:
            td: Todo = Todo(line=i, path=f)
            cl = i
            while cl < len(lines):
                if lines[cl].strip() != "":
                    td.content_lines.append(lines[cl].strip("\n"))
                    cl += 1
                    continue
                break
            yield td

def should_skip(f: Path) -> bool:
    if f.info.is_symlink() or f.is_dir():
        return True
    if not f.info.exists():
        return True
    if (  # is executable
        f.stat().st_mode & stat.S_IXUSR
        or f.stat().st_mode & stat.S_IXGRP
        or f.stat().st_mode & stat.S_IXOTH
        ):
        return True
    if any(n in f.absolute().as_uri() for n in BLACKLIST):
        return True
    return False

@dataclass
class Args:
    help: bool = field(default=False)
    colors: bool = field(default=True)
    keyword: str = "TODO:"
    target: Path = field(default=Path.cwd())

    def __post_init__(self) -> None:
        if len(sys.argv) <= 1:
            return
        i = 1
        while i < len(sys.argv):
            match sys.argv[i].strip():
                case "-n" | "--no-color":
                    self.colors = False
                case "-k" | "--key":
                    try:
                        if sys.argv[i + 1].startswith("-"):
                            print('No keyword added after "-k" flag.')
                            exit(1)
                        self.keyword = sys.argv[i + 1].strip()
                    except Exception:
                        print('No keyword added after "-k" flag.')
                        exit(1)
                case "--help" | "-h":
                    self.help = True
                case _:
                    return

            i += 1
        path = Path(sys.argv[-1].strip())
        if path.exists():
            self.target = path.resolve()

def help() -> None:
    print(
            "Usage: todo [OPTIONS]\n"
            "\n"
            "Options:\n"
            '-k, --key <keyword>    Keyword to search for (default: "TODO:")\n'
            "-n, --no-color         Disable color output (default: enabled)\n"
            "-h, --help             Show this help message and exit"
            )

def main() -> None:
    args = Args()
    if args.help:
        help()
        return

    files = [path for path in args.target.rglob("*") if not path.is_dir()]

    todo_items: list[Todo] = []
    for f in files:
        if should_skip(f):
            continue
        todo_items += list(scan_file(f, args.keyword))

    if len(todo_items) < 1:
        print("No tasks were found.")
        return
    for i in todo_items:
        i.print(args=args)

if __name__ == "__main__":
    main()
