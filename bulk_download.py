"""
Bulk download annotation JSON files from WSI items in WASABI/Girder.

This script does the following:

1. Connects to the WASABI Girder API.
2. Recursively scans a WASABI/Girder folder for WSI items.
3. For each WSI item, finds all annotations attached to that item.
4. Creates one local folder per WSI.
5. Saves each annotation as a separate JSON file inside that WSI folder.

Output structure example:

    downloaded_annotations/
        1007643/
            1007643_4_class_eunet.json
            another_annotation.json
        1007644/
            1007644_4_class_eunet.json

Important:
    This downloads real WASABI/Girder large-image annotations from the
    "Annotations" section. It does not download normal attached files from
    "Files & Links".
"""

from pathlib import Path

from utils import (
    connect,
    get_item_annotations,
    iter_items_recursive,
    make_annotation_filename,
    safe_filename,
    save_annotation_json,
)

# Girder folder containing WSI items. Replace with your own folder ID.
FOLDER_ID = "Replace with your Girder folder ID"

# Local output folder where downloaded annotations will be saved.
OUTPUT_DIR = Path("Replace with your local output directory")


# ---------------------------------------------------------------------------
# Per-item download
# ---------------------------------------------------------------------------


def get_item_output_dir(item: dict, output_dir: Path) -> Path:
    """Create and return the output folder for one WSI item.

    Parameters
    ----------
    item : dict
        Girder item dictionary.
    output_dir : Path
        Base local output directory.

    Returns
    -------
    Path
        Directory where this WSI's annotations should be saved.
    """
    item_name = safe_filename(Path(item["name"]).stem)
    item_dir = output_dir / item_name
    item_dir.mkdir(parents=True, exist_ok=True)
    return item_dir


def download_annotations_for_item(
    gc,
    item: dict,
    output_dir: Path,
    overwrite: bool = False,
    wrapped: bool = True,
) -> dict:
    """Download all annotations for one WSI item.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    item : dict
        Girder item dictionary for the WSI.
    output_dir : Path
        Base local output directory.
    overwrite : bool, default=False
        If False, skip local files that already exist.
        If True, overwrite existing local JSON files.
    wrapped : bool, default=True
        Whether to save annotations inside an outer ``{"annotation": ...}``
        wrapper.

    Returns
    -------
    dict
        Summary for this WSI item.
    """
    item_id = item["_id"]
    item_name = item["name"]

    item_dir = get_item_output_dir(item, output_dir)
    annotations = get_item_annotations(gc, item_id)

    saved = []
    skipped_existing = []

    if not annotations:
        print(f"No annotations found for: {item_name}")
        return {
            "item_name": item_name,
            "item_id": item_id,
            "output_dir": str(item_dir),
            "num_annotations": 0,
            "saved": saved,
            "skipped_existing": skipped_existing,
        }

    print(f"Found {len(annotations)} annotation(s) for: {item_name}")

    for index, annotation_record in enumerate(annotations, start=1):
        filename = make_annotation_filename(annotation_record, fallback_index=index)
        output_path = item_dir / filename

        if output_path.exists() and not overwrite:
            print(f"  Skipping existing local file: {output_path}")
            skipped_existing.append(str(output_path))
            continue

        save_annotation_json(
            annotation_record=annotation_record,
            output_path=output_path,
            wrapped=wrapped,
        )

        print(f"  Saved: {output_path}")
        saved.append(str(output_path))

    return {
        "item_name": item_name,
        "item_id": item_id,
        "output_dir": str(item_dir),
        "num_annotations": len(annotations),
        "saved": saved,
        "skipped_existing": skipped_existing,
    }


# ---------------------------------------------------------------------------
# Bulk download logic
# ---------------------------------------------------------------------------


def bulk_download_annotations(
    gc,
    folder_id: str,
    output_dir: Path,
    overwrite: bool = False,
    wrapped: bool = True,
):
    """Bulk download annotations from every WSI item under a Girder folder.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    folder_id : str
        Girder folder ID containing WSI items.
    output_dir : Path
        Local directory where annotation folders will be created.
    overwrite : bool, default=False
        If False, skip local annotation JSON files that already exist.
        If True, overwrite existing local files.
    wrapped : bool, default=True
        If True, save JSON as ``{"annotation": {...}}``.
        If False, save only the inner annotation object.

    Returns
    -------
    list[dict]
        Per-item download summaries.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    summaries = []

    for item in iter_items_recursive(gc, folder_id):
        summary = download_annotations_for_item(
            gc=gc,
            item=item,
            output_dir=output_dir,
            overwrite=overwrite,
            wrapped=wrapped,
        )
        summaries.append(summary)

    total_items = len(summaries)
    total_annotations = sum(s["num_annotations"] for s in summaries)
    total_saved = sum(len(s["saved"]) for s in summaries)
    total_skipped = sum(len(s["skipped_existing"]) for s in summaries)

    print("\nSummary")
    print("-------")
    print(f"WSI items scanned: {total_items}")
    print(f"Annotations found: {total_annotations}")
    print(f"Annotation files saved: {total_saved}")
    print(f"Local files skipped because they already existed: {total_skipped}")
    print(f"Output directory: {output_dir}")

    return summaries


if __name__ == "__main__":
    gc = connect()

    bulk_download_annotations(
        gc=gc,
        folder_id=FOLDER_ID,
        output_dir=OUTPUT_DIR,
        overwrite=False,
        wrapped=True,
    )
