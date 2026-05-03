PROMPT_TEMPLATE = """
You are classifying inbox items for a GTD system.

Rules:
- type = "task" if it is a single actionable step
- type = "project" if it requires multiple steps
- type = "reference" if the content is a reference to a resource and there is no action to be taken

Also:
- Generate a short title (max 8 words)
- Generate a concise description (max 2 sentences)
- Add 0–3 tags

Return ONLY valid JSON with this schema:
{
  "type": "...",
  "title": "...",
  "description": "...",
  "tags": ["..."]
}

Input:
{{INPUT_JSON}}
"""
