"""
Bulk upload annotation JSON files to WSI items in WASABI/Girder.

This script does the following:

1. Connects to the WASABI Girder API.
2. Recursively scans a WASABI folder for WSI items.
3. Scans a local folder for annotation JSON files.
4. Matches each WSI item to its corresponding annotation file by name.
5. Checks whether an annotation with the same name already exists on the WSI.
6. Skips existing annotations to avoid duplicates.
7. Uploads missing annotations using the Girder large-image annotation endpoint.

Important:
    This script uses the /annotation endpoint, not uploadFileToItem().
    That means annotations appear in the WASABI "Annotations" section,
    not merely in "Files & Links".
"""

from pathlib import Path

from utils import (
    connect,
    get_item_annotations,
    iter_items_recursive,
    load_annotation_document,
)

# The ID of the WASABI/Girder folder containing the WSI items.
# Replace with your own Girder folder ID.
FOLDER_ID = "5e3801a281265220a8d391eb"

# Local folder containing the annotation JSON files.
# Example:
#   /home/user/annotations
ANNOTATION_DIR = Path("./annotations_for_upload")
ANNOTATION_FILE_SUFFIXES= [
    "_tissue_mask",
    "_annotation_tissue"
]


# ---------------------------------------------------------------------
# Name matching
# ---------------------------------------------------------------------------


def normalise_name(name: str) -> str:
    """Convert a WSI item name or annotation filename to a common matching key.

    Parameters
    ----------
    name : str
        Either a WSI item name or an annotation filename.

    Returns
    -------
    str
        Normalised key used for matching WSI items to annotation files.

    Notes
    -----
    Known suffixes (e.g. ``_tissue_mask``) are stripped so that a file named
    ``1007643_tissue_mask.json`` matches a WSI called ``1007643.svs``.
    """
    stem = Path(name).stem

    known_suffixes = ANNOTATION_FILE_SUFFIXES

    for suffix in known_suffixes:
        if stem.endswith(suffix):
            return stem[: -len(suffix)]

    return stem


def build_annotation_lookup(annotation_dir: Path) -> dict[str, list[Path]]:
    """
    Build a dictionary mapping WSI keys to local annotation JSON files.

    Parameters
    ----------
    annotation_dir : Path
        Local directory containing annotation JSON files.

    Returns
    -------
    dict[str, list[Path]]
        Dictionary of:

            normalised_name -> list of annotation_json_paths

    Example
    -------
    If the local folder contains:

        1007643_4_class_eunet.json
        1007643_5_class_eunet.json

    the returned dictionary may be:

        {
            "1007643": Path(".../1007643_4_class_eunet.json"),
            "1007643": Path(".../1007643_5_class_eunet.json"),
        }

    Notes
    -----
    Multiple annotation files are allowed to map to the same WSI key,
    which enables uploading several annotations per slide.
    """
    # Empty dictionary to store annotation matches.
    lookup: dict[str, list[Path]] = {}

    for path in annotation_dir.glob("*.json"):
        key = normalise_name(path.name)

        # Store this annotation path under the normalised key.
        lookup.setdefault(key, []).append(path)

    return lookup


# ---------------------------------------------------------------------------
# Existing annotation check
# ---------------------------------------------------------------------------


def get_existing_annotation_names(gc, item_id: str) -> set[str]:
    """Return the names of annotations already attached to a WSI item.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    item_id : str
        Girder item ID for the WSI.

    Returns
    -------
    set[str]
        Set of existing annotation names on this item.
    """
    existing = get_item_annotations(gc, item_id, details=False)
    return {
        ann.get("annotation", {}).get("name")
        for ann in existing
        if ann.get("annotation", {}).get("name")
    }


# ---------------------------------------------------------------------------
# Bulk upload logic
# ---------------------------------------------------------------------------


def bulk_upload_annotations(
    gc,
    folder_id: str,
    annotation_dir: Path,
    dry_run: bool = True,
):
    """Bulk upload annotation JSON files to matching WSI items in a Girder folder.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    folder_id : str
        Girder folder ID containing WSI items.
    annotation_dir : Path
        Local directory containing annotation JSON files.
    dry_run : bool, default=True
        If True, only print what would happen without uploading.
        If False, actually upload annotations.

    Returns
    -------
    tuple
        uploaded, skipped_existing, missing_annotations, unmatched_jsons

        uploaded:
            List of annotations that were uploaded.

        skipped_existing:
            List of annotations skipped because an annotation with the same
            name already exists on the WSI.

        missing_annotations:
            List of WASABI WSI items for which no matching local JSON file
            was found.

        unmatched_jsons:
            Set of local JSON file paths that were not matched to any WSI item.

    Workflow
    --------
    For each WSI item in the WASABI folder:

        1. Normalise the WSI item name.
        2. Look for a local JSON file with the same normalised key.
        3. Load the JSON annotation.
        4. Check whether an annotation with the same name already exists.
        5. If it exists, skip it.
        6. If dry_run=True, print what would happen.
        7. If dry_run=False, upload it.
    """
    # Build a local lookup table from annotation filenames.
    #
    # Example:
    #   "1007643_4" -> [Path("1007643_4_class_eunet.json")]
    annotation_lookup = build_annotation_lookup(annotation_dir)

    uploaded = []
    skipped_existing = []
    missing_annotations = []

    # Initially, assume every local JSON file is unmatched.
    # Each time we match one to a WSI, we remove it from this set.
    unmatched_jsons = {
        str(path)
        for paths in annotation_lookup.values()
        for path in paths
    }

    for item in iter_items_recursive(gc, folder_id):
        item_key = normalise_name(item["name"])

        if item_key not in annotation_lookup:
            missing_annotations.append(item["name"])
            continue

        # Get all matching local annotation files for this WSI.
        annotation_paths = annotation_lookup[item_key]

        # Query WASABI for existing annotations on this WSI once.
        existing_names = get_existing_annotation_names(gc, item["_id"])

        for annotation_path in annotation_paths:
            # This JSON has now been matched to a WSI, so it is not unmatched.
            unmatched_jsons.discard(str(annotation_path))

            # Load the annotation document so we can inspect its name.
            annotation_doc = load_annotation_document(annotation_path)

            # This is the annotation name that will appear in WASABI.
            annotation_name = annotation_doc["name"]

            # If an annotation with the same name already exists, skip upload.
            if annotation_name in existing_names:
                print(
                    f"Skipping existing annotation: {annotation_name} "
                    f"already exists on {item['name']}"
                )

                skipped_existing.append({
                    "item_name": item["name"],
                    "item_id": item["_id"],
                    "annotation_name": annotation_name,
                    "annotation_file": str(annotation_path),
                })
                continue

            # Print the successful filename match.
            print(f"Matched: {item['name']}  <--  {annotation_path.name}")

            # If this is a dry run, do not upload anything.
            if dry_run:
                print(f"[DRY RUN] Would upload annotation: {annotation_name}")
                continue

            # Actually upload the annotation to WASABI.
            result = gc.post(
                f"/annotation?itemId={item['_id']}",
                json=annotation_doc,
            )

            # Track this name to avoid duplicate uploads in the same run.
            existing_names.add(annotation_name)

            # Store a record of the successful upload.
            uploaded.append({
                "item_name": item["name"],
                "item_id": item["_id"],
                "annotation_file": str(annotation_path),
                "annotation_name": annotation_name,
                "annotation_id": result.get("_id"),
            })

            # Print confirmation for this item.
            print(f"Uploaded: {annotation_name}")

    print("\nSummary")
    print("-------")
    print(f"Uploaded annotations: {len(uploaded)}")
    print(f"Skipped existing annotations: {len(skipped_existing)}")
    print(f"WSIs without matching JSON: {len(missing_annotations)}")
    print(f"JSON files not matched to any WSI: {len(unmatched_jsons)}")

    if missing_annotations:
        print("\nFirst WSIs without matching annotation:")
        for name in missing_annotations[:20]:
            print(" ", name)

    if unmatched_jsons:
        print("\nFirst unmatched JSON files:")
        for path in list(unmatched_jsons)[:20]:
            print(" ", path)

    return uploaded, skipped_existing, missing_annotations, unmatched_jsons


if __name__ == "__main__":
    gc = connect()

    # First run in dry-run mode to check matching and duplicate detection.
    # bulk_upload_annotations(
    #     gc=gc,
    #     folder_id=FOLDER_ID,
    #     annotation_dir=ANNOTATION_DIR,
    #     dry_run=True,
    # )

    # After verifying the output, set dry_run=False to actually upload.
    bulk_upload_annotations(
        gc=gc,
        folder_id=FOLDER_ID,
        annotation_dir=ANNOTATION_DIR,
        dry_run=False,
    )
