# Developer entry points for setup, tests, linting, data generation, and the component UIs.
# Every target runs inside the project virtualenv at .venv so the system Python stays untouched.
# `make data` generates and conforms both synthetic worlds; pdm-* and supply-* targets run one component package.
VENV := .venv
PYTHON := $(VENV)/bin/python
BOOTSTRAP_PYTHON := python3.11

# Per-machine settings: .env (gitignored, copied from .env.example) is loaded when present and exported to every
# target, so live-model commands ask for the model the local server really serves. `make settings` prints the result.
# Values in .env take precedence over the shell environment; override one for a single run with `make pdm-ask LLM_MODEL=...`.
-include .env
export

.PHONY: setup settings test lint data pdm-data supply-data pdm-oee pdm-predict pdm-alerts pdm-ask pdm-eval pdm-ui \
	supply-eval supply-demo supply-demo-offline supply-ui

setup:
	$(BOOTSTRAP_PYTHON) -m venv $(VENV)
	$(PYTHON) -m pip install -q -e ".[dev]"

settings:
	@$(PYTHON) -c "from llm_gateway.factory import default_selection as d; from pdm_oee.services import settings as p; from supply_ontology.services import settings as s; m = d(); print('LLM_PROVIDER=' + m.provider.value); print('MODEL=' + m.label); print('LLM_BASE_URL=' + m.base_url + ' (local only)'); print('PDM_DATA_DIR=' + str(p.DATA_DIR)); print('SUPPLY_DATA_DIR=' + str(s.DATA_DIR))"

test:
	$(PYTHON) -m pytest -q

lint:
	$(VENV)/bin/ruff check .
	$(PYTHON) tools/check_code_rules.py

data: pdm-data supply-data

pdm-data:
	$(PYTHON) -m pdm_oee.data_pipeline.synthetic.cli
	$(PYTHON) -m pdm_oee.data_pipeline.conform.cli

supply-data:
	$(PYTHON) -m supply_ontology.data_pipeline.synthetic.cli
	$(PYTHON) -m supply_ontology.data_pipeline.conform.cli

pdm-oee:
	$(PYTHON) -m pdm_oee.api.oee_cli

pdm-predict:
	$(PYTHON) -m pdm_oee.api.predict_cli

pdm-alerts:
	$(PYTHON) -m pdm_oee.api.alerts_cli

pdm-ask:
	$(PYTHON) -m pdm_oee.api.investigate_cli ask "$(Q)"

pdm-eval:
	$(PYTHON) -m pdm_oee.api.investigate_cli eval

pdm-ui:
	$(VENV)/bin/streamlit run src/pdm_oee/ui/app.py

supply-eval:
	$(PYTHON) -m supply_ontology.api.eval_cli

supply-demo:
	$(PYTHON) -m supply_ontology.api.demo_cli

supply-demo-offline:
	$(PYTHON) -m supply_ontology.api.demo_cli --offline

supply-ui:
	$(VENV)/bin/streamlit run src/supply_ontology/ui/app.py
