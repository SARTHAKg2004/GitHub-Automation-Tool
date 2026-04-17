"""
modules/deepScanner.py
LLM-based deep scanner using Anthropic Claude API.
Only called for files flagged as suspicious by the fast scanner.
"""

import json
import time
import re
from typing import List, Dict, Any

from modules.config import Config
from modules.logger import getLogger

logger = getLogger()

# Lazy import so the tool works even without anthropic installed during setup
_anthropicClient = None


def _getClient():
    global _anthropicClient
    if _anthropicClient is None:
        try:
            import anthropic
            _anthropicClient = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialise Anthropic client: {e}")
            _anthropicClient = None
    return _anthropicClient

def cleanText(text):
    if not isinstance(text, str):
        return text
    return re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', text)

SYSTEM_PROMPT = """You are an expert code security and quality auditor.
Analyse the provided source code and return ONLY a valid JSON array of issues.

Each issue must have exactly these fields:
{
  "issue_type": "string (Security Vulnerability | Performance Issue | Syntax Error | Code Quality | Best Practice)",
  "description": "string — clear explanation of the problem",
  "line_number": integer or 0 if not line-specific,
  "severity": "High | Medium | Low",
  "suggestion": "string — concrete fix or recommendation",
  "validation_type": "Security | Syntax | Performance | Best Practice"
}

Return [] if no issues are found.
Return ONLY the JSON array — no markdown, no prose, no explanation."""


def deepScanFile(
    filePath: str,
    fileContent: str,
    existingIssues: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Send the file to Claude for deep analysis.
    Returns:
        issues    : combined list (existing + LLM-found)
        scanTime  : seconds
        llmCalled : bool
        error     : str or None
    """
    startTime = time.time()
    client = _getClient()

    if not client:
        return {
            "issues"   : existingIssues,
            "scanTime" : 0,
            "llmCalled": False,
            "error"    : "Anthropic client not available — check ANTHROPIC_API_KEY",
        }

    # Truncate very large content to stay within context window
    maxChars = 12_000
    truncated = False
    content = fileContent
    if len(fileContent) > maxChars:
        content = fileContent[:maxChars]
        truncated = True

    existingSummary = ""
    if existingIssues:
        summaryLines = [
            f"  - Line {i['lineNumber']}: [{i['severity']}] {i['description']}"
            for i in existingIssues
        ]
        existingSummary = (
            "\n\nFast scanner already found these issues (do NOT duplicate them):\n"
            + "\n".join(summaryLines)
        )

    userMessage = (
        f"File: {filePath}"
        + (" (TRUNCATED — first 12,000 chars only)" if truncated else "")
        + existingSummary
        + f"\n\n```\n{content}\n```"
    )

    llmIssues: List[Dict[str, Any]] = []
    error = None

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": userMessage}],
            timeout=Config.LLM_TIMEOUT_SECONDS,
        )
        rawText = response.content[0].text.strip()

        # Strip markdown fences if present
        rawText = re.sub(r"^```[a-z]*\n?", "", rawText)
        rawText = re.sub(r"\n?```$", "", rawText)

        # ✅ ADD THIS CLEANING LINE (CRITICAL FIX)
        rawText = cleanText(rawText)
        try:
            parsed = json.loads(rawText)
        except Exception as e:
            error = f"Invalid JSON after cleaning: {e}"
            logger.warning(f"[deepScan] {filePath}: {error}")
            parsed = []

            llmIssues.append({
                "issueType": "LLM Response Error",
                "description": "Invalid AI response format",
                "actualIssue": f"Claude returned invalid JSON: {str(e)}",
                "lineNumber": 0,
                "severity": "Low",
                "suggestion": "Improve prompt or retry request",
                "validationType": "AI"
            })
        if isinstance(parsed, list):
            for item in parsed:
                desc = item.get("description", "")

                llmIssues.append({
                "issueType"      : item.get("issue_type", "Unknown"),
                "description"    : desc,
                "actualIssue"    : desc,   # 🔥 ADD THIS LINE (IMPORTANT)
                "lineNumber"     : int(item.get("line_number", 0)),
                "severity"       : item.get("severity", "Low"),
                "suggestion"     : item.get("suggestion", ""),
                "validationType" : item.get("validation_type", "Security"),
            })

    except json.JSONDecodeError as e:
        error = f"LLM returned non-JSON response: {e}"
        logger.warning(f"[deepScan] {filePath}: {error}")
    except Exception as e:
        error = f"LLM call failed: {type(e).__name__}: {e}"
        logger.error(f"[deepScan] {filePath}: {error}")

        # 🔥 ADD FALLBACK ISSUE
        llmIssues.append({
        "issueType": "LLM Analysis Failed",
        "description": "AI analysis could not be completed",
        "actualIssue": f"LLM failed due to: {str(e)}",
        "lineNumber": 0,
        "severity": "Low",
        "suggestion": "Check API key, network, or reduce file size",
        "validationType": "AI"
    })

    allIssues = existingIssues + llmIssues
    return {
        "issues"   : allIssues,
        "scanTime" : round(time.time() - startTime, 4),
        "llmCalled": True,
        "error"    : error,
    }
