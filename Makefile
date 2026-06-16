.PHONY: env-create env-remove install dev-backend dev-frontend dev build \
        deploy-dev deploy-prod setup-lakebase seed clean lint check-backend

CONDA_ENV = databricks-certifica
CONDA_RUN = conda run -n $(CONDA_ENV) --no-capture-output
PROFILE  ?= DEFAULT

# ─── Conda env ───────────────────────────────────────────────────────────────

env-create:
	@echo "Criando conda env '$(CONDA_ENV)' com Python 3.11..."
	conda create -n $(CONDA_ENV) python=3.11 -y
	@echo "Instalando dependências backend..."
	$(CONDA_RUN) pip install -r backend/requirements.txt
	@echo "Instalando dependências frontend..."
	cd frontend && npm install
	@echo ""
	@echo "Pronto! Ative com: conda activate $(CONDA_ENV)"

env-remove:
	conda env remove -n $(CONDA_ENV) -y

# ─── Local Dev ───────────────────────────────────────────────────────────────

install:
	$(CONDA_RUN) pip install -r backend/requirements.txt
	cd frontend && npm install

dev-backend:
	@echo "Iniciando backend em http://localhost:8005 (config em backend/.env)"
	cd backend && $(CONDA_RUN) uvicorn app.main:app --reload --host 0.0.0.0 --port 8005

dev-frontend:
	@echo "Iniciando frontend em http://localhost:3006"
	cd frontend && npm run dev

dev:
	@echo "Use dois terminais: 'make dev-backend' e 'make dev-frontend'"

# ─── Build ───────────────────────────────────────────────────────────────────

build:
	@echo "Build do frontend..."
	cd frontend && npm run build
	@echo "Frontend compilado em backend/static/"

# ─── Lakebase ──────────────────────────────────────────────────────────────────

setup-lakebase:
	@echo "Criando o projeto Lakebase Autoscaling + populando os dados..."
	cd backend && $(CONDA_RUN) python -m seed.setup_lakebase --seed

seed:
	@echo "Populando Lakebase (requer backend/.env com MOCK_MODE=false)..."
	cd backend && $(CONDA_RUN) python -m seed.seed_lakebase

# ─── Databricks Deploy ─────────────────────────────────────────────────────────

deploy-dev: build
	@echo "Deploy para Databricks (target: dev)..."
	cd backend && databricks bundle deploy --target dev -p $(PROFILE)
	@echo "Iniciando app..."
	cd backend && databricks bundle run --target dev gol_certifica -p $(PROFILE)

deploy-prod: build
	@echo "Deploy para Databricks (target: prod)..."
	cd backend && databricks bundle deploy --target prod -p $(PROFILE)
	@echo "Iniciando app..."
	cd backend && databricks bundle run --target prod gol_certifica -p $(PROFILE)

# ─── Utilities ───────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/static/

lint:
	cd frontend && npm run build

check-backend:
	cd backend && $(CONDA_RUN) python -c "from app.main import app; print('Backend OK')"

test:
	@echo "Testes do backend (pytest)..."
	cd backend && $(CONDA_RUN) pip install -q pytest && $(CONDA_RUN) python -m pytest
	@echo "Type-check do frontend (tsc)..."
	cd frontend && npx tsc --noEmit

test-backend:
	cd backend && $(CONDA_RUN) python -m pytest
