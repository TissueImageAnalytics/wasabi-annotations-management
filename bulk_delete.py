"""
Delete annotations matching a suffix from all WSI items inside a WASABI/Girder folder.

This script:

1. Connects to the WASABI Girder API.
2. Recursively scans a folder for WSI items.
3. For each WSI item, retrieves all annotations.
4. Finds annotations whose names end with a given suffix.
5. Prints all matched annotations grouped by WSI.
6. Asks the user to type "yes".
7. Deletes the matched annotations only after confirmation.

Important:
    This deletes real WASABI annotations from the "Annotations" section.
    It does not delete files from "Files & Links".
"""

from typing import Dict, List

from utils import (
    connect,
    delete_annotation,
    get_annotation_id,
    get_annotation_name,
    get_item_annotations,
    iter_items_recursive,
)

# Folder containing WSI items. Replace with your own Girder folder ID.
FOLDER_ID = "5e3801a281265220a8d391eb"

# Delete annotations whose names end with this suffix.
ANNOTATION_SUFFIX = "_4_class_eunet"


# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------


def find_matching_annotations_in_folder(
    gc,
    folder_id: str,
    suffix: str,
) -> List[Dict]:
    """Find all annotations ending with a suffix across all WSI items in a folder.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    folder_id : str
        Girder folder ID to scan recursively.
    suffix : str
        Annotation name suffix to match.

    Returns
    -------
    list[dict]
        Each entry contains ``item_name``, ``item_id``, ``annotation_name``,
        and ``annotation_id``.
    """
    matches = []

    for item in iter_items_recursive(gc, folder_id):
        item_id = item["_id"]
        item_name = item["name"]

        print(f"Checking item: {item_name} ({item_id})")

        try:
            annotations = get_item_annotations(
                gc, item_id, details=False, retries=5, sleep_seconds=2
            )
        except Exception as e:
            print(f"FAILED to read annotations for {item_name} ({item_id}): {e}")
            continue

        for record in annotations:
            annotation_name = get_annotation_name(record)

            if annotation_name.endswith(suffix):
                matches.append(
                    {
                        "item_name": item_name,
                        "item_id": item_id,
                        "annotation_name": annotation_name,
                        "annotation_id": get_annotation_id(record),
                    }
                )

    return matches


# ---------------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------------


def print_matches(matches: List[Dict], suffix: str):
    """Print all matched annotations grouped by WSI item.

    Parameters
    ----------
    matches : list[dict]
        Matched annotation records.
    suffix : str
        Suffix used for matching.
    """
    print("\nMatched annotations")
    print("-------------------")
    print(f"Suffix: {suffix!r}")
    print(f"Total annotations matched: {len(matches)}")

    if not matches:
        return

    current_item_id = None

    for match in matches:
        if match["item_id"] != current_item_id:
            current_item_id = match["item_id"]
            print("")
            print(f"WSI item: {match['item_name']}")
            print(f"Item ID:  {match['item_id']}")

        print(f"  Annotation: {match['annotation_name']}")
        print(f"  ID:         {match['annotation_id']}")


def ask_for_confirmation(matches: List[Dict], suffix: str) -> bool:
    """Ask the user to confirm deletion.

    Parameters
    ----------
    matches : list[dict]
        Matched annotations that would be deleted.
    suffix : str
        Suffix used for matching.

    Returns
    -------
    bool
        True only if the user types exactly "yes".
    """
    print_matches(matches, suffix)

    if not matches:
        print("\nNo matching annotations found. Nothing to delete.")
        return False

    print("")
    print("WARNING: This will permanently delete the annotations listed above.")
    return input("Type 'yes' to delete these annotations: ") == "yes"


# ---------------------------------------------------------------------------
# Main deletion function
# ---------------------------------------------------------------------------


def delete_annotations_by_suffix_from_folder(
    gc,
    folder_id: str,
    suffix: str,
    require_confirmation: bool = True,
) -> Dict:
    """Delete all annotations ending with a suffix from all WSI items in a folder.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    folder_id : str
        Girder folder ID to scan recursively.
    suffix : str
        Delete annotations whose names end with this suffix.
    require_confirmation : bool, default=True
        If True, ask user to type "yes" before deleting.
        If False, delete immediately after matching.

    Returns
    -------
    dict
        Summary of matched, deleted, and cancelled status.
    """
    matches = find_matching_annotations_in_folder(gc, folder_id, suffix)

    if not matches:
        print_matches(matches, suffix)
        return {
            "folder_id": folder_id,
            "suffix": suffix,
            "matched": [],
            "deleted": [],
            "cancelled": False,
        }

    if require_confirmation:
        confirmed = ask_for_confirmation(matches, suffix)

        if not confirmed:
            print("\nDeletion cancelled. No annotations were deleted.")
            return {
                "folder_id": folder_id,
                "suffix": suffix,
                "matched": matches,
                "deleted": [],
                "cancelled": True,
            }
    else:
        print_matches(matches, suffix)

    deleted = []

    print("\nDeleting annotations...")
    print("-----------------------")

    for match in matches:
        response = delete_annotation(gc, match["annotation_id"])

        deleted.append({**match, "response": response})

        print(
            f"Deleted {match['annotation_name']} "
            f"from {match['item_name']} "
            f"({match['annotation_id']})"
        )

    print("\nSummary")
    print("-------")
    print(f"Folder ID: {folder_id}")
    print(f"Suffix: {suffix!r}")
    print(f"Matched annotations: {len(matches)}")
    print(f"Deleted annotations: {len(deleted)}")

    return {
        "folder_id": folder_id,
        "suffix": suffix,
        "matched": matches,
        "deleted": deleted,
        "cancelled": False,
    }


if __name__ == "__main__":
    gc = connect()

    delete_annotations_by_suffix_from_folder(
        gc=gc,
        folder_id=FOLDER_ID,
        suffix=ANNOTATION_SUFFIX,
        require_confirmation=True,
    )
