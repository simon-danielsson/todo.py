#!/usr/bin/env python3

import stat
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import subprocess
from typing import Generator

# constants -------------------------------------------------------------------

ANSI_BLU: str = "\033[1;34m"
ANSI_RST: str = "\033[0m"

BLACKLIST: list[str] = [
        "LICENSE",
        "Cargo",
        "nob.h",
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

@dataclass
class Todo:
    path: Path
    line: int
    created_date_found: bool
    created: datetime
    content_lines: list[str]

def collect_files_in_cd() -> list[Path]:
    CD = Path.cwd()
    return [path for path in CD.rglob("*") if not path.is_dir()]

def get_time_created(f: Path, l: int) -> datetime | None:
    if l == 0:
        l += 1
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
                # timeout=0.5,
                )
    except subprocess.CalledProcessError:
        return None
    for line in process.stdout.splitlines():
        if line.startswith("author-time "):
            timestamp = int(line.split()[1])
            return datetime.fromtimestamp(timestamp)

def scan_file(f: Path) -> Generator[Todo]:
    l = 0
    it = f.open(errors="ignore", encoding="utf-8")
    lines = it.readlines()
    for i, l in enumerate(lines):
        if "TODO:" in l:
            # print(f"found: {f.name}")
            td: Todo = Todo(
                    line=i,
                    content_lines=[],
                    path=f,
                    created_date_found=False,
                    created=datetime.now(),
                    )
            created = get_time_created(f=f, l=i)
            if created is not None:
                td.created_date_found = True
                td.created = created
            cl = i
            while cl < len(lines):
                if lines[cl].strip() != "":
                    td.content_lines.append(lines[cl].strip("\n"))
                    cl += 1
                    continue
                break
            yield td
    it.close()

def print_todo(t: list[Todo]) -> None:
    if len(t) < 1:
        print("No TODO items were found.")
        return
    for i in t:
        print(f"\n{ANSI_BLU}File{ANSI_RST} {i.path.relative_to(Path.cwd())}:{i.line}")
        if i.created_date_found:
            print(f"{ANSI_BLU}Date{ANSI_RST} {i.created.date()} {i.created.time()}")
        for l in i.content_lines:
            print(f"{ANSI_BLU}┆{ANSI_RST} {l}")

def main() -> None:
    files = collect_files_in_cd()
    todo_items: list[Todo] = []
    for f in files:
        if f.info.is_symlink():
            continue
        if f.is_dir():
            continue
        if not f.info.exists():
            continue
        if (
                f.stat().st_mode & stat.S_IXUSR
                or f.stat().st_mode & stat.S_IXGRP
                or f.stat().st_mode & stat.S_IXOTH
                ):
            continue

        if not any(n in f.name for n in BLACKLIST):
            todo_items += list(scan_file(f))

    print_todo(todo_items)

if __name__ == "__main__":
    main()
