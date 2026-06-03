"""Shared utilities for WASABI/Girder annotation scripts."""

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List

import girder_client
import requests

API_URL = "https://wasabi.dcs.warwick.ac.uk/api/v1"
API_KEY = os.environ.get("GIRDER_API_KEY", "")


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def connect() -> girder_client.GirderClient:
    """Connect to the WASABI Girder API and authenticate using an API key.

    Returns
    -------
    girder_client.GirderClient
        Authenticated Girder client.

    Raises
    ------
    RuntimeError
        If ``GIRDER_API_KEY`` environment variable is not set.
    """
    if not API_KEY:
        raise RuntimeError(
            "GIRDER_API_KEY environment variable is not set.\n"
            "Set it with:  export GIRDER_API_KEY=your_api_key_here"
        )
    gc = girder_client.GirderClient(apiUrl=API_URL)
    gc.authenticate(apiKey=API_KEY)
    return gc


# ---------------------------------------------------------------------------
# Folder traversal
# ---------------------------------------------------------------------------


def iter_items_recursive(gc: girder_client.GirderClient, folder_id: str):
    """Recursively yield all items inside a Girder folder.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    folder_id : str
        ID of the Girder folder to scan.

    Yields
    ------
    dict
        Girder item dictionaries. In this context each item usually
        corresponds to one WSI.
    """
    for item in gc.listItem(folder_id):
        yield item

    for subfolder in gc.listFolder(folder_id):
        yield from iter_items_recursive(gc, subfolder["_id"])


# ---------------------------------------------------------------------------
# Item / annotation accessors
# ---------------------------------------------------------------------------


def get_wsi_item(gc: girder_client.GirderClient, item_id: str) -> Dict:
    """Return Girder metadata for one WSI item.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    item_id : str
        Girder item ID.

    Returns
    -------
    dict
        Girder item metadata.
    """
    return gc.get(f"/item/{item_id}")


def get_item_annotations(
    gc: girder_client.GirderClient,
    item_id: str,
    details: bool = True,
    retries: int = 3,
    sleep_seconds: float = 1.0,
) -> List[Dict]:
    """Get all annotations attached to one WSI item.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    item_id : str
        Girder item ID.
    details : bool, default=True
        If True, fetch full annotation data including all geometry elements.
        If False, fetch metadata only (name, id) — faster and used when
        element geometry is not needed (e.g. listing or deleting by name).
    retries : int, default=3
        Number of retry attempts on transient network errors.
    sleep_seconds : float, default=1.0
        Delay in seconds between retry attempts.

    Returns
    -------
    list[dict]
        Annotation records returned by Girder.

    Raises
    ------
    RuntimeError
        If all retry attempts are exhausted.
    """
    params = (
        {}
        if details
        else {
            "limit": 0,
            "offset": 0,
            "sort": "lowerName",
            "sortdir": 1,
            "details": "false",
        }
    )

    last_error = None

    for attempt in range(1, retries + 1):
        try:
            return gc.get(f"/annotation/item/{item_id}", parameters=params)

        except (
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as e:
            last_error = e
            print(
                f"Failed to read annotations for item {item_id} "
                f"(attempt {attempt}/{retries}). Retrying..."
            )
            time.sleep(sleep_seconds)

    raise RuntimeError(
        f"Failed to read annotations for item {item_id} after {retries} attempts"
    ) from last_error


def get_annotation_name(annotation_record: Dict) -> str:
    """Extract the annotation name from a Girder annotation record.

    Parameters
    ----------
    annotation_record : dict
        Annotation record returned by Girder.

    Returns
    -------
    str
        Annotation name, or an empty string if missing.
    """
    return annotation_record.get("annotation", {}).get("name", "")


def get_annotation_id(annotation_record: Dict) -> str:
    """Extract the Girder annotation ID from an annotation record.

    Parameters
    ----------
    annotation_record : dict
        Annotation record returned by Girder.

    Returns
    -------
    str
        Girder annotation ID.

    Raises
    ------
    ValueError
        If the annotation record has no ``"_id"`` field.
    """
    annotation_id = annotation_record.get("_id")

    if not annotation_id:
        raise ValueError(f"Annotation record has no '_id': {annotation_record}")

    return annotation_id


# ---------------------------------------------------------------------------
# Annotation CRUD
# ---------------------------------------------------------------------------


def delete_annotation(
    gc: girder_client.GirderClient,
    annotation_id: str,
) -> Dict:
    """Delete one annotation by Girder annotation ID.

    Parameters
    ----------
    gc : girder_client.GirderClient
        Authenticated Girder client.
    annotation_id : str
        Girder annotation ID.

    Returns
    -------
    dict
        Girder API response.
    """
    return gc.delete(f"/annotation/{annotation_id}")


def load_annotation_document(path: Path, name: str | None = None) -> Dict:
    """Load a local annotation JSON file in the format expected by Girder.

    Parameters
    ----------
    path : Path
        Path to the local annotation JSON file.
    name : str, optional
        Override the annotation name. If omitted and the JSON has no name,
        the file stem is used.

    Returns
    -------
    dict
        Annotation document suitable for ``POST /annotation?itemId=<id>``.

    Notes
    -----
    Handles both wrapped ``{"annotation": {...}}`` and unwrapped ``{...}``
    input formats.

    Raises
    ------
    ValueError
        If the JSON file does not contain an ``"elements"`` field.
    """
    with open(path, "r") as f:
        doc = json.load(f)

    annotation_doc = doc["annotation"] if "annotation" in doc else doc

    if not annotation_doc.get("name"):
        annotation_doc["name"] = name or path.stem

    if "description" not in annotation_doc:
        annotation_doc["description"] = ""

    if "elements" not in annotation_doc:
        raise ValueError(f"No 'elements' field found in annotation file: {path}")

    return annotation_doc


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------


def safe_filename(name: str) -> str:
    """Convert an arbitrary WASABI/Girder name into a safe local filename.

    Parameters
    ----------
    name : str
        Original item or annotation name.

    Returns
    -------
    str
        Filesystem-safe filename component.
    """
    if not name:
        name = "unnamed"

    name = re.sub(r'[<>:"/\\|?*\n\r\t]+', "_", name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name)
    name = name.strip(" ._")

    return name or "unnamed"


def make_annotation_filename(annotation_record: Dict, fallback_index: int) -> str:
    """Build a safe JSON filename for one annotation record.

    Parameters
    ----------
    annotation_record : dict
        Annotation record returned by Girder.
    fallback_index : int
        Index used when the annotation has no name.

    Returns
    -------
    str
        Filename ending in ``.json``.
    """
    annotation_name = (
        get_annotation_name(annotation_record) or f"annotation_{fallback_index:03d}"
    )

    filename = safe_filename(annotation_name)

    if not filename.endswith(".json"):
        filename += ".json"

    return filename


def save_annotation_json(
    annotation_record: Dict,
    output_path: Path,
    wrapped: bool = True,
):
    """Save one annotation record as a JSON file.

    Parameters
    ----------
    annotation_record : dict
        Full annotation record returned by Girder.
    output_path : Path
        Local path to write.
    wrapped : bool, default=True
        If True, save as ``{"annotation": {...}}``.
        If False, save only the inner annotation object.

    Notes
    -----
    Use ``wrapped=True`` so downloaded files are compatible with the
    upload scripts, which expect the ``{"annotation": ...}`` wrapper.
    """
    annotation_doc = annotation_record.get("annotation", annotation_record)
    data_to_save = {"annotation": annotation_doc} if wrapped else annotation_doc

    with open(output_path, "w") as f:
        json.dump(data_to_save, f, indent=2)
