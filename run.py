"""
Orquestador del agente GAIA — HF Agents Course, Unit 4.

Flujo:
  1. Descarga las preguntas de GET /questions.
  2. Para cada pregunta con file_name, descarga el adjunto a downloaded_files/.
  3. Corre el agente por pregunta (con manejo de excepción individual).
  4. Cachea el payload en answers.json.
  5. Envía a POST /submit con username, agent_code y answers.

Flags:
  --dry-run       Corre el agente pero NO envía. Solo genera answers.json.
  --submit-only   No corre el agente. Reenvía answers.json existente.
"""

import argparse
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

BASE_URL = "https://agents-course-unit4-scoring.hf.space"
QUESTIONS_URL = f"{BASE_URL}/questions"
FILES_URL = f"{BASE_URL}/files"
SUBMIT_URL = f"{BASE_URL}/submit"

ANSWERS_CACHE = "answers.json"
DOWNLOADS_DIR = "downloaded_files"


def fetch_questions() -> list[dict]:
    print(f"Descargando preguntas de {QUESTIONS_URL} ...")
    resp = requests.get(QUESTIONS_URL, timeout=60)
    resp.raise_for_status()
    questions = resp.json()
    print(f"  {len(questions)} preguntas recibidas.")
    return questions


def download_file(task_id: str, file_name: str) -> str | None:
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    local_path = os.path.join(DOWNLOADS_DIR, file_name)
    if os.path.exists(local_path):
        return local_path
    url = f"{FILES_URL}/{task_id}"
    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(resp.content)
        print(f"  Adjunto descargado: {file_name} ({len(resp.content)} bytes)")
        return local_path
    except Exception as exc:  # noqa: BLE001
        print(f"  [WARN] No se pudo descargar el adjunto de {task_id}: {exc}")
        return None


def run_agent_over_questions(questions: list[dict], sleep_between: float) -> list[dict]:
    # Import diferido: solo se necesita cuando realmente corremos el agente.
    from agent import GAIAAgent

    agent = GAIAAgent()
    answers = []
    total = len(questions)

    for i, item in enumerate(questions, start=1):
        task_id = item.get("task_id")
        question = item.get("question", "")
        file_name = item.get("file_name") or ""

        print(f"\n[{i}/{total}] task_id={task_id}")
        print(f"  Q: {question[:160]}{'...' if len(question) > 160 else ''}")

        file_path = None
        if file_name:
            file_path = download_file(task_id, file_name)

        try:
            answer = agent(question, file_path=file_path)
        except Exception as exc:  # noqa: BLE001
            print(f"  [ERROR] Falló la pregunta {task_id}: {exc}")
            answer = ""

        print(f"  A: {answer!r}")
        answers.append({"task_id": task_id, "submitted_answer": answer})

        if sleep_between and i < total:
            time.sleep(sleep_between)

    return answers


def save_cache(answers: list[dict]) -> None:
    with open(ANSWERS_CACHE, "w", encoding="utf-8") as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)
    print(f"\nCache guardado en {ANSWERS_CACHE} ({len(answers)} respuestas).")


def load_cache() -> list[dict]:
    if not os.path.exists(ANSWERS_CACHE):
        sys.exit(f"No existe {ANSWERS_CACHE}. Corre primero con --dry-run.")
    with open(ANSWERS_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)


def submit(answers: list[dict]) -> None:
    username = os.getenv("HF_USERNAME")
    agent_code = os.getenv("AGENT_CODE_URL", "")
    if not username:
        sys.exit("HF_USERNAME no está definido en el entorno/.env")

    payload = {
        "username": username.strip(),
        "agent_code": agent_code.strip(),
        "answers": answers,
    }
    print(f"\nEnviando {len(answers)} respuestas como '{username}' a {SUBMIT_URL} ...")
    resp = requests.post(SUBMIT_URL, json=payload, timeout=120)

    if resp.status_code != 200:
        print(f"[ERROR] HTTP {resp.status_code}: {resp.text}")
        resp.raise_for_status()

    data = resp.json()
    print("\n===== RESULTADO =====")
    print(f"  Usuario:        {data.get('username')}")
    print(f"  Score:          {data.get('score')}%")
    print(f"  Correctas:      {data.get('correct_count')} / {data.get('total_attempted')}")
    print(f"  Mensaje:        {data.get('message', '')}")
    print("=====================")
    score = data.get("score", 0) or 0
    if float(score) >= 30:
        print("\n✅ ¡Meta alcanzada (>=30%)! Ya puedes generar el certificado.")
    else:
        print("\n⚠️  Aún por debajo de 30%. Itera prompt/tools y reenvía.")


def main():
    parser = argparse.ArgumentParser(description="Runner del agente GAIA (Unit 4).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Corre el agente pero no envía; solo genera answers.json.")
    parser.add_argument("--submit-only", action="store_true",
                        help="No corre el agente; reenvía answers.json existente.")
    args = parser.parse_args()

    load_dotenv()
    sleep_between = float(os.getenv("SLEEP_BETWEEN", "2"))

    if args.submit_only:
        answers = load_cache()
        submit(answers)
        return

    questions = fetch_questions()
    answers = run_agent_over_questions(questions, sleep_between)
    save_cache(answers)

    if args.dry_run:
        print("\n--dry-run activo: NO se envía. Revisa answers.json y luego "
              "corre `python run.py --submit-only`.")
        return

    submit(answers)


if __name__ == "__main__":
    main()
