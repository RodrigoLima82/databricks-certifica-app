"""
Informação oficial de cada certificação (da Guia de Certificação Databricks).
Dados globais (não por tenant): formato do exame + temário com ponderações.

Multilíngue: campos traduzíveis são dicts {"pt","en","es"} resolvidos em runtime
por get_cert_info(id, lang). Dados neutros (nº de questões, duração, pesos, URL da
guia, códigos de idioma) ficam como strings simples.
"""
from typing import Optional


def L(pt: str, en: str, es: str) -> dict:
    """Atalho para um campo traduzível (pt/en/es)."""
    return {"pt": pt, "en": en, "es": es}


_GUIDE = {
    "data_engineer_associate": "https://www.databricks.com/sites/default/files/2026-05/databricks-certified-data-engineer-associate-exam-guide-may-2026-000.pdf",
    "machine_learning_associate": "https://www.databricks.com/sites/default/files/2025-02/databricks-certified-machine-learning-associate-exam-guide-1-mar-2025.pdf",
    "data_analyst_associate": "https://www.databricks.com/sites/default/files/2025-10/databricks-certified-data-analyst-associate-oct-2025.pdf",
}

# Snippets de formato/experiência reutilizados.
_MC = L("Múltipla escolha · proctored", "Multiple choice · proctored", "Opción múltiple · proctored")
_VALIDITY = L("2 anos", "2 years", "2 años")
_LANG_MULTI = "EN · JP · PT-BR · KR"           # códigos — neutro
_LANG_EN_ONLY = L("EN (apenas inglês)", "EN (English only)", "EN (solo inglés)")

CERT_INFO = {
    "data_engineer_associate": {
        "questions": "45", "duration": "90 min",
        "format": L("Múltipla escolha · proctored (online ou centro)",
                    "Multiple choice · proctored (online or center)",
                    "Opción múltiple · proctored (online o centro)"),
        "language": _LANG_MULTI, "validity": _VALIDITY,
        "experience": L("Prática com as tarefas do exam guide",
                        "Hands-on with the exam guide tasks",
                        "Hands-on con las tareas del exam guide"),
        "exam_guide_url": _GUIDE["data_engineer_associate"],
        "domains": [
            {"name": L("Data Intelligence Platform e workspace",
                       "Data Intelligence Platform and workspace",
                       "Data Intelligence Platform y workspace"), "weight": None},
            {"name": L("Ingestão e carga (Lakeflow Connect, Auto Loader, COPY INTO)",
                       "Ingestion and loading (Lakeflow Connect, Auto Loader, COPY INTO)",
                       "Ingesta y carga (Lakeflow Connect, Auto Loader, COPY INTO)"), "weight": None},
            {"name": L("Transformação e modelagem (PySpark, SQL)",
                       "Transformation and modeling (PySpark, SQL)",
                       "Transformación y modelado (PySpark, SQL)"), "weight": None},
            {"name": "Lakeflow Declarative Pipelines + Lakeflow Jobs (CI/CD)", "weight": None},
            {"name": "Delta Lake (ACID, time travel, MERGE, OPTIMIZE/VACUUM)", "weight": None},
            {"name": L("Unity Catalog (governança, permissões, linhagem)",
                       "Unity Catalog (governance, permissions, lineage)",
                       "Unity Catalog (gobierno, permisos, linaje)"), "weight": None},
            {"name": L("Troubleshooting, monitoramento e otimização",
                       "Troubleshooting, monitoring and optimization",
                       "Troubleshooting, monitoreo y optimización"), "weight": None},
        ],
    },
    "machine_learning_associate": {
        "questions": "48", "duration": "90 min", "format": _MC,
        "language": _LANG_MULTI, "validity": _VALIDITY,
        "experience": L("6+ meses de ML no Databricks",
                        "6+ months of ML on Databricks",
                        "6+ meses de ML en Databricks"),
        "exam_guide_url": _GUIDE["machine_learning_associate"],
        "domains": [
            {"name": "Databricks Machine Learning", "weight": 38},
            {"name": L("Desenvolvimento de modelos", "Model Development", "Desarrollo de modelos"), "weight": 31},
            {"name": L("Fluxos de trabalho de ML", "ML Workflows", "Flujos de trabajo de ML"), "weight": 19},
            {"name": L("Implantação de modelos", "Model Deployment", "Despliegue de modelos"), "weight": 12},
        ],
    },
    "data_analyst_associate": {
        "questions": "45", "duration": "90 min", "format": _MC,
        "language": _LANG_EN_ONLY, "validity": _VALIDITY,
        "experience": L("6+ meses de análise de dados",
                        "6+ months of data analysis",
                        "6+ meses de análisis de datos"),
        "exam_guide_url": _GUIDE["data_analyst_associate"],
        "domains": [
            {"name": L("Execução de consultas com Databricks SQL e Warehouses",
                       "Running queries with Databricks SQL and Warehouses",
                       "Ejecución de consultas con Databricks SQL y Warehouses"), "weight": 20},
            {"name": L("Criação de dashboards e visualizações",
                       "Creating dashboards and visualizations",
                       "Creación de dashboards y visualizaciones"), "weight": 16},
            {"name": L("Análise de consultas", "Query analysis", "Análisis de consultas"), "weight": 15},
            {"name": L("Desenvolvimento e manutenção de AI/BI Genie spaces",
                       "Developing and maintaining AI/BI Genie spaces",
                       "Desarrollo y mantenimiento de AI/BI Genie spaces"), "weight": 12},
            {"name": L("Entender a Data Intelligence Platform",
                       "Understanding the Data Intelligence Platform",
                       "Entender el Data Intelligence Platform"), "weight": 11},
            {"name": L("Gestão de dados", "Data management", "Gestión de datos"), "weight": 8},
            {"name": L("Segurança de dados", "Data security", "Seguridad de datos"), "weight": 8},
            {"name": L("Importação de dados", "Data import", "Importación de datos"), "weight": 5},
            {"name": L("Modelagem de dados com Databricks SQL",
                       "Data modeling with Databricks SQL",
                       "Modelado de datos con Databricks SQL"), "weight": 5},
        ],
    },
    "generative_ai_engineer_associate": {
        "questions": "45", "duration": "90 min", "format": _MC,
        "language": _LANG_MULTI, "validity": _VALIDITY,
        "experience": L("6+ meses de GenAI/LLM no Databricks",
                        "6+ months of GenAI/LLM on Databricks",
                        "6+ meses de GenAI/LLM en Databricks"),
        "exam_guide_url": "https://www.databricks.com/sites/default/files/2026-03/Databricks-Certified-Generative-AI-Engineer-Associate-Exam-Guide-Mar26.pdf",
        "domains": [
            {"name": L("Desenvolvimento de aplicações", "Application Development", "Desarrollo de aplicaciones"), "weight": 30},
            {"name": L("Montagem e implantação de apps", "Assembling and Deploying Apps", "Ensamblaje y despliegue de apps"), "weight": 22},
            {"name": L("Design de aplicações", "Design Applications", "Diseño de aplicaciones"), "weight": 14},
            {"name": L("Preparação de dados", "Data Preparation", "Preparación de datos"), "weight": 14},
            {"name": L("Avaliação e monitoramento", "Evaluation and Monitoring", "Evaluación y monitoreo"), "weight": 12},
            {"name": L("Governança", "Governance", "Gobierno"), "weight": 8},
        ],
    },
    "machine_learning_professional": {
        "questions": "60", "duration": "120 min", "format": _MC,
        "language": _LANG_EN_ONLY, "validity": _VALIDITY,
        "experience": L("1+ ano de ML em produção no Databricks",
                        "1+ year of ML in production on Databricks",
                        "1+ año de ML en producción en Databricks"),
        "exam_guide_url": "https://www.databricks.com/learn/certification/machine-learning-professional",
        "domains": [
            {"name": L("Experimentação", "Experimentation", "Experimentación"), "weight": 30},
            {"name": L("Gestão do ciclo de vida do modelo", "Model Lifecycle Management", "Gestión del ciclo de vida del modelo"), "weight": 30},
            {"name": L("Implantação de modelos", "Model Deployment", "Despliegue de modelos"), "weight": 25},
            {"name": L("Monitoramento de solução e dados", "Solution and Data Monitoring", "Monitoreo de solución y datos"), "weight": 15},
        ],
    },
    "data_engineer_professional": {
        "questions": "60", "duration": "120 min", "format": _MC,
        "language": _LANG_EN_ONLY, "validity": _VALIDITY,
        "experience": L("1+ ano de data engineering no Databricks",
                        "1+ year of data engineering on Databricks",
                        "1+ año de data engineering en Databricks"),
        "exam_guide_url": "https://www.databricks.com/learn/certification/data-engineer-professional",
        "domains": [
            {"name": L("Ferramentas Databricks", "Databricks Tooling", "Herramientas Databricks"), "weight": 20},
            {"name": L("Processamento de dados", "Data Processing", "Procesamiento de datos"), "weight": 30},
            {"name": L("Modelagem de dados", "Data Modeling", "Modelado de datos"), "weight": 20},
            {"name": L("Segurança e governança", "Security and Governance", "Seguridad y gobierno"), "weight": 10},
            {"name": L("Monitoramento e logging", "Monitoring and Logging", "Monitoreo y registro"), "weight": 10},
            {"name": L("Testes e implantação", "Testing and Deployment", "Pruebas y despliegue"), "weight": 10},
        ],
    },
}

_SUPPORTED = ("pt", "en", "es")


def resolve_lang(accept_language: Optional[str]) -> str:
    """Extrai o idioma suportado (pt/en/es) do header Accept-Language; default pt."""
    if not accept_language:
        return "pt"
    code = accept_language.split(",")[0].strip().lower()[:2]
    return code if code in _SUPPORTED else "pt"


def _pick(value, lang: str):
    """Resolve um campo: dict traduzível → string no idioma (fallback pt); senão devolve como está."""
    if isinstance(value, dict) and any(k in value for k in _SUPPORTED):
        return value.get(lang) or value.get("pt") or next(iter(value.values()))
    return value


def get_cert_info(certification_id: str, lang: str = "pt") -> Optional[dict]:
    info = CERT_INFO.get(certification_id)
    if not info:
        return None
    lang = lang if lang in _SUPPORTED else "pt"
    out = {k: _pick(v, lang) for k, v in info.items() if k != "domains"}
    out["domains"] = [{"name": _pick(d["name"], lang), "weight": d.get("weight")}
                      for d in info.get("domains", [])]
    return out
