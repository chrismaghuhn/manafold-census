doctor:
    python -m manafold_census.cli doctor

test:
    python -m pytest

lint:
    python -m ruff format --check .
    python -m ruff check .

typecheck:
    python -m mypy src/manafold_census

reproduce:
    python -m manafold_census.cli reproduce

source-discover:
    python -m manafold_census.cli source-discover

source-acquire:
    python -m manafold_census.cli source-acquire

corpus-build:
    python -m manafold_census.cli corpus-build

corpus-check:
    python -m manafold_census.cli corpus-check --synthetic

check: doctor lint typecheck test reproduce corpus-check
