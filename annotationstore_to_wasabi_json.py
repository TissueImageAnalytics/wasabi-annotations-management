"""Convert TIAToolbox SQLiteStore annotation stores to WASABI-format JSON files.

For each ``.db`` annotation store in the input directory, this script reads the
annotations and writes a WASABI-compatible JSON file that can be uploaded using
``bulk_upload.py``.

Supported geometry types: Polygon, LineString, LinearRing.
"""

import json
import os
from pathlib import Path

from tiatoolbox.annotation.storage import SQLiteStore


def to_wasabi(save_path, annotation_store, color_dict, annotator, line_width=4):
    """Convert a TIAToolbox annotation store to a WASABI-format JSON file.

    Args:
        save_path (Path | str): Output path for the JSON file.
        annotation_store (SQLiteStore): Loaded TIAToolbox annotation store.
        color_dict (dict): Mapping from annotation type name to
            ``[R, G, B, A]`` colour values (0–255).
        annotator (str): Annotator name used as the annotation group and
            the ``name`` field in the output JSON.
        line_width (int): Stroke width for rendered polylines. Default: 4.
    """

    def _make_element(element_id, coords, type_name, type_color, line_width):
        r, g, b, a = type_color
        return {
            "fillColor": f"rgba({r},{g},{b},{a})",
            "id": f"{element_id:024d}",
            "label": {"value": type_name},
            "group": annotator,
            "lineColor": f"rgb({r},{g},{b})",
            "type": "polyline",
            "closed": True,
            "points": coords,
            "lineWidth": line_width,
        }

    elements = []
    for i, ann in enumerate(annotation_store.values()):
        geom = ann.geometry
        if geom.geom_type == "Polygon":
            coords = geom.exterior.coords
        elif geom.geom_type in ("LineString", "LinearRing"):
            coords = geom.coords
        else:
            continue  # skip unsupported geometry types

        pts = [[int(x), int(y), 0] for x, y in coords]
        type_name = ann.properties["type"]
        elements.append(
            _make_element(i, pts, type_name, color_dict[type_name], line_width)
        )

    output = {
        "annotation": {
            "description": "",
            "elements": elements,
            "name": annotator,
        }
    }
    with open(save_path, "w") as fh:
        json.dump(output, fh, indent=4)


if __name__ == "__main__":
    # -----------------------------------------------------------------------
    # Configuration
    # -----------------------------------------------------------------------

    INPUT_DIR = Path("/path/to/annotation_stores")  # directory of .db files
    OUTPUT_DIR = Path("/path/to/wasabi_jsons")  # where JSON files are saved
    SAVE_SUFFIX = "_tissue_mask"  # appended to each output filename
    ANNOTATOR = "GrandQC_Model"  # shown in WASABI as the annotator

    COLOR_DICT = {
        "Background": [0, 0, 0, 0],
        "Tissue": [0, 255, 0, 255],
    }

    # -----------------------------------------------------------------------

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    db_files = list(INPUT_DIR.glob("*.db"))
    print(f"Found {len(db_files)} annotation stores in {INPUT_DIR}")

    for db_path in db_files:
        store = SQLiteStore.open(str(db_path))
        save_path = OUTPUT_DIR / f"{db_path.stem}{SAVE_SUFFIX}.json"
        to_wasabi(save_path, store, COLOR_DICT, ANNOTATOR)
        print(f"  Written: {save_path.name}")

    print(f"Done. JSON files saved to {OUTPUT_DIR}")
