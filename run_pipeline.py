"""Run the full CoA pipeline on a test PDF — for development/testing.

Usage:
    python run_pipeline.py test_data/BP_T-003-23_COA__Eurofins_.pdf
"""

import json
import logging
import shutil
import sys
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent))

from backend.config import settings
from backend.database import init_db, SessionLocal
from backend.models import CoAJob, Product, ProductTestData, RedactionRegion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("run_pipeline")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <path_to_coa.pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    # Initialize database
    init_db()

    # Copy PDF to uploads
    dest = settings.uploads_path / pdf_path.name
    shutil.copy2(pdf_path, dest)

    # Create job
    db = SessionLocal()
    job = CoAJob(filename=pdf_path.name)
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()

    logger.info("Created job %s for %s", job_id, pdf_path.name)

    # Run pipeline
    from backend.tasks.process_coa import process_coa
    process_coa(job_id)

    # Print results
    db = SessionLocal()
    job = db.query(CoAJob).filter(CoAJob.id == job_id).first()
    print(f"\n{'='*60}")
    print(f"Job: {job.id}")
    print(f"Status: {job.status.value}")
    print(f"Pages: {job.page_count}")

    if job.error_message:
        print(f"Error: {job.error_message}")

    if job.product_id:
        product = db.query(Product).filter(Product.id == job.product_id).first()
        print(f"\nProduct: {product.name}")
        print(f"Lot: {product.lot_number}")
        print(f"Lab: {product.lab}")
        print(f"Test Date: {product.test_date}")
        print(f"Report #: {product.report_number}")
        print(f"Tags: {product.tags}")

        test_data = db.query(ProductTestData).filter(ProductTestData.product_id == product.id).all()
        print(f"\nTest Sections ({len(test_data)}):")
        for td in test_data:
            print(f"  - {td.test_type}: {json.dumps(td.data, indent=2)[:200]}...")

    regions = db.query(RedactionRegion).filter(RedactionRegion.job_id == job_id).all()
    print(f"\nRedaction Regions ({len(regions)}):")
    for r in regions:
        print(f"  Page {r.page}: ({r.x_pct:.1f}%, {r.y_pct:.1f}%) {r.w_pct:.1f}x{r.h_pct:.1f}% — {r.reason} [{r.confidence.value}]")

    print(f"\n{'='*60}")
    db.close()


if __name__ == "__main__":
    main()
