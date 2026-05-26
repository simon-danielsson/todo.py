#!/usr/bin/env python3

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

    def print(self, icons: bool, colors: bool) -> None:
        ansi_blue: str = "\033[1;34m"
        ansi_rese: str = "\033[0m"
        if not colors:
            ansi_blue = ansi_rese
        months = self.created.days // 30
        days = self.created.days % 30
        file_p = "File"
        comm_p = "Commit"
        month_spacing = " "
        path_spacing = "   "
        if icons:
            month_spacing = " "
            path_spacing = " "
            file_p = ""
            comm_p = "󰘬"
        print(
                f"\n{ansi_blue}◎ {file_p}{ansi_rese}{path_spacing}{self.path.relative_to(Path.cwd())}:{self.line}"
                )
        if self.found_created:
            if months < 1:
                print(f"{ansi_blue}║ {comm_p}{ansi_rese}{month_spacing}{days} days ago")
            else:
                print(
                        f"{ansi_blue}║ {comm_p}{ansi_rese}{month_spacing}{months} month(s) and {days} days ago"
                        )
        print(f"{ansi_blue}║")
        for l in self.content_lines:
            print(f"{ansi_blue}║{ansi_rese} {l}")

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
    icons: bool = field(default=False)
    colors: bool = field(default=True)
    keyword: str = "TODO:"
    target: Path = field(default=Path.cwd())

    def __post_init__(self) -> None:
        if len(sys.argv) <= 1:
            return
        i = 1
        while i < len(sys.argv):
            match sys.argv[i].strip():
                case "-i" | "--icons":
                    self.icons = True
                case "-c" | "--no-color":
                    self.colors = False
                case "-k":
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
            i += 1
        path = Path(sys.argv[-1].strip())
        if path.exists():
            self.target = path.resolve()

def help() -> None:
    print(
            "Usage: todo [OPTIONS]\n"
            "\n"
            "Options:\n"
            '-k  <keyword>    Keyword to search for (default: "TODO:")\n'
            "-i, --icons      Enable nerdfont icons (default: disabled)\n"
            "-c, --no-color   Disable color output (default: enabled)\n"
            "-h, --help       Show this help message and exit"
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
        print("No TODO items were found.")
        return
    for i in todo_items:
        i.print(icons=args.icons, colors=args.colors)

if __name__ == "__main__":
    main()
