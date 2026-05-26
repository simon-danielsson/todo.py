#!/usr/bin/env python3

from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import subprocess
from typing import Generator

# constants -------------------------------------------------------------------

ANSI_GRN: str = "\033[1;32m"
ANSI_BLU: str = "\033[1;34m"
ANSI_RST: str = "\033[0m"

BLACKLIST: list[str] = [
        "LICENSE",
        "todo.py",
        "license",
        ".git",
        "README",
        ".sample",
        ".log",
        "git",
        ]

# program ---------------------------------------------------------------------

@dataclass
class Todo:
    path: Path
    line: int
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
                    str(f.absolute()),
                    ],
                capture_output=True,
                text=True,
                check=True,
                )
    except subprocess.CalledProcessError as e:
        print(
                f"{e.stderr}".strip(),
                f'\nCould not process TODO in "{f.name}", skipping file...\n',
                )
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
            created = get_time_created(f=f, l=i)
            if created == None:
                return
            td: Todo = Todo(line=i, content_lines=[], path=f, created=created)
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
    print(f"{ANSI_GRN}{len(t)} TODO items were found!{ANSI_RST}")

    for i in t:
        print(
                f"\n{ANSI_BLU}File:{ANSI_RST} {i.path.name}:{i.line}"
                f"\n{ANSI_BLU}Date:{ANSI_RST} {i.created.date()} {i.created.time()}"
                f"\n╭────────────────────────"
                )
        for l in i.content_lines:
            print(f"│ {l}")

def main() -> None:
    files = collect_files_in_cd()
    todo_items: list[Todo] = []
    for f in files:
        if not any(n in f.name for n in BLACKLIST):
            todo_items += list(scan_file(f))
        # else:
        #     print(f"ignored: {f.name}")

    print_todo(todo_items)

if __name__ == "__main__":
    main()
