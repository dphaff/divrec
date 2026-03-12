# Dividend Crediting & Reconciliation Engine

A Python project that simulates a UK brokerage dividend processing workflow: reading internal holdings and a CREST-style external snapshot, validating inputs, calculating client dividend credits, reconciling internal and external positions, and producing operational outputs plus audit artefacts.

Python-only CLI project with automated tests (`pytest`) and a `src/` layout. No pandas.

## What this project demonstrates

- input validation and data quality controls
- deterministic money calculations using `Decimal`
- bucket-level reconciliation between internal and external views
- residual tolerance handling for rounding differences
- structured exception handling via break outputs
- repeatable batch outputs with audit logging and checksums

## Repository structure

- `src/divrec/cli.py` - command-line entrypoint for the workflow
- `src/divrec/domain/` - domain models and mapping logic
- `src/divrec/io/` - CSV readers and output writers
- `src/divrec/validate/` - validation rules for internal and CREST inputs
- `src/divrec/calc/` - entitlement, aggregation, and rounding logic
- `src/divrec/recon/` - reconciliation logic and break generation
- `src/divrec/audit/` - audit log and checksum helpers
- `tests/` - automated tests
- `examples/` - human-readable demo datasets
- `data/` - existing test-linked CSV fixtures used by current golden tests

## Workflow overview

1. Read internal holdings CSV
2. Validate internal holdings data
3. Read CREST-style snapshot CSV
4. Validate CREST snapshot data
5. Compute client dividend credit lines
6. Reconcile internal bucket totals against CREST bucket totals
7. Write outputs including credits, reconciliation results, run summary, and audit artefacts

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pytest -q
```

## Example datasets

The `examples/` folder contains:

- `happy_internal.csv` / `happy_crest.csv` - clean passing example
- `recon_fail_internal.csv` / `recon_fail_crest.csv` - controlled reconciliation fail example

## Run a happy-path example

```bash
python -m divrec.cli run \
  --run-id demo-happy-001 \
  --isin GB00B3MLX29 \
  --record-date 2026-02-20 \
  --pay-date 2026-03-05 \
  --dividend-per-share 0.125 \
  --internal examples/happy_internal.csv \
  --crest examples/happy_crest.csv \
  --outdir out/demo-happy-001
```

Expected outcome:

- run completes successfully
- `run_summary.json` reports `PASS`
- output files are written to the run output directory

## Run a controlled fail example

```bash
python -m divrec.cli run \
  --run-id demo-fail-001 \
  --isin GB00B3MLX29 \
  --record-date 2026-02-20 \
  --pay-date 2026-03-05 \
  --dividend-per-share 0.125 \
  --internal examples/recon_fail_internal.csv \
  --crest examples/recon_fail_crest.csv \
  --outdir out/demo-fail-001
```

Expected outcome:

- run completes with a fail status
- `run_summary.json` reports `FAIL`
- `break_report.csv` is written
- audit artefacts are still produced

## Outputs

A run writes outputs to a run-specific folder. Depending on the scenario, outputs include:

- `credit_file.csv` - computed client credit lines
- `recon_report.csv` - bucket-level reconciliation results
- `run_summary.json` - high-level run metadata, status, fail reasons, and checksums
- `audit_log.jsonl` - run lifecycle audit events
- `break_report.csv` - structured exception output for failed reconciliation cases

## Controls and exception handling

This project includes several control layers.

### Input controls

- required field validation
- CSV schema checks
- typed mapping into domain models
- rejection of malformed numeric and date values
- duplicate handling through validation and test coverage

### Calculation controls

- `Decimal` arithmetic for cash values
- explicit rounding behaviour using quantized money values
- deterministic output formatting

### Reconciliation controls

- comparison of internal and CREST shares by bucket
- comparison of internal and CREST cash by bucket
- residual tolerance to allow small rounding differences
- explicit fail reasons when tolerance is exceeded

### Exception handling

- failing buckets are surfaced in reconciliation outputs
- fail reasons are recorded in `run_summary.json`
- `break_report.csv` provides structured exception output
- audit logs and checksums are still produced on failed runs

## Testing

Run the full test suite with:

```bash
pytest -q
```

The test suite covers:

- CSV reading
- domain mapping
- entitlement calculation
- rounding and tolerance behaviour
- reconciliation logic
- CLI happy path
- CLI hardening and negative paths

## Scope and assumptions

Current scope:

- simplified UK brokerage-style dividend processing workflow
- single-event batch run
- internal holdings and CREST-style external snapshot inputs
- deterministic command-line execution
- residual tolerance for small rounding differences

Out of scope for the current version:

- FX / overseas dividend handling
- corporate action variants beyond the current dividend workflow
- production-scale orchestration, scheduling, or database persistence

## Why this matters

This project is designed to demonstrate the kind of controls and operational thinking used in brokerage and financial operations workflows:

- data quality validation before processing
- deterministic cash calculation
- reconciliation between internal and external views
- exception management for mismatches
- auditability and reproducibility of batch outputs