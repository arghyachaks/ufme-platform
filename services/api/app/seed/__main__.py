"""python -m app.seed  — seed the demo tenant (no-op unless SEED_DEMO=true or --force)."""

import sys

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.seed import seed_demo

if __name__ == "__main__":
    configure_logging(settings.log_level, settings.log_json)
    if not (settings.seed_demo or "--force" in sys.argv):
        print("SEED_DEMO is not enabled; skipping demo seed.")
        sys.exit(0)
    with SessionLocal.begin() as session:
        seed_demo(session)
    print("Demo data seeded.")
