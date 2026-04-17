"""
modules/config.py
Loads and validates all environment configuration.
"""

import os
from dotenv import load_dotenv

# Load .env from project root
_root = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(_root, ".env"))


class Config:
    # ── API ────────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # ── Scanner ────────────────────────────────────────────────────────────
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "8"))
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    DEEP_SCAN_THRESHOLD: int = int(os.getenv("DEEP_SCAN_THRESHOLD", "3"))
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    # ── Dashboard ──────────────────────────────────────────────────────────
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "5000"))
    DASHBOARD_HOST: str = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # ── Paths ──────────────────────────────────────────────────────────────
    ROOT_DIR: str = _root
    UPLOAD_DIR: str = os.path.join(_root, os.getenv("UPLOAD_DIR", "uploads"))
    LOG_DIR: str = os.path.join(_root, os.getenv("LOG_DIR", "logs"))
    DB_PATH: str = os.path.join(_root, os.getenv("DB_PATH", "database/validator.db"))

    # ── Git ────────────────────────────────────────────────────────────────
    GIT_CLONE_TIMEOUT: int = int(os.getenv("GIT_CLONE_TIMEOUT", "120"))
    GIT_DEPTH: int = int(os.getenv("GIT_DEPTH", "1"))

    # ── File classification maps ───────────────────────────────────────────
    FRONTEND_EXTENSIONS = {".html", ".htm", ".css", ".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte"}
    BACKEND_EXTENSIONS  = {".py", ".java", ".php", ".cpp", ".c", ".cs", ".go", ".rb", ".rs", ".kt", ".swift"}
    CONFIG_EXTENSIONS   = {".json", ".yaml", ".yml", ".env", ".toml", ".ini", ".cfg", ".xml", ".conf"}
    BINARY_EXTENSIONS   = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".ico",
        ".mp4", ".mp3", ".wav", ".avi", ".mov",
        ".zip", ".tar", ".gz", ".rar", ".7z",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".exe", ".dll", ".so", ".dylib", ".bin", ".obj",
        ".pyc", ".class", ".jar",
        ".woff", ".woff2", ".ttf", ".eot",
    }

    # ── Suspicious rule-based patterns ────────────────────────────────────
    DANGEROUS_PATTERNS = [
        (r'\beval\s*\(', "eval() usage detected", "High", "Security"),
        (r'\bexec\s*\(', "exec() usage detected", "High", "Security"),
        (r'(?i)password\s*=\s*["\'][^"\']{4,}', "Hardcoded password detected", "High", "Security"),
        (r'(?i)(api_key|apikey|secret_key|auth_token)\s*=\s*["\'][^"\']{8,}', "Hardcoded API key/secret", "High", "Security"),
        (r'(?i)-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----', "Private key material in source", "High", "Security"),
        (r'(?i)(aws_access_key_id|aws_secret_access_key)\s*=', "AWS credentials detected", "High", "Security"),
        (r'\bos\.system\s*\(', "os.system() shell injection risk", "Medium", "Security"),
        (r'\bsubprocess\.call\s*\(.*shell\s*=\s*True', "subprocess with shell=True", "Medium", "Security"),
        (r'(?i)TODO|FIXME|HACK|XXX', "Code smell / unresolved TODO", "Low", "Best Practice"),
        (r'print\s*\(.*password', "Possible password printed to stdout", "Medium", "Security"),
        (r'(?i)http://(?!localhost|127\.0\.0\.1)', "Insecure HTTP URL (use HTTPS)", "Low", "Security"),
        (r'\bpickle\.loads?\s*\(', "Unsafe pickle deserialization", "High", "Security"),
        (r'__import__\s*\(', "Dynamic __import__ usage", "Medium", "Security"),
        (r'(?i)(input|raw_input)\s*\(', "Unvalidated user input", "Low", "Security"),
        (r'time\.sleep\s*\([5-9]\d*\.\d*|\d{2,}', "Long sleep call may cause performance issues", "Low", "Performance"),
        (r'\bSELECT\s+\*\s+FROM\b', "SELECT * query — performance issue", "Low", "Performance"),
        (r'(?i)format_string|%s.*sql|f".*SELECT', "Possible SQL injection via string format", "High", "Security"),
    ]

    @classmethod
    def ensureDirectories(cls):
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        os.makedirs(cls.LOG_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(cls.DB_PATH), exist_ok=True)


Config.ensureDirectories()
