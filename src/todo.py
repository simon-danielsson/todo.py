#!/usr/bin/env python3

import stat
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import subprocess
from typing import Generator

# constants -------------------------------------------------------------------

ANSI_BLU: str = "\033[1;34m"
ANSI_RST: str = "\033[0m"

FALLBACK_DATETIME: datetime = datetime.now()
CD = Path.cwd()

BLACKLIST: list[str] = [
        "LICENSE",
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

def get_time_created(f: Path, l: int) -> datetime | None:
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
    for line in process.stdout.splitlines():
        if line.startswith("author-time "):
            return datetime.fromtimestamp(int(line.split()[1]))

@dataclass
class Todo:
    path: Path
    line: int
    found_created: bool = False
    created: datetime = field(default=FALLBACK_DATETIME)
    content_lines: list[str] = field(default_factory=list)

    def print(self) -> None:
        print(
                f"\n{ANSI_BLU}File{ANSI_RST} {self.path.relative_to(Path.cwd())}:{self.line}"
                )
        if self.found_created:
            print(
                    f"{ANSI_BLU}Date{ANSI_RST} {self.created.date()} {self.created.time()}"
                    )
        for l in self.content_lines:
            print(f"{ANSI_BLU}┆{ANSI_RST} {l}")

    def __post_init__(self) -> None:
        created = get_time_created(f=self.path, l=self.line)
        if created != None:
            self.found_created = True
            self.created = created

def scan_file(f: Path) -> Generator[Todo]:
    lines = f.open(errors="ignore", encoding="utf-8").readlines()
    for i, l in enumerate(lines):
        if "TODO:" in l:
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

def main() -> None:
    files = [path for path in CD.rglob("*") if not path.is_dir()]
    todo_items: list[Todo] = []
    for f in files:
        if should_skip(f):
            continue
        todo_items += list(scan_file(f))

    if len(todo_items) < 1:
        print("No TODO items were found.")
        return
    for i in todo_items:
        i.print()

if __name__ == "__main__":
    main()
