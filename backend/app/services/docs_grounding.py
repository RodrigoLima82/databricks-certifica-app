"""
Grounding em documentação oficial (AI Prep Guide, Step 2/4.3).

A guia exige ancorar tudo em docs.databricks.com e citar a URL da página. Para
evitar que o modelo *invente* ou "chute a seção mais próxima", damos a ele uma
allowlist real de páginas oficiais: o `llms.txt` que a Databricks publica para
consumo por LLMs (índice curado título + descrição + URL por seção).

Snapshot versionado em `databricks_llms.txt` (determinístico, sem rede em
runtime). Selecionamos as N páginas mais relevantes a um objetivo por overlap
de tokens (sem dependências externas) e as injetamos no prompt do deep-dive,
instruindo o modelo a citar SOMENTE dessa lista.

Atualizar o snapshot: `curl -s https://docs.databricks.com/llms.txt -o app/services/databricks_llms.txt`
"""
import logging
import re
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

_LLMS_TXT = Path(__file__).resolve().parent / "databricks_llms.txt"

# Linha do llms.txt: "- [Título](https://url) - descrição"
_LINE = re.compile(r"-\s*\[(?P<title>[^\]]+)\]\((?P<url>https?://[^)]+)\)\s*-?\s*(?P<desc>.*)")

# Stopwords PT/ES/EN — removidas do matching para focar em termos de produto.
_STOP = {
    "the", "and", "for", "with", "que", "los", "las", "del", "para", "com",
    "una", "uno", "por", "how", "you", "your", "use", "using", "learn", "get",
    "what", "que", "como", "sobre", "este", "esta", "aprende", "aprenda",
    "de", "da", "do", "em", "en", "an", "of", "to", "in", "on", "a", "o", "e",
}


def _tokens(text: str) -> set:
    return {
        w for w in re.split(r"[^a-z0-9]+", text.lower())
        if len(w) > 2 and w not in _STOP
    }


class _DocIndex:
    """Índice em memória do llms.txt (carregado uma vez)."""

    def __init__(self) -> None:
        self.entries: List[Tuple[str, str, set]] = []  # (title+desc, url, tokens)
        try:
            raw = _LLMS_TXT.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("databricks_llms.txt ausente — grounding desativado")
            return
        for line in raw.splitlines():
            m = _LINE.match(line.strip())
            if not m:
                continue
            title, url, desc = m["title"], m["url"], m["desc"]
            self.entries.append((f"{title} — {desc}", url, _tokens(f"{title} {desc}")))
        logger.info(f"docs_grounding: {len(self.entries)} páginas oficiais indexadas")

    def top(self, query: str, k: int = 8) -> List[Tuple[str, str]]:
        """Retorna [(label, url)] das k páginas mais relevantes ao query."""
        if not self.entries:
            return []
        qt = _tokens(query)
        if not qt:
            return []
        scored = []
        for label, url, toks in self.entries:
            overlap = len(qt & toks)
            if overlap:
                # normaliza levemente por tamanho do doc p/ não favorecer descrições longas
                scored.append((overlap, -len(toks), label, url))
        scored.sort(reverse=True)
        return [(label, url) for _, _, label, url in scored[:k]]


_INDEX: _DocIndex | None = None


def _index() -> _DocIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = _DocIndex()
    return _INDEX


def official_sources(query: str, k: int = 8) -> List[Tuple[str, str]]:
    """Páginas oficiais (label, url) mais relevantes ao objetivo/consulta."""
    return _index().top(query, k)


def sources_block(query: str, k: int = 8) -> str:
    """Bloco de texto para injetar no prompt: allowlist de URLs oficiais.
    Vazio se não houver índice (o chamador deve degradar graciosamente)."""
    hits = official_sources(query, k)
    if not hits:
        return ""
    lines = "\n".join(f"   - {label}\n     {url}" for label, url in hits)
    return (
        "OFFICIAL DOCUMENTATION ALLOWLIST (docs.databricks.com). "
        "Cite doc_url ONLY from this list — pick the single most relevant page. "
        "If none fits, set doc_url to \"https://docs.databricks.com/\" and say so:\n"
        + lines
    )
