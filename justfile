set shell := ["powershell.exe", "-NoProfile", "-Command"]

doctor:
    $env:PYTHONPATH = (Join-Path (Get-Location) 'src'); python -m manafold_census.cli doctor

test:
    python -m pytest

lint:
    python -m ruff format --check .
    python -m ruff check .

typecheck:
    python -m mypy src/manafold_census

reproduce:
    $env:PYTHONPATH = (Join-Path (Get-Location) 'src'); python -m manafold_census.cli reproduce

check: doctor lint typecheck test reproduce
