"""python -m app.seed.benchmark --rows 100000 — load a synthetic IC extract through the full pipeline and time it."""

import argparse
import time
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.engines.connectors.synthetic import write_csv
from app.models import DataSource, Tenant
from app.services import ingestion

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--source", default="SRC-01")
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == "demo"))
        source = db.scalar(select(DataSource).where(DataSource.code == args.source))
        assert tenant and source, "seed the demo tenant first"
        batch = ingestion.create_batch(db, tenant, source, f"benchmark ({args.rows} rows)")
        t0 = time.perf_counter()
        write_csv(Path(batch.storage_path or ""), args.rows, seed=int(batch.code[4:]) + 1000)
        t1 = time.perf_counter()
        ingestion.run_batch(db, batch)
        t2 = time.perf_counter()
    print(
        f"BENCHMARK {batch.code}: {batch.rows_total} rows ({batch.rows_loaded} loaded, "
        f"{batch.rows_quarantined} quarantined) generated in {t1 - t0:.1f}s, ingested in {t2 - t1:.1f}s "
        f"= {batch.rows_total / (t2 - t1):,.0f} rows/s; status {batch.status}"
    )
