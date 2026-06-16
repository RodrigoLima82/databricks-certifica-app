"""
Testes de integração da API via TestClient (com autenticação JWT).
"""
from tests.conftest import ASSOC


# ── Abertos (sem auth) ────────────────────────────────────────────────────────
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["mode"] == "mock"


def test_auth_status(client):
    r = client.get("/api/auth/status")
    assert r.status_code == 200
    assert r.json()["pass_mark"] == 70


def test_list_certifications_open(client):
    r = client.get("/api/certifications/")
    assert r.status_code == 200 and len(r.json()) == 6


# ── Auth ──────────────────────────────────────────────────────────────────────
def test_register_login_me(client):
    email = "novo@gol.com"
    r = client.post("/api/auth/register", json={"name": "Novo", "email": email, "password": "senha123"})
    assert r.status_code == 200
    tok = r.json()["access_token"]
    assert r.json()["user"]["email"] == email
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200 and me.json()["email"] == email


def test_register_senha_curta_422(client):
    r = client.post("/api/auth/register", json={"name": "X", "email": "x@gol.com", "password": "123"})
    assert r.status_code == 422


def test_login_errado_401(client):
    client.post("/api/auth/register", json={"name": "Y", "email": "y@gol.com", "password": "senha123"})
    r = client.post("/api/auth/login", json={"email": "y@gol.com", "password": "errada"})
    assert r.status_code == 401


def test_email_duplicado_409(client):
    client.post("/api/auth/register", json={"name": "Z", "email": "z@gol.com", "password": "senha123"})
    r = client.post("/api/auth/register", json={"name": "Z2", "email": "z@gol.com", "password": "senha123"})
    assert r.status_code == 409


# ── Endpoints protegidos exigem auth ──────────────────────────────────────────
def test_questions_sem_auth_401(client):
    assert client.get(f"/api/certifications/{ASSOC}/questions").status_code == 401


def test_tests_sem_auth_401(client):
    assert client.post("/api/tests/", json={"certification_id": ASSOC, "num_questions": 5}).status_code == 401


def test_get_questions_autenticado(auth_client):
    r = auth_client.get(f"/api/certifications/{ASSOC}/questions")
    assert r.status_code == 200 and len(r.json()) > 0


def test_flashcards_autenticado(auth_client):
    r = auth_client.get(f"/api/certifications/{ASSOC}/flashcards")
    assert r.status_code == 200 and len(r.json()) > 0


def test_criar_e_corrigir_simulado(auth_client):
    r = auth_client.post("/api/tests/", json={"certification_id": ASSOC, "num_questions": 8})
    assert r.status_code == 200
    session = r.json()
    assert len(session["questions"]) == 8
    answers = [{"question_id": q["id"], "selected": q["correct_answers"]} for q in session["questions"]]
    r2 = auth_client.post("/api/tests/submit", json={
        "session_id": session["id"], "certification_id": ASSOC, "answers": answers, "duration_sec": 30})
    assert r2.status_code == 200
    res = r2.json()
    assert res["correct"] == 8 and res["score_pct"] == 100.0
    assert res["passed"] is True and res["pass_mark"] == 70


def test_simulado_reprovado(auth_client):
    r = auth_client.post("/api/tests/", json={"certification_id": ASSOC, "num_questions": 10})
    session = r.json()
    # responde tudo errado
    answers = [{"question_id": q["id"], "selected": [(q["correct_answers"][0] + 1) % len(q["options"])]}
               for q in session["questions"]]
    res = auth_client.post("/api/tests/submit", json={
        "session_id": session["id"], "certification_id": ASSOC, "answers": answers}).json()
    assert res["passed"] is False


def test_num_questions_fora_do_range_422(auth_client):
    assert auth_client.post("/api/tests/", json={"certification_id": ASSOC, "num_questions": 1}).status_code == 422
    assert auth_client.post("/api/tests/", json={"certification_id": ASSOC, "num_questions": 999}).status_code == 422


def test_generate_autenticado_mock(auth_client):
    r = auth_client.post("/api/generate/", json={"certification_id": ASSOC, "count": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] and len(body["questions"]) == 3


# ── Tracking ──────────────────────────────────────────────────────────────────
def test_my_attempts_autenticado(auth_client):
    r = auth_client.get("/api/me/attempts")
    assert r.status_code == 200
    assert r.json()["pass_mark"] == 70 and "attempts" in r.json()


def test_admin_overview_requer_admin(auth_client, admin_client):
    assert auth_client.get("/api/admin/overview").status_code == 403
    r = admin_client.get("/api/admin/overview")
    assert r.status_code == 200 and "users" in r.json()


# ── SPA ───────────────────────────────────────────────────────────────────────
def test_spa_serve_index(client):
    r = client.get("/cert/qualquer")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert client.get("/api/rota_inexistente").status_code == 404
