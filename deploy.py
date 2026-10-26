#!/usr/bin/env python3
"""Copy public pages + lesson definitions to the local web service."""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def publish_local(dest: Path) -> None:
    if not (ROOT / 'docs' / 'index.html').is_file():
        raise ValueError('Build the public site first: python3 publish.py')
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'docs', dest / 'www', dirs_exist_ok=True)
    shutil.copytree(ROOT / 'lessons', dest / 'lessons', dirs_exist_ok=True)
    # The server program is outside www; token and SQLite DB stay in /var/lib/den-z.
    shutil.copy2(ROOT / 'backend.py', dest / 'backend.py')
    print(f'Published local content to {dest}')


if __name__ == '__main__':
    publish_local(Path(sys.argv[1] if len(sys.argv)>1 else '/srv/den-z').resolve())
