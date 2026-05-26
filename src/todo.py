#!/usr/bin/env python3

from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import subprocess
from typing import Generator

# constants -------------------------------------------------------------------

BLACKLIST: list[str] = ["LICENSE", ".git", "README"]

# program ---------------------------------------------------------------------

@dataclass
class Todo:
    path: Path
    line: int
    created: datetime
    content_lines: list[str]

def collect_files_in_cd() -> list[Path]:
    CD = Path.cwd()
    return [path for path in CD.rglob("*") if path.is_file()]

# git blame --line-porcelain -L 42,42 path/to/file | grep '^author-time'
def get_time_created(f: Path, l: int) -> datetime:
    process = subprocess.run(
            [
                "git",
                "blame",
                "--line-porcelain",
                "-L",
                f"{l},{l}",
                f.absolute(),
                "|",
                "grep",
                "'^author-time'",
                ],
            capture_output=True,
            text=True,
            )
    return datetime.fromtimestamp(float(process.stdout.strip()))

def scan_file(f: Path) -> Generator[Todo]:
    l = 0
    it = f.open()
    lines = it.readlines()
    while True:
        try:
            if "TODO" in lines[l]:
                td: Todo = Todo(
                        line=l, content_lines=[], path=f, created=get_time_created(f=f, l=l)
                        )
                td.content_lines.append(lines[l])
                l += 1
                while not lines[l].isspace():
                    try:
                        td.content_lines.append(lines[l])
                        l += 1
                    except:
                        break
                yield td
            l += 1
        except:
            it.close()
            return

def main():
    files = collect_files_in_cd()
    todo_items: list[Todo] = []
    for f in files:
        if not any(n in f.name for n in BLACKLIST):
            try:
                todo_items += list(scan_file(f))
            except:
                break
        else:
            print(f"ignored: {f.name}")

if __name__ == "__main__":
    main()
