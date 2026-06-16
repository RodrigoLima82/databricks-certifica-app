"""
Store em memória carregado de seed/seed_data.json.

Usado em MOCK_MODE (dev local) e como fonte para popular o Lakebase (seed).
Questões geradas via LLM em runtime também são guardadas aqui quando não há DB.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

SEED_PATH = Path(__file__).resolve().parent.parent.parent / "seed" / "seed_data.json"


class SeedStore:
    def __init__(self):
        self.certifications: List[dict] = []
        self.questions: List[dict] = []
        self.flashcards: List[dict] = []
        self._load()

    def _load(self):
        if not SEED_PATH.exists():
            logger.warning(f"Seed não encontrado em {SEED_PATH}")
            return
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        self.certifications = data.get("certifications", [])
        self.questions = data.get("questions", [])
        self.flashcards = data.get("flashcards", [])
        logger.info(
            f"Seed carregado: {len(self.certifications)} certs, "
            f"{len(self.questions)} questões, {len(self.flashcards)} flashcards"
        )

    # ── leitura ──────────────────────────────────────────────────────────────
    def list_certifications(self) -> List[dict]:
        return self.certifications

    def get_certification(self, cid: str) -> dict | None:
        return next((c for c in self.certifications if c["id"] == cid), None)

    def questions_for(self, cid: str) -> List[dict]:
        return [q for q in self.questions if q["certification_id"] == cid]

    def flashcards_for(self, cid: str) -> List[dict]:
        return [f for f in self.flashcards if f["certification_id"] == cid]

    # ── escrita (runtime, sem DB) ──────────────────────────────────────────────
    def add_questions(self, questions: List[dict]):
        self.questions.extend(questions)


_store: SeedStore | None = None


def get_store() -> SeedStore:
    global _store
    if _store is None:
        _store = SeedStore()
    return _store
