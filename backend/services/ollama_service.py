import json
import re
import os

import requests


OLLAMA_URL = os.getenv("OLLAMA_URL")


def extract_json(text):
    start = text.find("{")

    if start == -1:
        return None

    brace_count = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        char = text[i]

        if escape:
            escape = False
            continue

        if char == "\\" and in_string:
            escape = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1

            if brace_count == 0:
                return text[start:i + 1]

    return None


def strip_json_comments(text):
    output = []
    i = 0
    in_string = False
    escape = False

    while i < len(text):
        char = text[i]
        next_char = text[i + 1] if i + 1 < len(text) else ""

        if escape:
            output.append(char)
            escape = False
            i += 1
            continue

        if char == "\\" and in_string:
            output.append(char)
            escape = True
            i += 1
            continue

        if char == '"':
            output.append(char)
            in_string = not in_string
            i += 1
            continue

        if not in_string and char == "#":
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue

        if not in_string and char == "/" and next_char == "/":
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue

        output.append(char)
        i += 1

    return "".join(output)


def clean_json_string(text):
    text = re.sub(r"```json|```", "", text)
    text = strip_json_comments(text)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text.strip()


def fallback_response(message, raw_response=""):
    return json.dumps({
        "issues": [],
        "error": message,
        "raw_response": raw_response
    })


def generate_ai_review(diff_content):
    prompt = f"""
You are an AI pull request reviewer.

Review ONLY the added lines in this git diff. Added lines start with +.
Use removed and context lines only to understand the change.
Support any programming language present in the diff.
Do not invent issues that are not visible in the added code.
If the added code has no meaningful issue, return {{"issues": []}}.

Return ONLY valid JSON with this exact shape:
{{
  "issues": [
    {{
      "file": "path/from/diff.ext",
      "severity": "critical | high | medium | low",
      "category": "security | performance | quality | maintainability",
      "message": "Clear one sentence issue description.",
      "suggestion": "Clear one sentence recommendation.",
      "vulnerable_code": "Exact added code from the diff that caused the issue.",
      "fixed_code": "Complete corrected replacement code."
    }}
  ]
}}

Rules:
- Return JSON only. No markdown.
- Use only double quotes for JSON strings.
- Every issue must include file, severity, category, message, suggestion, vulnerable_code, and fixed_code.
- vulnerable_code must be copied from added lines in the diff.
- fixed_code must be real corrected code, not an explanation.
- Review all languages generically: Python, JavaScript, TypeScript, Java, Go, PHP, Ruby, C#, SQL, shell, config files, and others.
- Look for security, performance, quality, and maintainability problems.

Git diff:
{diff_content}
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "deepseek-coder",
            "prompt": prompt,
            "stream": False,
            "temperature": 0,
            "format": "json"
        },
        timeout=(10, 120)
    )

    response.raise_for_status()
    data = response.json()
    raw_response = data.get("response", "")

    # print("\n===== RAW AI RESPONSE =====")
    # print(raw_response)
    # print("===========================\n")

    clean_json = extract_json(raw_response)

    if not clean_json:
        return fallback_response("AI returned unstructured response", raw_response)

    clean_json = clean_json_string(clean_json)

    try:
        json.loads(clean_json)
    except json.JSONDecodeError:
        return fallback_response("AI returned invalid JSON", raw_response)

    return clean_json
