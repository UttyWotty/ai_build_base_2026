# Developer entry points for setup, tests, linting, data generation, and the component UIs.
# Every target runs inside the project virtualenv at .venv so the system Python stays untouched.
# `make data` generates and conforms both worlds and the bridge; `make models` trains the failure model and replays its alerts.
# `make api` and `make web` run the backend and the React app; `make impact A=<alert id>` analyses one alert, `make ask Q="..."` asks the copilot agent, and `make eval` scores it.
# pdm-* and supply-* targets run one component package.
VENV := .venv
PYTHON := $(VENV)/bin/python
BOOTSTRAP_PYTHON := python3.11
FRONTEND := src/frontend

# Per-machine settings: .env (gitignored, copied from .env.example) is loaded when present and exported to every
# target, so live-model commands ask for the model the local server really serves. `make settings` prints the result.
# Values in .env take precedence over the shell environment; override one for a single run with `make pdm-ask LLM_MODEL=...`.
-include .env
export

.PHONY: setup settings test lint data models bridge impact value ask eval api web web-build image deploy pdm-data supply-data pdm-oee pdm-predict pdm-alerts pdm-ask pdm-eval pdm-ui \
	supply-eval supply-demo supply-demo-offline supply-ui

setup:
	$(BOOTSTRAP_PYTHON) -m venv $(VENV)
	$(PYTHON) -m pip install -q -e ".[dev]"
	npm --prefix $(FRONTEND) ci --silent

settings:
	@$(PYTHON) -c "from llm_gateway.factory import default_selection as d; from pdm_oee.services import settings as p; from supply_ontology.services import settings as s; m = d(); print('LLM_PROVIDER=' + m.provider.value); print('MODEL=' + m.label); print('LLM_BASE_URL=' + m.base_url + ' (local only)'); print('PDM_DATA_DIR=' + str(p.DATA_DIR)); print('SUPPLY_DATA_DIR=' + str(s.DATA_DIR))"

test:
	$(PYTHON) -m pytest -q
	npm --prefix $(FRONTEND) test --silent

lint:
	$(VENV)/bin/ruff check .
	$(PYTHON) tools/check_code_rules.py
	npm --prefix $(FRONTEND) run --silent typecheck
	npm --prefix $(FRONTEND) run --silent lint

data: pdm-data supply-data bridge

models: pdm-predict pdm-alerts

bridge:
	$(PYTHON) -m copilot.api.bridge_cli

impact:
	$(PYTHON) -m copilot.api.impact_cli $(A) $(if $(AS_OF),--as-of $(AS_OF))

value:
	$(PYTHON) -m copilot.api.value_cli

ask:
	$(PYTHON) -m copilot.api.agent_cli "$(Q)" $(if $(AS_OF),--as-of $(AS_OF))

eval:
	$(PYTHON) -m copilot.api.agent_eval_cli

api:
	$(VENV)/bin/uvicorn copilot.api.server:app --reload --reload-dir src/backend --port 8000

# The React app with hot reload on port 5173; it proxies /api to `make api`.
web:
	npm --prefix $(FRONTEND) run dev

web-build:
	npm --prefix $(FRONTEND) run build

# Local container check, then Cloud Run deployment (see docs/HANDOVER.md).
image:
	docker build -t ops-copilot .
	docker run --rm -p 8080:8080 --env-file .env -e LLM_PROVIDER=gemini ops-copilot

deploy:
	deploy/cloudrun.sh

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
	$(VENV)/bin/streamlit run src/backend/pdm_oee/ui/app.py

supply-eval:
	$(PYTHON) -m supply_ontology.api.eval_cli

supply-demo:
	$(PYTHON) -m supply_ontology.api.demo_cli

supply-demo-offline:
	$(PYTHON) -m supply_ontology.api.demo_cli --offline

supply-ui:
	$(VENV)/bin/streamlit run src/backend/supply_ontology/ui/app.py
