import json
import re

from celery import shared_task

from reviews.models import Review
from services.ollama_service import generate_ai_review


VALID_CATEGORIES = {
    "security",
    "performance",
    "quality",
    "maintainability",
}

VALID_SEVERITIES = {
    "critical",
    "high",
    "medium",
    "low",
}

SECRET_PATTERN = re.compile(
    r"\b(secret|token|api[_-]?key|password|passwd|private[_-]?key)\b\s*[:=]\s*['\"][^'\"]{6,}['\"]",
    re.IGNORECASE,
)

COMMAND_EXEC_PATTERN = re.compile(
    r"\b(os\.system|subprocess\.(Popen|call|run)|exec\(|eval\(|child_process\.exec|Runtime\.getRuntime\(\)\.exec)\b"
)


def parse_diff_files(diff_content):
    files = []
    current_file = None

    for line in diff_content.splitlines():
        if line.startswith("diff --git "):
            if current_file:
                files.append(current_file)

            parts = line.split(" b/", 1)
            filename = parts[1] if len(parts) == 2 else "unknown"
            current_file = {
                "filename": filename,
                "added": [],
                "removed": [],
                "context": [],
            }
            continue

        if not current_file:
            continue

        if line.startswith("+++") or line.startswith("---"):
            continue

        if line.startswith("+"):
            current_file["added"].append(line[1:])
        elif line.startswith("-"):
            current_file["removed"].append(line[1:])
        elif line.startswith(" "):
            current_file["context"].append(line[1:])

    if current_file:
        files.append(current_file)

    if not files and diff_content.strip():
        files.append({
            "filename": "pasted-code",
            "added": diff_content.splitlines(),
            "removed": [],
            "context": [],
        })

    return files


def compact_snippet(lines):
    return "\n".join(line.rstrip() for line in lines).strip()


def normalize_code(value):
    return "\n".join(
        line.strip()
        for line in str(value or "").splitlines()
        if line.strip()
    )


def normalize_category(category):
    category = str(category or "").strip().lower()

    if category in VALID_CATEGORIES:
        return category

    if "security" in category:
        return "security"

    if "performance" in category:
        return "performance"

    if "maintain" in category:
        return "maintainability"

    if "quality" in category:
        return "quality"

    return ""


def normalize_severity(severity):
    severity = str(severity or "").strip().lower()

    for valid_severity in VALID_SEVERITIES:
        if valid_severity in severity:
            return valid_severity

    return ""


def find_matching_file(vulnerable_code, diff_files):
    normalized_vulnerable_code = normalize_code(vulnerable_code)

    if not normalized_vulnerable_code:
        return ""

    for file_diff in diff_files:
        added_code = normalize_code("\n".join(file_diff["added"]))

        if normalized_vulnerable_code in added_code:
            return file_diff["filename"]

    return ""


def file_exists_in_diff(filename, diff_files):
    if not filename:
        return False

    return any(file_diff["filename"] == filename for file_diff in diff_files)


def issue_points_to_changed_code(issue, diff_files):
    vulnerable_code = issue.get("vulnerable_code", "")
    filename = issue.get("file", "")

    if not vulnerable_code:
        return False

    matched_file = find_matching_file(vulnerable_code, diff_files)

    if not matched_file:
        return False

    if filename and filename != matched_file:
        return False

    issue["file"] = matched_file
    return True


def normalize_ai_issue(issue, diff_files):
    if not isinstance(issue, dict):
        return None

    if "fixedCode" in issue and "fixed_code" not in issue:
        issue["fixed_code"] = issue["fixedCode"]

    if isinstance(issue.get("suggestion"), dict):
        issue["suggestion"] = issue["suggestion"].get("text", "")

    normalized = {
        "file": str(issue.get("file") or issue.get("filename") or "").strip(),
        "severity": normalize_severity(issue.get("severity")),
        "category": normalize_category(issue.get("category")),
        "message": str(issue.get("message", "")).strip(),
        "suggestion": str(issue.get("suggestion", "")).strip(),
        "vulnerable_code": str(issue.get("vulnerable_code", "")).strip(),
        "fixed_code": str(issue.get("fixed_code", "")).strip(),
    }

    if not normalized["category"]:
        normalized["category"] = "quality"

    if not normalized["severity"]:
        normalized["severity"] = "medium"

    if not normalized["message"] or not normalized["suggestion"] or not normalized["fixed_code"]:
        return None

    if normalized["file"] and not file_exists_in_diff(normalized["file"], diff_files):
        normalized["file"] = ""

    if not issue_points_to_changed_code(normalized, diff_files):
        return None

    return normalized


def build_request_fix(added_lines):
    fixed_lines = []

    for line in added_lines:
        if re.search(r"\bverify\s*=\s*False\b", line):
            continue

        fixed_lines.append(line.replace("http://", "https://"))

    return compact_snippet(fixed_lines)


def static_review_diff(diff_files):
    issues = []

    for file_diff in diff_files:
        filename = file_diff["filename"]
        added = file_diff["added"]
        added_text = "\n".join(added)
        normalized_added = added_text.replace(" ", "")
        added_lower = added_text.lower()

        has_insecure_http = "http://" in added_lower
        disables_tls = bool(re.search(r"\bverify\s*=\s*False\b", added_text))

        if has_insecure_http or disables_tls:
            vulnerable_lines = [
                line for line in added
                if "http://" in line.lower() or re.search(r"\bverify\s*=\s*False\b", line)
            ]

            if has_insecure_http and disables_tls:
                message = "Insecure HTTP request with disabled TLS verification introduced."
                suggestion = "Use HTTPS and keep TLS certificate verification enabled."
                severity = "critical"
            elif has_insecure_http:
                message = "Insecure HTTP request introduced."
                suggestion = "Use HTTPS for external service calls."
                severity = "high"
            else:
                message = "TLS certificate verification is disabled."
                suggestion = "Keep TLS certificate verification enabled."
                severity = "critical"

            issues.append({
                "file": filename,
                "severity": severity,
                "category": "security",
                "message": message,
                "suggestion": suggestion,
                "vulnerable_code": compact_snippet(vulnerable_lines),
                "fixed_code": build_request_fix(added),
            })

        if re.search(r"\bwhile\s*\(?\s*true\s*\)?\s*:", added_text, re.IGNORECASE) or re.search(r"\bwhile\s*\(\s*true\s*\)", added_text, re.IGNORECASE):
            issues.append({
                "file": filename,
                "severity": "critical",
                "category": "performance",
                "message": "Infinite loop introduced.",
                "suggestion": "Add a break condition, sleep, timeout, or return meaningful data.",
                "vulnerable_code": compact_snippet(added),
                "fixed_code": "return []",
            })

        secret_match_lines = [line for line in added if SECRET_PATTERN.search(line)]

        if secret_match_lines:
            issues.append({
                "file": filename,
                "severity": "critical",
                "category": "security",
                "message": "Hardcoded secret introduced.",
                "suggestion": "Load secrets from environment variables or a secret manager.",
                "vulnerable_code": compact_snippet(secret_match_lines),
                "fixed_code": "import os\n\nSECRET_VALUE = os.environ[\"SECRET_VALUE\"]",
            })

        has_sql_keyword = any(keyword in added_lower for keyword in ["select", "insert", "update", "delete"])
        has_dynamic_sql = (
            "+" in added_text
            or "${" in added_text
            or "%s" in added_text
            or ".format(" in added_text
            or "cursor.execute(query)" in normalized_added
        )

        if has_sql_keyword and has_dynamic_sql:
            sql_lines = [
                line for line in added
                if any(token in line.lower() for token in ["select", "where", "execute", "+", "format", "user"])
            ] or added

            issues.append({
                "file": filename,
                "severity": "critical",
                "category": "security",
                "message": "SQL query appears to include dynamic string construction.",
                "suggestion": "Use parameterized queries instead of string concatenation or interpolation.",
                "vulnerable_code": compact_snippet(sql_lines),
                "fixed_code": "query = \"SELECT * FROM users WHERE id = ?\"\ncursor.execute(query, [user_id])",
            })

        if re.search(r"\bexcept\s*:", added_text):
            issues.append({
                "file": filename,
                "severity": "medium",
                "category": "maintainability",
                "message": "Bare exception handler introduced.",
                "suggestion": "Catch a specific exception and handle or log it explicitly.",
                "vulnerable_code": compact_snippet(added),
                "fixed_code": "try:\n    return data[\"value\"]\nexcept KeyError:\n    return None",
            })

        if COMMAND_EXEC_PATTERN.search(added_text):
            exec_lines = [line for line in added if COMMAND_EXEC_PATTERN.search(line)]
            issues.append({
                "file": filename,
                "severity": "critical",
                "category": "security",
                "message": "Potential command execution risk introduced.",
                "suggestion": "Avoid executing dynamic strings; use safe APIs and validated arguments.",
                "vulnerable_code": compact_snippet(exec_lines),
                "fixed_code": "Use a safe API with validated arguments instead of dynamic command execution.",
            })

        if "console.log(" in added_text or "print(" in added_text:
            suspicious_logs = [
                line for line in added
                if ("console.log(" in line or "print(" in line)
                and any(word in line.lower() for word in ["password", "token", "secret", "key"])
            ]

            if suspicious_logs:
                issues.append({
                    "file": filename,
                    "severity": "high",
                    "category": "security",
                    "message": "Sensitive data may be logged.",
                    "suggestion": "Do not log secrets, tokens, passwords, or API keys.",
                    "vulnerable_code": compact_snippet(suspicious_logs),
                    "fixed_code": "logger.info(\"Operation completed\")",
                })

        if "password" in added_lower and ("md5(" in added_lower or "sha1(" in added_lower or "sha256(" in added_lower):
            hash_lines = [
                line for line in added
                if any(token in line.lower() for token in ["password", "md5", "sha1", "sha256"])
            ]

            issues.append({
                "file": filename,
                "severity": "high",
                "category": "security",
                "message": "Password hashing uses a fast hash function.",
                "suggestion": "Use a password hashing algorithm such as bcrypt, Argon2, or PBKDF2.",
                "vulnerable_code": compact_snippet(hash_lines),
                "fixed_code": "Use bcrypt, Argon2, or PBKDF2 with a salt and work factor.",
            })

    return issues


def dedupe_issues(issues):
    deduped = []
    seen = set()

    for issue in issues:
        key = (
            issue.get("file"),
            issue.get("category"),
            issue.get("severity"),
            normalize_code(issue.get("vulnerable_code")),
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(issue)

    return deduped


@shared_task
def analyze_pull_request(review_id):
    review = Review.objects.get(id=review_id)

    try:
        diff_files = parse_diff_files(review.diff_content)
        issues = []
        result = generate_ai_review(review.diff_content)

        # print("\n===== CLEAN JSON =====")
        # print(result)
        # print("======================\n")

        try:
            parsed_result = json.loads(result)
            raw_issues = parsed_result.get("issues", [])

            if isinstance(raw_issues, list):
                for issue in raw_issues:
                    normalized_issue = normalize_ai_issue(issue, diff_files)

                    if normalized_issue:
                        issues.append(normalized_issue)

        except Exception:
            issues = []

        issues.extend(static_review_diff(diff_files))

        review.ai_response = {
            "issues": dedupe_issues(issues)
        }
        review.status = "completed"
        review.save()

    except Exception as e:
        review.status = "failed"
        review.ai_response = {
            "error": str(e)
        }
        review.save()




