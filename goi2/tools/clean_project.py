"""Remove generated caches; preserve .venv, release bundle, docs and user results."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def prune_build(directory, keep):
    if not directory.exists():
        return
    for child in directory.iterdir():
        if child == keep:
            continue
        if child in keep.parents and not child.is_symlink():
            prune_build(child, keep)
        else:
            remove(child)


def main():
    for parent in (ROOT/'frequency_filter', ROOT/'tests', ROOT/'tools', ROOT/'docs'):
        for path in parent.rglob('__pycache__'):
            remove(path)
    for relative in ('.pytest_cache', 'flutter_app/.dart_tool', 'flutter_app/.idea',
                     'flutter_app/linux/flutter/ephemeral'):
        remove(ROOT/relative)
    prune_build(ROOT/'flutter_app/build',
                ROOT/'flutter_app/build/linux/x64/release/bundle')
    print('Đã dọn cache và build tạm. Giữ .venv, release bundle, tài liệu và results.')


if __name__ == '__main__':
    main()
