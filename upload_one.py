"""
Upload one annotation JSON file to a single WSI item in WASABI/Girder.

This script:
1. Connects to the WASABI Girder API.
2. Loads a local annotation JSON file.
3. Uploads it to the specified WSI item using the large-image annotation endpoint.

The annotation will appear in the WASABI "Annotations" section,
not in "Files & Links".
"""

from pathlib import Path

from utils import (
    connect,
    get_annotation_name,
    get_item_annotations,
    load_annotation_document,
)

# Replace with your own Girder item ID.
ITEM_ID = "679b87cf8fd95c173de1ed75"

# Path to the local annotation JSON file to upload.
ANNOTATION_JSON = Path("annotations/example_annotation.json")


def upload_annotation_document(gc, item_id: str, annotation_path: Path):
    annotation_doc = load_annotation_document(annotation_path)

    return gc.post(
        f"/annotation?itemId={item_id}",
        json=annotation_doc,
    )


if __name__ == "__main__":
    gc = connect()

    result = upload_annotation_document(gc, ITEM_ID, ANNOTATION_JSON)

    print("Created annotation:")
    print(result)

    print("\nAnnotations now on item:")
    for ann in get_item_annotations(gc, ITEM_ID):
        print(ann["_id"], get_annotation_name(ann))
