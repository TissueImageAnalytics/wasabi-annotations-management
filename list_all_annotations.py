"""
List all annotations from all WSI items inside a WASABI/Girder folder.

This script:

1. Connects to the WASABI Girder API.
2. Recursively scans a folder for WSI items.
3. Retrieves annotation metadata for each WSI item.
4. Prints all annotations grouped by WSI.
5. Optionally saves the annotation list to a CSV file.

Important:
    This script is read-only.
    It does not delete, upload, or download annotation JSON files.
"""

import csv
import time
from pathlib import Path
from typing import Dict, List

from utils import (
    connect,
    get_annotation_name,
    get_item_annotations,
    iter_items_recursive,
)

# Girder folder containing WSI items. Replace with your own folder ID.
FOLDER_ID = "679b87bf8fd95c173de1ed66"

# Optional CSV output. Set to None if you do not want to save a CSV.
OUTPUT_CSV = Path("wasabi_annotation_list.csv")


# ---------------------------------------------------------------------------
# Listing logic
# ---------------------------------------------------------------------------


def list_annotations_in_folder(
    gc,
    folder_id: str,
) -> List[Dict]:
    """List all annotations from all WSI items in a folder.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    folder_id : str
        Girder folder ID to scan recursively.

    Returns
    -------
    list[dict]
        Flat list of annotation metadata records. Each record contains:
        ``item_name``, ``item_id``, ``annotation_name``, ``annotation_id``,
        ``created``, ``updated``, and ``status``.
    """
    records = []

    items = list(iter_items_recursive(gc, folder_id))
    total_items = len(items)

    print(f"Scanning {total_items} WSI item(s)...")

    for idx, item in enumerate(items, start=1):
        item_id = item["_id"]
        item_name = item["name"]

        print(f"\n[{idx}/{total_items}] WSI item: {item_name}")
        print(f"Item ID: {item_id}")

        start = time.time()

        try:
            annotations = get_item_annotations(gc, item_id, details=False)
        except Exception as e:
            print(f"  FAILED to read annotations: {e}")

            records.append(
                {
                    "item_name": item_name,
                    "item_id": item_id,
                    "annotation_name": "",
                    "annotation_id": "",
                    "created": "",
                    "updated": "",
                    "status": f"failed: {e}",
                }
            )

            continue

        elapsed = time.time() - start

        print(f"  Annotations found: {len(annotations)}")
        print(f"  Request time: {elapsed:.2f}s")

        if not annotations:
            records.append(
                {
                    "item_name": item_name,
                    "item_id": item_id,
                    "annotation_name": "",
                    "annotation_id": "",
                    "created": "",
                    "updated": "",
                    "status": "no_annotations",
                }
            )
            continue

        for record in annotations:
            annotation_name = get_annotation_name(record)
            annotation_id = record.get("_id", "")
            created = record.get("created", "")
            updated = record.get("updated", "")

            print(f"    - {annotation_name} ({annotation_id})")

            records.append(
                {
                    "item_name": item_name,
                    "item_id": item_id,
                    "annotation_name": annotation_name,
                    "annotation_id": annotation_id,
                    "created": created,
                    "updated": updated,
                    "status": "ok",
                }
            )

    return records


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


def save_annotation_list_to_csv(records: List[Dict], output_csv: Path):
    """Save annotation listing records to a CSV file.

    Parameters
    ----------
    records : list[dict]
        Annotation listing records.
    output_csv : Path
        Path to output CSV file.
    """
    if not records:
        print("No records to save.")
        return

    fieldnames = [
        "item_name",
        "item_id",
        "annotation_name",
        "annotation_id",
        "created",
        "updated",
        "status",
    ]

    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"\nSaved CSV: {output_csv}")


if __name__ == "__main__":
    gc = connect()

    records = list_annotations_in_folder(gc=gc, folder_id=FOLDER_ID)

    total_items = len(set(record["item_id"] for record in records))
    total_annotations = sum(1 for record in records if record["annotation_id"])
    failed_items = sum(1 for record in records if record["status"].startswith("failed"))
    empty_items = sum(1 for record in records if record["status"] == "no_annotations")

    print("\nSummary")
    print("-------")
    print(f"WSI items scanned: {total_items}")
    print(f"Annotations found: {total_annotations}")
    print(f"WSI items with no annotations: {empty_items}")
    print(f"WSI items failed: {failed_items}")

    if OUTPUT_CSV is not None:
        save_annotation_list_to_csv(records, OUTPUT_CSV)
