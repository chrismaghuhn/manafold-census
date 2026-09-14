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

source-refresh:
    python -m manafold_census.cli source-refresh

source-fetch-pinned:
    python -m manafold_census.cli source-fetch-pinned

corpus-build:
    python -m manafold_census.cli corpus-build

corpus-check:
    python -m manafold_census.cli corpus-check --synthetic

structural-build:
    python -m manafold_census.cli structural-build

structural-check:
    python -m manafold_census.cli structural-check --synthetic

m3-build:
    python -m manafold_census.cli m3-build --synthetic

m3-check:
    python -m manafold_census.cli m3-check --synthetic

m3-report:
    python -m manafold_census.cli m3-report --synthetic

check: doctor lint typecheck test reproduce corpus-check structural-check
