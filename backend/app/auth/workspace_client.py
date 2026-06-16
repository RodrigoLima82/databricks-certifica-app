"""
WorkspaceClient singleton — OAuth M2M em Databricks Apps, ou token/CLI em dev.
"""
import logging
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_workspace_client():
    from databricks.sdk import WorkspaceClient

    s = get_settings()

    # Em Databricks Apps, DATABRICKS_HOST/CLIENT_ID/CLIENT_SECRET são injetados.
    if s.DATABRICKS_CLIENT_ID and s.DATABRICKS_CLIENT_SECRET:
        logger.info("WorkspaceClient via OAuth M2M (service principal)")
        return WorkspaceClient(
            host=s.databricks_host,
            client_id=s.DATABRICKS_CLIENT_ID,
            client_secret=s.DATABRICKS_CLIENT_SECRET,
        )
    if s.DATABRICKS_TOKEN:
        logger.info("WorkspaceClient via PAT")
        return WorkspaceClient(host=s.databricks_host, token=s.DATABRICKS_TOKEN)

    # Fallback: configuração padrão (CLI profile / env)
    logger.info("WorkspaceClient via default config (CLI/env)")
    return WorkspaceClient()
