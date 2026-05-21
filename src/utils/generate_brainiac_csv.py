"""
Generate a CSV compatible with src/get_brainiac_features.py / BrainAgeDataset

Scans a directory for T1w NIfTI files (default pattern "*T1w.nii.gz") and writes a CSV
with columns: pat_id,label,dataset. pat_id is the filename without the .nii or .nii.gz
extension so that BrainAgeDataset will locate the image as pat_id + ".nii.gz" in the
root_dir provided to get_brainiac_features.py.

Usage:
    python src/utils/generate_brainiac_csv.py /path/to/images output.csv

Options:
    --pattern    glob pattern (default "*T1w.nii.gz")
    --recursive  search recursively
    --label      numeric label to write for every file (default 0)
    --dataset    dataset value to write (default empty string)
    --overwrite  overwrite output CSV if it exists
"""
from pathlib import Path
import argparse
import pandas as pd
from typing import List


def _pat_id_from_filename(name: str) -> str:
    """Return pat_id appropriate for BrainAgeDataset (remove .nii.gz or .nii)

    Examples:
        sample.nii.gz -> sample
        sample.nii -> sample
        sample -> sample
    """
    if name.endswith(".nii.gz"):
        return name[:-7]
    if name.endswith(".nii"):
        return name[:-4]
    return Path(name).stem


def find_files(src: Path, pattern: str = "*.nii.gz", recursive: bool = False) -> List[Path]:
    if recursive:
        return sorted(src.rglob(pattern))
    return sorted(src.glob(pattern))


def generate_csv(src_dir: str, out_csv: str, pattern: str = "*.nii.gz", recursive: bool = False, label: float = 0, dataset: str = "", overwrite: bool = False) -> Path:
    src = Path(src_dir)
    if not src.exists() or not src.is_dir():
        raise ValueError(f"Source directory does not exist or is not a directory: {src}")

    out_path = Path(out_csv)
    if out_path.exists() and not overwrite:
        raise FileExistsError(f"Output CSV exists: {out_path} (use --overwrite to replace)")

    files = find_files(src, pattern=pattern, recursive=recursive)
    if not files:
        print(f"No files found in {src} matching pattern '{pattern}'")

    rows = []
    seen = set()
    for f in files:
        name = f.name
        pat_id = _pat_id_from_filename(name)
        if pat_id in seen:
            print(f"Warning: duplicate pat_id '{pat_id}' generated from {f}; skipping duplicate")
            continue
        seen.add(pat_id)
        rows.append({"pat_id": pat_id, "label": label, "dataset": dataset})

    df = pd.DataFrame(rows, columns=["pat_id", "label", "dataset"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return out_path


def _parse_args():
    p = argparse.ArgumentParser(description="Generate CSV for get_brainiac_features.py from T1w NIfTI files")
    p.add_argument("src_dir", help="Directory containing T1w .nii(.gz) files")
    p.add_argument("out_csv", help="Output CSV path to write")
    p.add_argument("--pattern", default="*.nii.gz", help="Glob pattern to match files (default '*T1w.nii.gz')")
    p.add_argument("--recursive", action="store_true", help="Search recursively")
    p.add_argument("--label", type=float, default=0, help="Numeric label value to populate (default 0)")
    p.add_argument("--dataset", default="", help="Dataset column value to populate (default empty)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite output CSV if it exists")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    generate_csv(args.src_dir, args.out_csv, pattern=args.pattern, recursive=args.recursive, label=args.label, dataset=args.dataset, overwrite=args.overwrite)
