ufme sample data
================

Synthetic intercompany ledgers for trying ufme. No real company data.
Six entities: US01 (USD), UK02 (GBP), DE03 (EUR), IN04 (INR), SG05 (SGD), BR06 (BRL), period August 2026.
They include realistic noise: FX differences, timing lags, split payments, reference typos, and a few
deliberately broken rows (missing partner, bad amount, lower-case currency, duplicates) so you can see
data-quality checks and quarantine at work.

  ic_ledger_small.csv        2,000 lines   quick first run
  ic_ledger_medium.csv      20,000 lines   a realistic month
  ic_ledger_sap_headers.csv  1,000 lines   SAP column names (BELNR, BUKRS, VBUND, WRBTR ...) to show column mapping

How to use: sign in, open More > Data sources, click "Upload file" on a source, choose a file,
then run a reconciliation from Reconciliation > Runs. Full steps: docs/user-manual.html ("Load data").

Regenerate or make bigger files (inside the API container):
  python -m app.engines.connectors.synthetic --rows 100000 --seed 7 --out /tmp/ic_aug.csv
