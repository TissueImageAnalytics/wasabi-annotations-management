"""
Download all annotations from one WSI item in WASABI/Girder.

This script:
1. Connects to the WASABI Girder API.
2. Gets all annotations attached to one WSI item.
3. Creates a local output folder for that WSI.
4. Saves each annotation as a separate JSON file.

"""

from pathlib import Path

from utils import (
    connect,
    get_item_annotations,
    get_wsi_item,
    make_annotation_filename,
    safe_filename,
    save_annotation_json,
)

# The Girder item ID for one WSI. Replace with your own.
ITEM_ID = "Replace with your Girder item ID"

# Local folder where annotations will be saved.
OUTPUT_DIR = Path("Replace with your local output directory")


def download_annotations_from_item(
    gc,
    item_id: str,
    output_dir: Path,
    overwrite: bool = False,
    wrapped: bool = True,
):
    """Download all annotations from one WSI item.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    item_id : str
        Girder item ID for the WSI.
    output_dir : Path
        Base local output directory.
    overwrite : bool, default=False
        If False, skip local files that already exist.
        If True, overwrite existing local files.
    wrapped : bool, default=True
        Whether to save annotations inside an outer ``{"annotation": ...}``
        wrapper.

    Returns
    -------
    dict
        Summary of downloaded annotations.
    """
    item = get_wsi_item(gc, item_id)
    item_name = item["name"]

    wsi_folder_name = safe_filename(Path(item_name).stem)
    item_output_dir = output_dir / wsi_folder_name
    item_output_dir.mkdir(parents=True, exist_ok=True)

    annotations = get_item_annotations(gc, item_id)

    saved = []
    skipped_existing = []

    print(f"WSI item: {item_name}")
    print(f"Item ID: {item_id}")
    print(f"Annotations found: {len(annotations)}")
    print(f"Output folder: {item_output_dir}")

    if not annotations:
        print("No annotations found.")
        return {
            "item_name": item_name,
            "item_id": item_id,
            "output_dir": str(item_output_dir),
            "num_annotations": 0,
            "saved": saved,
            "skipped_existing": skipped_existing,
        }

    for index, annotation_record in enumerate(annotations, start=1):
        filename = make_annotation_filename(annotation_record, fallback_index=index)
        output_path = item_output_dir / filename

        if output_path.exists() and not overwrite:
            print(f"Skipping existing local file: {output_path}")
            skipped_existing.append(str(output_path))
            continue

        save_annotation_json(
            annotation_record=annotation_record,
            output_path=output_path,
            wrapped=wrapped,
        )

        print(f"Saved: {output_path}")
        saved.append(str(output_path))

    print("\nSummary")
    print("-------")
    print(f"Annotations found: {len(annotations)}")
    print(f"Files saved: {len(saved)}")
    print(f"Files skipped because they already existed: {len(skipped_existing)}")

    return {
        "item_name": item_name,
        "item_id": item_id,
        "output_dir": str(item_output_dir),
        "num_annotations": len(annotations),
        "saved": saved,
        "skipped_existing": skipped_existing,
    }


if __name__ == "__main__":
    gc = connect()

    download_annotations_from_item(
        gc=gc,
        item_id=ITEM_ID,
        output_dir=OUTPUT_DIR,
        overwrite=False,
        wrapped=True,
    )
