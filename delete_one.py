"""
Delete selected annotations from one WSI item in WASABI/Girder.

This script:

1. Connects to the WASABI Girder API.
2. Gets metadata for one WSI item.
3. Gets all annotations attached to that WSI item.
4. Finds annotations whose names end with a given suffix.
5. Prints exactly which annotations will be deleted.
6. Asks the user to type "yes".
7. Deletes the matched annotations only if the user confirms.

Important:
    This script deletes real WASABI/Girder annotations from the
    annotation section. It does not delete normal files from "Files & Links".
"""

from typing import Dict, List

from utils import (
    connect,
    delete_annotation,
    get_annotation_id,
    get_annotation_name,
    get_item_annotations,
    get_wsi_item,
)

# Girder item ID for the WSI. Replace with your own.
ITEM_ID = "5e3801c281265220a8d391ed"

# Delete annotations whose annotation name ends with this suffix.
ANNOTATION_SUFFIX = "_4_class_eunet"


# ---------------------------------------------------------------------------
# Matching and confirmation
# ---------------------------------------------------------------------------


def find_annotations_ending_with(
    annotations: List[Dict],
    suffix: str,
) -> List[Dict]:
    """Find annotations whose names end with the given suffix.

    Parameters
    ----------
    annotations : list[dict]
        Annotation records returned by Girder.
    suffix : str
        Suffix to match at the end of the annotation name.

    Returns
    -------
    list[dict]
        Matching annotation records.
    """
    return [
        record for record in annotations if get_annotation_name(record).endswith(suffix)
    ]


def ask_for_confirmation(
    item_name: str,
    item_id: str,
    suffix: str,
    matched_annotations: List[Dict],
) -> bool:
    """Print annotations that will be deleted and ask the user for confirmation.

    Parameters
    ----------
    item_name : str
        Human-readable WSI item name.
    item_id : str
        Girder item ID.
    suffix : str
        Annotation suffix used for matching.
    matched_annotations : list[dict]
        Matched annotation records.

    Returns
    -------
    bool
        True if the user typed exactly "yes"; False otherwise.
    """
    print("\nThe following annotations will be deleted:")
    print("------------------------------------------------")
    print(f"WSI item name: {item_name}")
    print(f"WSI item ID:   {item_id}")
    print(f"Suffix:        {suffix!r}")
    print("------------------------------------------------")

    for record in matched_annotations:
        print(f"Annotation name: {get_annotation_name(record)}")
        print(f"Annotation ID:   {get_annotation_id(record)}")
        print("")

    print("------------------------------------------------")
    print(f"Total annotations to delete: {len(matched_annotations)}")
    print("")

    return input("Type 'yes' to permanently delete these annotations: ") == "yes"


# ---------------------------------------------------------------------------
# Main deletion function
# ---------------------------------------------------------------------------


def delete_annotations_from_item_by_suffix(
    gc,
    item_id: str,
    suffix: str,
    require_confirmation: bool = True,
) -> Dict:
    """Delete all annotations from one WSI item whose names end with a suffix.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    item_id : str
        Girder item ID for the WSI.
    suffix : str
        Delete annotations whose names end with this suffix.
    require_confirmation : bool, default=True
        If True, ask the user to type "yes" before deleting.
        If False, delete immediately after matching.

    Returns
    -------
    dict
        Summary of matched and deleted annotations.
    """
    item = get_wsi_item(gc, item_id)
    item_name = item.get("name", "unknown_item")

    annotations = get_item_annotations(gc, item_id, details=False)
    matched = find_annotations_ending_with(annotations, suffix)

    print(f"WSI item: {item_name}")
    print(f"WSI item ID: {item_id}")
    print(f"Total annotations found: {len(annotations)}")
    print(f"Annotations matching suffix {suffix!r}: {len(matched)}")

    if not matched:
        print("No matching annotations found.")
        return {
            "item_name": item_name,
            "item_id": item_id,
            "suffix": suffix,
            "matched": [],
            "deleted": [],
            "cancelled": False,
        }

    matched_summary = [
        {
            "annotation_id": get_annotation_id(r),
            "annotation_name": get_annotation_name(r),
        }
        for r in matched
    ]

    if require_confirmation:
        confirmed = ask_for_confirmation(item_name, item_id, suffix, matched)

        if not confirmed:
            print("\nDeletion cancelled. No annotations were deleted.")
            return {
                "item_name": item_name,
                "item_id": item_id,
                "suffix": suffix,
                "matched": matched_summary,
                "deleted": [],
                "cancelled": True,
            }

    deleted = []

    print("\nDeleting annotations...")

    for record in matched:
        annotation_id = get_annotation_id(record)
        annotation_name = get_annotation_name(record)

        response = delete_annotation(gc, annotation_id)

        deleted.append(
            {
                "annotation_id": annotation_id,
                "annotation_name": annotation_name,
                "response": response,
            }
        )

        print(f"Deleted: {annotation_name} ({annotation_id})")

    print("\nSummary")
    print("-------")
    print(f"WSI item: {item_name}")
    print(f"Matched annotations: {len(matched)}")
    print(f"Deleted annotations: {len(deleted)}")

    return {
        "item_name": item_name,
        "item_id": item_id,
        "suffix": suffix,
        "matched": matched_summary,
        "deleted": deleted,
        "cancelled": False,
    }


if __name__ == "__main__":
    gc = connect()

    delete_annotations_from_item_by_suffix(
        gc=gc,
        item_id=ITEM_ID,
        suffix=ANNOTATION_SUFFIX,
        require_confirmation=True,
    )
