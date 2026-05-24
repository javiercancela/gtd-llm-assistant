CLASSIFY_ENGLISH_PROMPT = """
You are classifying inbox items for a GTD system.

Rules:
- type = "task" if it is a single actionable step
- type = "project" if it requires multiple steps toward one outcome
- type = "reference" if the content is a resource to keep and there is no action to take
- type = "waiting_for" if we are waiting on another person or entity for a response or delivery

Split the input into separate items when it contains multiple independent captures.
For each item, include a "text" field with only the portion of the input that item covers.

Return ONLY valid JSON (no markdown, no commentary).
The output may be either a single object or an array of objects.
Use this schema for each item:
{
  "type": "task" | "project" | "reference" | "waiting_for",
  "text": "the inbox text this item refers to"
}

Input:
{{INPUT_JSON}}
"""

TASK_ENGLISH_PROMPT = """
You are refining a classified inbox item into one or more Google Tasks–ready tasks for a GTD system.
The item has already been classified as type "task".

Rules:
- Extract a short, meaningful, action-oriented title (max 8 words); start with a verb when possible
- Put ALL remaining details in description ONLY when the title cannot hold them
- If the title already captures everything, description must be ""
- Split multiple independent single-step actions into separate task objects in an array
- Do not invent due dates, people, or URLs not present in the input

Return ONLY valid JSON (no markdown fences, no commentary).
The output may be either a single object or an array of objects.
Use this schema for each item:
{
  "type": "task",
  "title": "...",
  "description": "..."
}

Input:
{{INPUT_JSON}}
"""

PROJECT_ENGLISH_PROMPT = """
You are decomposing a GTD inbox item already classified as type "project".

Rules:
- Determine the project subject/outcome: what "done" looks like for this input.
- Compare against EXISTING_PROJECTS: set existing_project_title to an exact title from that list only when the new input clearly belongs to the same outcome; otherwise null for a new project.
- Decompose the input into distinct, concrete subtasks; each should be a single next physical action where possible.
- Do not duplicate generic placeholders like "Define next action" — list real subtasks derived from the input.
- subtasks must have at least one entry.

Return ONLY valid JSON.
The output may be either a single object or an array of objects.
Use this schema for each item:
{
  "type": "project",
  "title": "project subject (outcome-oriented, max 8 words)",
  "description": "optional context not covered by title or subtasks",
  "existing_project_title": "exact title from EXISTING_PROJECTS list if a match fits, else null",
  "subtasks": ["actionable subtask titles", "..."]
}

Input:
{{INPUT_JSON}}

Existing projects:
{{EXISTING_PROJECTS_JSON}}
"""

REFERENCE_ENGLISH_PROMPT = """
You are processing inbox items already classified as type "reference" for a GTD system.

This is non-actionable reference material: articles, links, notes, or resources to keep for later lookup—not tasks or projects.

For each reference item:
- title: short identifying title (max 8 words)—how you would find this later in a list
- summary: 1-3 sentences capturing the essence; do not copy the entire input verbatim unless the input is already short
- url: extract a URL from the input if present; otherwise use an empty string ""; never fabricate URLs

If the input contains multiple distinct references, return a JSON array with one object per reference.
If there is a single reference, return either a single object or an array with one object.

Return ONLY valid JSON (object or array). No markdown, no commentary.

Schema for each item:
{
  "type": "reference",
  "title": "short identifying title (max 8 words)",
  "summary": "1-3 sentence summary of the content",
  "url": "URL string or empty string if none in input"
}

Input:
{{INPUT_JSON}}
"""

WAITING_FOR_ENGLISH_PROMPT = """
You are structuring a GTD inbox item already classified as waiting_for.

Rules:
- what: the deliverable, outcome, or response we are waiting for (the thing expected)
- who: the person or entity we are waiting on (accountable for delivering what)
- title: short task-list title (max 8 words); start with "Waiting for" when natural; summarize what
- description: who and any context or deadline not already in the title; format clearly

Separate what (the expected thing) from who (the accountable party).
title is for the task list; if who is not obvious from the title, description must include who.
If who is unknown or unclear, set who to "Unknown" and note the uncertainty in description.
Multiple distinct waiting-for items in the input → return a JSON array with one object per item.
Do not invent names, deadlines, or commitments not present in the input.

Return ONLY valid JSON (no markdown, no commentary).
The output may be either a single object or an array of objects.
Use this schema for each item:
{
  "type": "waiting_for",
  "what": "...",
  "who": "...",
  "title": "...",
  "description": "..."
}

Input:
{{INPUT_JSON}}
"""

CLASSIFY_SPANISH_PROMPT = """
Eres un asistente de GTD que clasifica los items del inbox personal.

Reglas:
- tipo = "compra" si es añadir algo para comprar (lista de la compra)
- tipo = "tarea" para cualquier otra acción tangible (incluye varios pasos, esperas a otras
  personas, o información que en otro idioma sería referencia o proyecto)
- Nunca uses otros tipos: no "proyecto", no "referencia", no "esperando"

También:
- Genera un título corto (máximo 8 palabras)
- Genera una descripción concisa (máximo 2 sentencias) solo si es necesario añadir información al título

Return ONLY valid JSON with this schema:
[
  {
    "tipo": "...",
    "titulo": "...",
    "descripcion": "..."
  }
]
Ejemplo de entrada 1:
{
  "text": "Comprar leche y pan  "
}
Ejemplo de salida 1:
[
  {
    "tipo": "compra",
    "titulo": "Leche",
    "descripcion": ""
  },
  {
    "tipo": "compra",
    "titulo": "Pan",
    "descripcion": ""
  }
]
Ejemplo de entrada 2:
{
  "text": "Asegurarse de que la alarma de la casa de Gandarío esté bien configurada y que las cámaras esté grabando todo el exterior. El vídeo debe estar almacenado en local y en la nube, y debe ser accesible desde cualquier dispositivo."
}
Ejemplo de salida 2:
[
  {
    "tipo": "tarea",
    "titulo": "Asegurar alarma y cámaras",
    "descripcion": "El vídeo debe estar almacenado en local y en la nube, y debe ser accesible desde cualquier dispositivo."
  }
]
Input:
{{INPUT_JSON}}
"""
