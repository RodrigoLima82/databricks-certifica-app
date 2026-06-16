"""
Gera simulações de demonstração para um usuário de teste (ML Associate).
Executa o código real do app (build_test + grade_test) contra o Lakebase
configurado no ambiente. Uso:

    python -m seed.sim_demo
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.services import users as users_svc, test_service  # noqa: E402
from app.auth.security import hash_password  # noqa: E402
from app.models.schemas import (  # noqa: E402
    TestSetupRequest, TestSubmitRequest, AnswerSubmission,
)

CERT = "machine_learning_associate"
EMAIL = "aluno.teste@gol.com"
NAME = "Aluno Teste"
PASSWORD = "aluno123"


def main():
    get_settings.cache_clear()
    if not users_svc.get_user(EMAIL):
        users_svc.create_user(EMAIL, NAME, hash_password(PASSWORD))
        print(f"usuario criado: {EMAIL} / senha: {PASSWORD}")
    else:
        print(f"usuario ja existe: {EMAIL}")

    rng = random.Random(7)
    plan = [(20, 0.55), (15, 0.80), (20, 0.90), (25, 0.60), (10, 1.00)]
    print("\n=== simulacoes ===")
    for i, (n, target) in enumerate(plan, 1):
        s = test_service.build_test(TestSetupRequest(certification_id=CERT, num_questions=n))
        qs = s.questions
        k = round(len(qs) * target)
        idxs = list(range(len(qs)))
        rng.shuffle(idxs)
        correct_set = set(idxs[:k])
        answers = []
        for j, q in enumerate(qs):
            if j in correct_set:
                sel = q.correct_answers
            else:
                sel = [(q.correct_answers[0] + 1) % len(q.options)]
            answers.append(AnswerSubmission(question_id=q.id, selected=sel))
        res = test_service.grade_test(
            TestSubmitRequest(session_id=s.id, certification_id=CERT,
                              answers=answers, duration_sec=rng.randint(90, 600)),
            user_email=EMAIL,
        )
        verdict = "APROVADO" if res.passed else "reprovado"
        print(f"  tentativa {i}: {res.correct}/{res.total} = {res.score_pct}% "
              f"| {verdict} | repetidas={res.repeated_questions}")
    print(f"\npronto - login como {EMAIL} / {PASSWORD}, ou veja no painel Admin")


if __name__ == "__main__":
    main()
