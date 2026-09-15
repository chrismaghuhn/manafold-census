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

m4-build:
    python -m manafold_census.cli m4-build --synthetic

m4-check:
    python -m manafold_census.cli m4-check --synthetic

m4-report:
    python -m manafold_census.cli m4-report --synthetic

m5-input-lock-check lock source_lock structural_output analysis_output:
    python -m manafold_census.cli m5-input-lock-check --lock "{{lock}}" --source-lock "{{source_lock}}" --structural-output "{{structural_output}}" --analysis-output "{{analysis_output}}"

m5-authority-check package lock source_lock structural_output analysis_output:
    python -m manafold_census.cli m5-authority-check --package "{{package}}" --lock "{{lock}}" --source-lock "{{source_lock}}" --structural-output "{{structural_output}}" --analysis-output "{{analysis_output}}"

m5-m4-build input_lock authority_package source_lock structural_output analysis_output output:
    python -m manafold_census.cli m5-m4-build --input-lock "{{input_lock}}" --authority-package "{{authority_package}}" --source-lock "{{source_lock}}" --structural-output "{{structural_output}}" --analysis-output "{{analysis_output}}" --output "{{output}}"

m5-bundle-build input_lock authority_package source_lock structural_output analysis_output m4_output output:
    python -m manafold_census.cli m5-bundle-build --input-lock "{{input_lock}}" --authority-package "{{authority_package}}" --source-lock "{{source_lock}}" --structural-output "{{structural_output}}" --analysis-output "{{analysis_output}}" --m4-output "{{m4_output}}" --output "{{output}}"

check: doctor lint typecheck test reproduce corpus-check structural-check
