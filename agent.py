"""
GAIA Agent — HF Agents Course, Unit 4.

Define un CodeAgent de smolagents equipado con búsqueda web y lectura de páginas,
más las base tools. El modelo se selecciona por la variable MODEL_PROVIDER.

La clase expone __call__(question, file_path=None) -> str, que corre el agente y
devuelve la respuesta final normalizada para EXACT MATCH (última línea no vacía,
sin prefijos tipo "FINAL ANSWER:").
"""

import os

from smolagents import (
    CodeAgent,
    DuckDuckGoSearchTool,
    VisitWebpageTool,
    LiteLLMModel,
    InferenceClientModel,
)

# Prompt de sistema orientado a exact match. Se antepone a cada pregunta.
SYSTEM_PROMPT = """You are a general AI assistant solving GAIA benchmark questions.
Reason step by step using the tools available (web search, visit webpage, and Python code).
The final line of your answer MUST contain ONLY the final answer, with NO label,
NO "FINAL ANSWER" prefix, and NO trailing punctuation.

Answer formatting rules (scoring is EXACT MATCH against ground truth):
- If the answer is a number, write only the digits: no thousands separators, no units
  (no $, %, etc.) unless the question explicitly asks for the unit.
- If the answer is a string, make it as short as possible: no leading articles,
  no abbreviations unless the question asks for them, spell out digits as words only
  if the question asks for it.
- If the answer is a comma-separated list, apply the number and string rules to each
  element, separated by ", ".
- Do not add explanations on the final line. Put your reasoning on earlier lines only.
"""


def _build_model():
    provider = os.getenv("MODEL_PROVIDER", "gemini").lower()
    forced_id = os.getenv("MODEL_ID")

    # num_retries: litellm reintenta con backoff ante 429/503 transitorios
    # (los modelos preview de Gemini devuelven 503 esporádicos bajo carga).
    retries = int(os.getenv("MODEL_NUM_RETRIES", "4"))

    if provider == "gemini":
        model_id = forced_id or "gemini/gemini-2.0-flash"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY no está definida en el entorno/.env")
        return LiteLLMModel(model_id=model_id, api_key=api_key, num_retries=retries)

    if provider == "groq":
        model_id = forced_id or "groq/llama-3.3-70b-versatile"
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY no está definida en el entorno/.env")
        return LiteLLMModel(model_id=model_id, api_key=api_key, num_retries=retries)

    if provider == "hf":
        model_id = forced_id or "Qwen/Qwen2.5-Coder-32B-Instruct"
        token = os.getenv("HF_TOKEN")
        if not token:
            raise RuntimeError("HF_TOKEN no está definido en el entorno/.env")
        return InferenceClientModel(model_id=model_id, token=token)

    raise ValueError(f"MODEL_PROVIDER desconocido: {provider!r} (usa gemini|groq|hf)")


def _clean_answer(text: str) -> str:
    """Extrae la última línea no vacía y limpia prefijos tipo FINAL ANSWER."""
    if text is None:
        return ""
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    if not lines:
        return str(text).strip()
    answer = lines[-1]

    # Limpia prefijos comunes.
    for prefix in ("FINAL ANSWER:", "FINAL ANSWER", "Answer:", "ANSWER:"):
        if answer.upper().startswith(prefix.upper()):
            answer = answer[len(prefix):].strip()
            break

    # Quita comillas envolventes y un único punto final.
    # (un decimal como "3.14" termina en dígito, no en ".", así que es seguro.)
    answer = answer.strip().strip('"').strip("'").strip()
    if answer.endswith("."):
        answer = answer[:-1].strip()
    return answer


class GAIAAgent:
    def __init__(self, verbose: bool = True):
        self.model = _build_model()
        self.agent = CodeAgent(
            tools=[DuckDuckGoSearchTool(), VisitWebpageTool()],
            model=self.model,
            add_base_tools=True,
            max_steps=8,
            planning_interval=3,
            verbosity_level=2 if verbose else 0,
        )

    def __call__(self, question: str, file_path: str | None = None) -> str:
        prompt = SYSTEM_PROMPT + "\n\nQuestion:\n" + question
        if file_path:
            prompt += (
                f"\n\nAn attached file is available at the local path: {file_path}\n"
                "Read it with Python (pandas / openpyxl / PIL / plain open) as needed "
                "to answer the question."
            )
        raw = self.agent.run(prompt)
        return _clean_answer(raw)
