"""TIAToolbox model demo: predict on WSIs and save results as annotation stores.

This script uses a TIAToolbox semantic segmentation model (GrandQC tissue
detection) to process a directory of SVS whole-slide images and writes the
predictions as SQLiteStore annotation stores — one ``.db`` file per slide.

The output annotation stores can then be converted to WASABI-format JSON using
``annotationstore_to_wasabi_json.py`` and uploaded in bulk with
``bulk_upload.py``.
"""

from pathlib import Path

from tiatoolbox.models.engine.semantic_segmentor import SemanticSegmentor

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SLIDES_DIR = Path("/path/to/slides")  # directory containing .svs files
OUTPUT_DIR = Path("/path/to/annotation_stores")  # where .db files will be saved

MODEL = "grandqc_tissue_detection"
BATCH_SIZE = 16
NUM_WORKERS = 4
DEVICE = "cuda"  # use "cpu" if no GPU is available

# ---------------------------------------------------------------------------

segmentor = SemanticSegmentor(
    model=MODEL,
    batch_size=BATCH_SIZE,
    num_workers=NUM_WORKERS,
)

all_slides = list(SLIDES_DIR.glob("*.svs"))
print(f"Found {len(all_slides)} slides in {SLIDES_DIR}")

results = segmentor.run(
    images=all_slides,
    patch_mode=False,
    auto_get_mask=False,
    output_type="annotationstore",
    save_dir=OUTPUT_DIR,
    overwrite=True,
    device=DEVICE,
)

print(f"Done. Annotation stores saved to {OUTPUT_DIR}")
