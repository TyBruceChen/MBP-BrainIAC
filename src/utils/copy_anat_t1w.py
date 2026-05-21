"""
Copy anat/*T1w.nii.gz files from each subfolder of a parent directory into a destination folder.

Behavior:
- Iterates over immediate subdirectories of the given parent directory.
- For each subdirectory, looks for files matching anat/<pattern> (default "*T1w.nii.gz").
- Copies matched files into the destination directory.
- If a filename collision occurs in the destination, the source subfolder name is prefixed. If that
  still collides, a numeric suffix is appended to make the name unique.

Simple usage:
    python src/utils/copy_anat_t1w.py /path/to/parent /path/to/dest

Options:
    --pattern to change the filename pattern inside anat/
    --preserve-structure to copy into dest/<subfolder>/ (keeps per-subfolder structure)
    --dry-run to only print actions without copying
"""
from pathlib import Path
import shutil
import argparse
from typing import List


def copy_anat_t1w(parent_dir: Path, dest_dir: Path, pattern: str = "*T1w.nii.gz", preserve_structure: bool = False, dry_run: bool = False) -> List[Path]:
    """Copy matching files and return list of destination paths created.

    parent_dir: Path containing subject subfolders (one level deep)
    dest_dir: Path to a directory where files will be copied
    pattern: glob pattern used inside the anat/ folder
    preserve_structure: if True, create dest/<subfolder>/ and copy files there
    dry_run: if True, don't actually copy files
    """
    parent_dir = Path(parent_dir)
    dest_dir = Path(dest_dir)

    if not parent_dir.exists() or not parent_dir.is_dir():
        raise ValueError(f"Parent directory does not exist or is not a directory: {parent_dir}")

    dest_dir.mkdir(parents=True, exist_ok=True)

    copied = []

    for child in sorted(parent_dir.iterdir()):
        if not child.is_dir():
            continue

        anat_dir = child / "anat"
        if not anat_dir.exists() or not anat_dir.is_dir():
            # no anat folder in this subfolder; skip
            continue

        for src in sorted(anat_dir.glob(pattern)):
            if not src.is_file():
                continue

            if preserve_structure:
                target_dir = dest_dir / child.name
                target_dir.mkdir(parents=True, exist_ok=True)
                dest_path = target_dir / src.name
            else:
                dest_path = dest_dir / src.name

            # handle collisions: prefix with source folder name, then add counter if needed
            if dest_path.exists():
                prefixed = dest_dir / f"{child.name}_{src.name}"
                dest_path = prefixed
                counter = 1
                while dest_path.exists():
                    dest_path = dest_dir / f"{child.name}_{counter}_{src.name}"
                    counter += 1

            if dry_run:
                print(f"DRY RUN: would copy {src} -> {dest_path}")
            else:
                shutil.copy2(src, dest_path)
                print(f"Copied {src} -> {dest_path}")

            copied.append(dest_path)

    return copied


def _parse_args():
    p = argparse.ArgumentParser(description="Copy anat/*T1w.nii.gz files from subfolders into a destination folder")
    p.add_argument("parent", help="Parent directory containing subfolders")
    p.add_argument("dest", help="Destination directory to copy files into")
    p.add_argument("--pattern", default="*T1w.nii.gz", help="Glob pattern to match files inside anat/")
    p.add_argument("--preserve-structure", action="store_true", help="Copy files into dest/<subfolder>/ instead of flattening into dest/")
    p.add_argument("--dry-run", action="store_true", help="Don't actually copy files; just print what would be done")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    parent = Path(args.parent)
    dest = Path(args.dest)

    copied = copy_anat_t1w(parent, dest, pattern=args.pattern, preserve_structure=args.preserve_structure, dry_run=args.dry_run)
    print(f"Done. Files copied (or would be copied, if dry-run): {len(copied)}")
