"""
modules/fastScanner.py
Rule-based fast scanner: regex patterns + lightweight checks.
Every issue includes:
  - exact line number
  - actual line content (for context)
  - specific, actionable suggestion
  - issue type, severity, validation type
Runs on every text file before deciding if LLM deep scan is needed.
"""

import re
import os
import time
from typing import List, Dict, Any, Optional

from modules.config import Config
from modules.logger import getLogger

logger = getLogger()


def fastScanFile(filePath: str, fileContent: str) -> Dict[str, Any]:
    """
    Perform fast rule-based scan on a single file.

    Returns:
        issues      : list of fully-populated issue dicts
        scanTime    : seconds taken
        isEmpty     : bool
        isLarge     : bool
        lineCount   : int
        linesScanned: int (may differ from lineCount if file was truncated)
    """
    startTime  = time.time()
    issues: List[Dict[str, Any]] = []

    lines     = fileContent.splitlines()
    lineCount = len(lines)
    fileSize  = os.path.getsize(filePath) if os.path.exists(filePath) else 0
    maxBytes  = Config.MAX_FILE_SIZE_MB * 1024 * 1024

    isEmpty  = lineCount == 0 or fileContent.strip() == ""
    isLarge  = fileSize > maxBytes
    truncated = False

    # ── Empty file ──────────────────────────────────────────────────────────
    if isEmpty:
        issues.append(_makeIssue(
            issueType      = "Empty File",
            description    = "File contains no content (0 bytes or whitespace only).",
            lineNumber     = 0,
            lineContent    = "",
            severity       = "Low",
            suggestion     = (
                "Either remove this file from the repository, "
                "or add meaningful content / a placeholder comment."
            ),
            validationType = "Best Practice",
        ))

    # ── Large file ──────────────────────────────────────────────────────────
    if isLarge:
        truncated = True
        issues.append(_makeIssue(
            issueType      = "Large File",
            description    = (
                f"File size is {fileSize / 1024 / 1024:.2f} MB, exceeding the "
                f"{Config.MAX_FILE_SIZE_MB} MB limit. "
                "Only the first 5,000 lines were scanned."
            ),
            lineNumber     = 0,
            lineContent    = "",
            severity       = "Medium",
            suggestion     = (
                "Split this file into smaller modules, or add it to .gitignore "
                "if it is a generated / binary artefact. "
                "Consider using Git LFS for large assets."
            ),
            validationType = "Performance",
        ))
        lines = lines[:5000]   # scan only first 5000 lines

    linesScanned = len(lines)

    # ── Line-by-line pattern matching ──────────────────────────────────────
    for lineNum, rawLine in enumerate(lines, start=1):
        strippedLine = rawLine.strip()
        for pattern, baseDesc, severity, validationType in Config.DANGEROUS_PATTERNS:
            match = re.search(pattern, rawLine)
            if match:
                matchedText = match.group(0)[:80]   # cap at 80 chars
                issues.append(_makeIssue(
                    issueType      = _typeFromCategory(validationType),
                    description    = (
                        f"{baseDesc}. "
                        f"Matched: `{matchedText}` at line {lineNum}."
                    ),
                    lineNumber     = lineNum,
                    lineContent    = strippedLine[:120],   # show actual line
                    severity       = severity,
                    suggestion     = _specificSuggestion(baseDesc, rawLine, filePath),
                    validationType = validationType,
                ))

    # ── Language-specific checks ────────────────────────────────────────────
    ext = os.path.splitext(filePath)[1].lower()

    if ext == ".py":
        syntaxIssue = _checkPythonSyntax(fileContent, filePath)
        if syntaxIssue:
            issues.append(syntaxIssue)
        issues.extend(_checkPythonBestPractices(lines))

    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        issues.extend(_checkJsBestPractices(lines))

    elif ext in (".html", ".htm"):
        issues.extend(_checkHtmlIssues(lines))

    elif ext in (".env",):
        issues.extend(_checkEnvFileIssues(lines))

    # ── Deduplicate on (lineNumber, issueType) ─────────────────────────────
    seen: set = set()
    unique: List[Dict[str, Any]] = []
    for issue in issues:
        key = (issue["lineNumber"], issue["issueType"], issue["description"][:40])
        if key not in seen:
            seen.add(key)
            unique.append(issue)

    return {
        "issues"      : unique,
        "scanTime"    : round(time.time() - startTime, 4),
        "isEmpty"     : isEmpty,
        "isLarge"     : isLarge,
        "truncated"   : truncated,
        "lineCount"   : lineCount,
        "linesScanned": linesScanned,
    }


# ══════════════════════════════════════════════════════════════════════════
# Language-specific checkers
# ══════════════════════════════════════════════════════════════════════════

def _checkPythonSyntax(content: str, filePath: str) -> Optional[Dict[str, Any]]:
    """Compile Python source to detect syntax errors with exact line number."""
    try:
        compile(content, filePath, "exec")
        return None
    except SyntaxError as e:
        lines = content.splitlines()
        lineNum  = e.lineno or 0
        lineText = lines[lineNum - 1].strip() if lineNum and lineNum <= len(lines) else ""
        return _makeIssue(
            issueType      = "Syntax Error",
            description    = f"Python SyntaxError — {e.msg}.",
            lineNumber     = lineNum,
            lineContent    = lineText,
            severity       = "High",
            suggestion     = (
                f"Fix the syntax error on line {lineNum}. "
                "Run `python -m py_compile <file>` locally to verify."
            ),
            validationType = "Syntax",
        )
    except Exception:
        return None


def _checkPythonBestPractices(lines: List[str]) -> List[Dict[str, Any]]:
    """Detect Python-specific anti-patterns."""
    issues = []
    for lineNum, rawLine in enumerate(lines, start=1):
        stripped = rawLine.strip()
        # bare except
        if re.match(r'^except\s*:', stripped):
            issues.append(_makeIssue(
                issueType      = "Code Quality",
                description    = "Bare `except:` clause catches all exceptions including SystemExit.",
                lineNumber     = lineNum,
                lineContent    = stripped,
                severity       = "Medium",
                suggestion     = "Use `except Exception as e:` to catch specific exceptions only.",
                validationType = "Best Practice",
            ))
        # mutable default argument
        if re.search(r'def\s+\w+\s*\(.*=\s*(\[\]|\{\})', rawLine):
            issues.append(_makeIssue(
                issueType      = "Code Quality",
                description    = "Mutable default argument (list/dict) in function signature.",
                lineNumber     = lineNum,
                lineContent    = stripped,
                severity       = "Medium",
                suggestion     = "Use `None` as default and initialise inside the function body.",
                validationType = "Best Practice",
            ))
        # print statement used as debug
        if re.match(r'^\s*print\s*\(', rawLine) and "debug" in rawLine.lower():
            issues.append(_makeIssue(
                issueType      = "Code Quality",
                description    = "Debug print statement left in production code.",
                lineNumber     = lineNum,
                lineContent    = stripped,
                severity       = "Low",
                suggestion     = "Remove debug prints or replace with `logging.debug()`.",
                validationType = "Best Practice",
            ))
    return issues


def _checkJsBestPractices(lines: List[str]) -> List[Dict[str, Any]]:
    """Detect JS/TS-specific anti-patterns."""
    issues = []
    for lineNum, rawLine in enumerate(lines, start=1):
        stripped = rawLine.strip()
        if re.search(r'\bconsole\.log\b', rawLine):
            issues.append(_makeIssue(
                issueType      = "Code Quality",
                description    = "console.log() left in source — should not reach production.",
                lineNumber     = lineNum,
                lineContent    = stripped,
                severity       = "Low",
                suggestion     = "Remove console.log() or replace with a proper logger library.",
                validationType = "Best Practice",
            ))
        if re.search(r'\bvar\b', rawLine) and not re.search(r'//.*var', rawLine):
            issues.append(_makeIssue(
                issueType      = "Code Quality",
                description    = "`var` declaration used — function-scoped and error-prone.",
                lineNumber     = lineNum,
                lineContent    = stripped,
                severity       = "Low",
                suggestion     = "Replace `var` with `const` or `let` for block-scoped variables.",
                validationType = "Best Practice",
            ))
        if re.search(r'==(?!=)', rawLine) and not re.search(r'(!=|==\s*null)', rawLine):
            issues.append(_makeIssue(
                issueType      = "Code Quality",
                description    = "Loose equality `==` — may cause unexpected type coercion.",
                lineNumber     = lineNum,
                lineContent    = stripped,
                severity       = "Low",
                suggestion     = "Use strict equality `===` instead of `==`.",
                validationType = "Best Practice",
            ))
    return issues


def _checkHtmlIssues(lines: List[str]) -> List[Dict[str, Any]]:
    """Detect HTML security / accessibility issues."""
    issues = []
    for lineNum, rawLine in enumerate(lines, start=1):
        stripped = rawLine.strip()
        if re.search(r'javascript\s*:', stripped, re.IGNORECASE):
            issues.append(_makeIssue(
                issueType      = "Security Vulnerability",
                description    = "Inline `javascript:` URI found — XSS risk.",
                lineNumber     = lineNum,
                lineContent    = stripped,
                severity       = "High",
                suggestion     = "Remove inline javascript: URIs; attach event handlers via addEventListener().",
                validationType = "Security",
            ))
        if re.search(r'<input(?![^>]*type=["\']hidden)', stripped, re.IGNORECASE):
            if not re.search(r'autocomplete\s*=\s*["\']off["\']', stripped, re.IGNORECASE):
                if re.search(r'(password|passwd|secret)', stripped, re.IGNORECASE):
                    issues.append(_makeIssue(
                        issueType      = "Security Vulnerability",
                        description    = "Password input missing `autocomplete='off'`.",
                        lineNumber     = lineNum,
                        lineContent    = stripped,
                        severity       = "Medium",
                        suggestion     = 'Add autocomplete="off" to password input fields.',
                        validationType = "Security",
                    ))
    return issues


def _checkEnvFileIssues(lines: List[str]) -> List[Dict[str, Any]]:
    """Detect committed secrets in .env files."""
    issues = []
    for lineNum, rawLine in enumerate(lines, start=1):
        stripped = rawLine.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        value = value.strip().strip('"').strip("'")
        if len(value) > 8 and not value.startswith("${"):
            if re.search(r'(key|secret|token|password|passwd|api)', key, re.IGNORECASE):
                issues.append(_makeIssue(
                    issueType      = "Security Vulnerability",
                    description    = f"Real secret value found in .env for key `{key.strip()}`.",
                    lineNumber     = lineNum,
                    lineContent    = f"{key.strip()}=***REDACTED***",
                    severity       = "High",
                    suggestion     = (
                        "Never commit .env files containing real secrets. "
                        "Add .env to .gitignore and use a secrets manager or CI/CD env vars."
                    ),
                    validationType = "Security",
                ))
    return issues


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════

def _makeIssue(
    issueType: str,
    description: str,
    lineNumber: int,
    lineContent: str,
    severity: str,
    suggestion: str,
    validationType: str,
) -> Dict[str, Any]:
    """Central factory so every issue dict has identical keys."""
    return {
    "issueType": issueType,
    "description": description,
    "actualIssue": _generateActualIssue(description),  # 🔥 ADD THIS
    "lineNumber": lineNumber,
    "lineContent": lineContent,
    "severity": severity,
    "suggestion": suggestion,
    "validationType": validationType,
}

def _generateActualIssue(description: str) -> str:
    """
    Convert description into clear human-readable issue explanation.
    """
    d = description.lower()

    if "password" in d:
        return "Sensitive password is exposed directly in the code, which can lead to security breaches if the code is shared."
    
    if "api key" in d or "secret" in d:
        return "Confidential API keys or secrets are hardcoded, which can be exploited by attackers."
    
    if "eval" in d or "exec" in d:
        return "Dynamic code execution is used, which can allow attackers to run malicious code."
    
    if "sql" in d:
        return "User input is not safely handled in SQL query, which can lead to SQL Injection attacks."
    
    if "syntax error" in d:
        return "The code contains syntax errors that will break execution."
    
    if "large file" in d:
        return "File size is too large, which affects performance and scanning efficiency."
    
    if "empty file" in d:
        return "File has no content and does not contribute to the project."
    
    return "This issue affects code quality, security, or performance and should be reviewed."


def _typeFromCategory(category: str) -> str:
    return {
        "Security"    : "Security Vulnerability",
        "Performance" : "Performance Issue",
        "Best Practice": "Code Quality",
        "Syntax"      : "Syntax Error",
    }.get(category, "Issue")


def _specificSuggestion(baseDesc: str, rawLine: str, filePath: str) -> str:
    """
    Return a concrete, line-aware suggestion based on the matched description.
    """
    d = baseDesc.lower()
    ext = os.path.splitext(filePath)[1].lower()

    if "eval()" in d:
        return (
            "Replace eval() with ast.literal_eval() for data parsing, "
            "or refactor to avoid dynamic code execution entirely."
        )
    if "exec()" in d:
        return (
            "Remove exec(). Refactor the logic into explicit functions "
            "or use importlib for dynamic module loading."
        )
    if "hardcoded password" in d:
        return (
            "Move this password to an environment variable. "
            "Access it via os.getenv('PASSWORD') and store it in a secrets manager (e.g. AWS Secrets Manager, HashiCorp Vault)."
        )
    if "api key" in d or "apikey" in d or "secret_key" in d:
        return (
            "Remove the hardcoded key. Store it in .env (excluded from Git) "
            "and load with os.getenv(). Rotate the exposed key immediately."
        )
    if "private key" in d:
        return (
            "This private key must never be committed. "
            "Remove it, rotate/revoke it immediately, and store private keys in a secrets vault."
        )
    if "aws" in d:
        return (
            "Remove AWS credentials from code. "
            "Use IAM roles (EC2/Lambda), AWS Secrets Manager, or environment variables instead."
        )
    if "os.system" in d:
        return (
            "Replace os.system() with subprocess.run([...], shell=False, check=True) "
            "to avoid shell-injection vulnerabilities."
        )
    if "shell=true" in d:
        return (
            "Set shell=False and pass the command as a list: "
            "subprocess.run(['cmd', 'arg1'], shell=False). "
            "This prevents shell injection."
        )
    if "todo" in d or "fixme" in d:
        return (
            "Resolve this TODO/FIXME before merging. "
            "Create a tracked issue in your project tracker instead of leaving inline comments."
        )
    if "http://" in d:
        return (
            "Replace http:// with https:// to encrypt data in transit. "
            "Obtain a TLS certificate (e.g. via Let's Encrypt) if self-hosting."
        )
    if "pickle" in d:
        return (
            "Replace pickle with json.loads/json.dumps or the safer `marshal` module. "
            "Pickle can execute arbitrary code on deserialization."
        )
    if "select *" in d:
        return (
            "List only the columns you need: SELECT col1, col2 FROM table. "
            "SELECT * fetches unnecessary data and breaks if columns change."
        )
    if "sql injection" in d:
        return (
            "Use parameterised queries: cursor.execute('SELECT … WHERE id = %s', (user_id,)). "
            "Never build SQL strings by concatenation or f-strings."
        )
    if "console.log" in d:
        return (
            "Remove console.log() statements before production deployment. "
            "Use a structured logger (e.g. winston, pino) with log levels."
        )
    return (
        f"Review line {rawLine.strip()[:60]} and apply the relevant security/quality fix. "
        "Consult OWASP guidelines for security issues."
    )
