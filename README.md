# GAIA Agent — HF Agents Course (Unit 4)

Agente local que responde 20 preguntas del benchmark **GAIA (nivel 1)** vía la API
del [Hugging Face Agents Course](https://huggingface.co/learn/agents-course) para
obtener el **Certificate of Completion** de forma gratuita, sin depender de un
Hugging Face Space de pago.

## Cómo funciona

El scoring lo hace una **API HTTP** del curso, no un Space. El campo `agent_code`
del envío es solo un link de referencia para el leaderboard y **la API no lo valida**,
así que no se necesita un Space corriendo. Todo se desarrolla y ejecuta en local; la
única credencial obligatoria para enviar es el **username de Hugging Face**.

- **Base URL:** `https://agents-course-unit4-scoring.hf.space`
- `GET /questions` — lista completa de preguntas
- `GET /files/{task_id}` — adjunto de una pregunta (si existe)
- `POST /submit` — envía respuestas y calcula el score
- Scoring: **EXACT MATCH** → el agente responde solo la respuesta final, sin prefijos.

## Estructura

```
gaia-agent/
├── agent.py           # CodeAgent (smolagents) con búsqueda web + lectura de páginas
├── run.py             # Orquestador: descarga, corre, cachea y envía
├── requirements.txt
├── .env.example       # Plantilla de variables
├── .env               # Tu copia con credenciales (NO se commitea)
└── README.md
```

## Setup

```powershell
cd gaia-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# Edita .env: completa HF_USERNAME y GEMINI_API_KEY
```

La `GEMINI_API_KEY` se obtiene gratis en [Google AI Studio](https://aistudio.google.com/apikey).

## Uso

```powershell
# 1. Genera answers.json SIN enviar, para revisar las respuestas
python run.py --dry-run

# 2. Cuando se vean razonables, envía
python run.py

# (o reenvía el cache existente sin re-correr el agente ni gastar cuota)
python run.py --submit-only
```

## Meta y certificado

- **Objetivo:** score ≥ 30% (al menos 6/20 correctas).
- Con ese score: ve a
  [Unit4-Final-Certificate](https://huggingface.co/spaces/agents-course/Unit4-Final-Certificate),
  inicia sesión con tu cuenta HF, ingresa tu nombre completo y genera el PDF.

## Notas para iterar

- Las preguntas con archivos (Excel, imágenes, audio) son las más difíciles;
  prioriza las respondibles por búsqueda y razonamiento.
- Gran parte del resultado depende del **prompt de normalización** de la respuesta
  final (exact match), no solo de las tools.
- El cache `answers.json` permite reenviar sin re-correr el agente.
- Cambia de proveedor con `MODEL_PROVIDER` (gemini / groq / hf) si topas rate limits.
