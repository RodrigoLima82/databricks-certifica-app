.PHONY: env-create env-remove install dev-backend dev-frontend dev build \
        seed deploy-prod deploy-backend clean lint check-backend test test-backend

CONDA_ENV = certifica
CONDA_RUN = conda run -n $(CONDA_ENV) --no-capture-output

# ─── Databricks Apps (deploy atual) ─────────────────────────────────────────────
# Configure um profile:  databricks auth login --host <workspace> --profile <nome>
PROFILE ?= DEFAULT

# ─── AWS (App Runner via ECR — host alternativo, não usado no deploy atual) ─────
AWS_REGION ?= us-east-1
ECR_REPO   ?= certifica
IMAGE_TAG  ?= latest

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

# ─── Seed do Postgres (Lakebase / RDS) ───────────────────────────────────────

seed:
	@echo "Criando schema + populando o Postgres (requer backend/.env com MOCK_MODE=false)..."
	cd backend && $(CONDA_RUN) python -m seed.seed_db

# ─── Databricks Apps Deploy (deploy atual) ──────────────────────────────────────

deploy-prod: build
	@echo "Deploy para Databricks Apps (target: prod)..."
	cd backend && databricks bundle deploy --target prod -p $(PROFILE)
	cd backend && databricks bundle run --target prod certifica -p $(PROFILE)

# ─── AWS Deploy (backend → ECR → App Runner — host alternativo) ─────────────────
# Frontend pelo Amplify (amplify.yml). Não usado no deploy atual (Databricks Apps).

ecr-login:
	aws ecr get-login-password --region $(AWS_REGION) | \
	docker login --username AWS --password-stdin \
	$$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$(AWS_REGION).amazonaws.com

deploy-backend:
	@echo "Build + push da imagem do backend para o ECR ($(ECR_REPO):$(IMAGE_TAG))..."
	cd backend && docker build -t $(ECR_REPO):$(IMAGE_TAG) .
	$(eval ACCOUNT := $(shell aws sts get-caller-identity --query Account --output text))
	docker tag $(ECR_REPO):$(IMAGE_TAG) $(ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPO):$(IMAGE_TAG)
	docker push $(ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPO):$(IMAGE_TAG)
	@echo "Imagem publicada. Aponte o serviço do App Runner para essa imagem (ou faça deploy via console)."

# ─── Utilities ───────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

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
