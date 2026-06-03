# WASABI Python Scripts For TIA Internal Users  
Python scripts for managing annotations on the [WASABI](https://wasabi.dcs.warwick.ac.uk) platform, which is powered by [Girder](https://girder.readthedocs.io/).

These scripts interact with the **Annotations** section of WASABI using the Girder REST API.

---

## Scripts

| Script | Description |
|---|---|
| `upload_one.py` | Upload a single annotation JSON to one WSI item |
| `download_one.py` | Download all annotations from one WSI item |
| `delete_one.py` | Delete annotations matching a name suffix from one WSI item |
| `bulk_upload.py` | Bulk upload annotation JSONs to matching WSI items in a folder |
| `bulk_download.py` | Bulk download all annotations from every WSI item in a folder |
| `bulk_delete.py` | Bulk delete annotations matching a name suffix across a folder |
| `list_all_annotations.py` | List all annotations in a folder and optionally save to CSV |
| `tiatoolbox_demo.py` | Run a TIAToolbox model on a directory of WSIs and save annotation stores |
| `annotationstore_to_wasabi_json.py` | Convert TIAToolbox annotation stores (`.db`) to WASABI-format JSON files |

---

## Requirements

- Python 3.10+
- A WASABI account with API key access

Install dependencies:

```bash
pip install -r requirements.txt
```

For the TIAToolbox scripts (`tiatoolbox_demo.py`, `annotationstore_to_wasabi_json.py`), install `TIAToolbox>=2.0` separately:

```bash
pip install tiatoolbox>=2.0
```

---

## Authentication

All scripts read your API key from the `GIRDER_API_KEY` environment variable. Never hard-code credentials.

```bash
export GIRDER_API_KEY=your_api_key_here
```

You can find your API key in WASABI under **Account → API keys**.

See `.env.example` for reference.

---

## Configuration

Each script has a short **Configuration** block near the top. Edit these values before running:

| Variable | Description |
|---|---|
| `API_URL` | WASABI Girder API base URL (default: `https://wasabi.dcs.warwick.ac.uk/api/v1`) |
| `FOLDER_ID` | Girder folder ID (from the URL when browsing a folder of whole-slide images in WASABI) |
| `ITEM_ID` | Girder item ID for a single WSI |
| `OUTPUT_DIR` | Local directory for downloaded annotation JSON files |
| `ANNOTATION_DIR` | Local directory containing annotation JSON files for upload |
| `ANNOTATION_SUFFIX` | Name suffix used to match annotations for deletion or upload |

---

## Usage

### List all annotations in a folder

```bash
python list_all_annotations.py
```

Prints every annotation on every WSI in the folder, grouped by WSI, and optionally saves a CSV.

---

### Download annotations from one WSI

Edit `download_one.py`:
```python
ITEM_ID   = "your_item_id"
OUTPUT_DIR = Path("downloaded_annotations")
```

```bash
python download_one.py
```

Downloads each annotation as a separate JSON file into `downloaded_annotations/<wsi_name>/`.

---

### Bulk download annotations from a folder

Edit `bulk_download.py`:
```python
FOLDER_ID  = "your_folder_id"
OUTPUT_DIR = Path("downloaded_annotations")
```

```bash
python bulk_download.py
```

Output structure:
```
downloaded_annotations/
    wsi_1/
        annotation_1.json
    wsi_2/
        annotation_1.json
        annotation_2.json
```

---

### Upload an annotation to one WSI

Edit `upload_one.py`:
```python
ITEM_ID         = "your_item_id"
ANNOTATION_JSON = Path("annotations/my_annotation.json")
```

```bash
python upload_one.py
```

---

### Bulk upload annotations to a folder

Edit `bulk_upload.py`:
```python
FOLDER_ID      = "your_folder_id"
ANNOTATION_DIR = Path("annotations")
```

Each JSON filename is matched to the corresponding WSI item by name. Existing annotations with the same name are skipped.

Run a dry run first (set `dry_run=True` in `__main__`):

```bash
python bulk_upload.py
```

---

### Delete annotations from one WSI

Edit `delete_one.py`:
```python
ITEM_ID           = "your_item_id"
ANNOTATION_SUFFIX = "_prediction"
```

```bash
python delete_one.py
```

Prints all matching annotations and asks you to type `yes` before deleting.

---

### Bulk delete annotations from a folder

Edit `bulk_delete.py`:
```python
FOLDER_ID         = "your_folder_id"
ANNOTATION_SUFFIX = "_prediction"
```

```bash
python bulk_delete.py
```

Scans every WSI in the folder, prints all matches, and requires `yes` confirmation before any deletion occurs.

---

## Annotation JSON format

These scripts use the standard Girder large-image annotation format:

```json
{
  "annotation": {
    "name": "my_annotation_name",
    "description": "",
    "elements": [
      {
        "type": "polyline",
        "points": [[x1, y1, 0], [x2, y2, 0], ...],
        "closed": true
      }
    ]
  }
}
```

Both wrapped (`{"annotation": {...}}`) and unwrapped (`{"name": ..., "elements": [...]}`) formats are accepted on upload.

---

## TIAToolbox integration workflow

These two scripts form a complete pipeline for generating model predictions on WSIs and publishing them as WASABI annotations.

### Step 1 — Run a TIAToolbox model on a directory of slides

Edit `tiatoolbox_demo.py`:
```python
SLIDES_DIR = Path("/path/to/slides")           # .svs files
OUTPUT_DIR = Path("/path/to/annotation_stores") # output .db files
MODEL      = "grandqc_tissue_detection"
DEVICE     = "cuda"   # or "cpu"
```

```bash
python tiatoolbox_demo.py
```

Produces one `.db` annotation store per slide in `OUTPUT_DIR`.

---

### Step 2 — Convert annotation stores to WASABI JSON

Edit `annotationstore_to_wasabi_json.py`:
```python
INPUT_DIR   = Path("/path/to/annotation_stores")
OUTPUT_DIR  = Path("/path/to/wasabi_jsons")
SAVE_SUFFIX = "_tissue_mask"    # appended to each output filename
ANNOTATOR   = "GrandQC_Model"   # displayed in WASABI as the annotator name
COLOR_DICT  = {
    "Background": [0, 0, 0, 0],
    "Tissue":     [0, 255, 0, 255],
}
```

```bash
python annotationstore_to_wasabi_json.py
```

Produces one WASABI-format JSON per slide in `OUTPUT_DIR`.

---

### Step 3 — Bulk upload to WASABI

Follow the [Bulk upload](#bulk-upload-annotations-to-a-folder) instructions above, pointing `ANNOTATION_DIR` at the JSON directory from Step 2.

---

## Notes

- The `bulk_delete` and `delete_one` scripts require interactive confirmation (`yes`) before any data is deleted. **Use with Caution!!!**
- The `bulk_download` and `download_one` scripts skip files that already exist locally by default (`overwrite=False`).
- The `bulk_upload` script skips annotations that already exist on the target WSI on WASABI by name.

---

