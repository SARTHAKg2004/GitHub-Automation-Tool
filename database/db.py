"""
database/db.py
SQLite persistence for scan jobs and history.
"""

import sqlite3
import json
import os
import time
from typing import Optional, List, Dict, Any
from modules.config import Config
from modules.logger import getLogger

logger = getLogger()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initDb():
    """Create tables if they don't exist."""
    conn = _connect()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS scan_jobs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                repoUrl     TEXT    NOT NULL,
                startedAt   REAL    NOT NULL,
                finishedAt  REAL,
                status      TEXT    DEFAULT 'running',
                totalFiles  INTEGER DEFAULT 0,
                totalIssues INTEGER DEFAULT 0,
                reportPath  TEXT,
                summary     TEXT
            );

            CREATE TABLE IF NOT EXISTS scan_files (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                jobId       INTEGER NOT NULL,
                fileName    TEXT,
                filePath    TEXT,
                fileType    TEXT,
                codeType    TEXT,
                scanStatus  TEXT,
                issuesFound INTEGER DEFAULT 0,
                scanMode    TEXT,
                processingTime REAL,
                errorMessage TEXT,
                skippedReason TEXT,
                issuesJson  TEXT,
                FOREIGN KEY (jobId) REFERENCES scan_jobs(id)
            );
        """)
        conn.commit()
        logger.info("Database initialised")
    finally:
        conn.close()


def createJob(repoUrl: str) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO scan_jobs (repoUrl, startedAt, status) VALUES (?, ?, 'running')",
            (repoUrl, time.time()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def completeJob(jobId: int, summary: Dict[str, Any], reportPath: str):
    conn = _connect()
    try:
        conn.execute(
            """UPDATE scan_jobs
               SET finishedAt=?, status='completed', totalFiles=?, totalIssues=?,
                   reportPath=?, summary=?
               WHERE id=?""",
            (
                time.time(),
                summary.get("totalFiles", 0),
                summary.get("totalIssues", 0),
                reportPath,
                json.dumps(summary),
                jobId,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def failJob(jobId: int, error: str):
    conn = _connect()
    try:
        conn.execute(
            "UPDATE scan_jobs SET finishedAt=?, status='failed', summary=? WHERE id=?",
            (time.time(), json.dumps({"error": error}), jobId),
        )
        conn.commit()
    finally:
        conn.close()


def saveFileResults(jobId: int, fileResults: List[Dict[str, Any]]):
    conn = _connect()
    try:
        rows = [
            (
                jobId,
                fr["fileName"],
                fr["filePath"],
                fr["fileType"],
                fr["codeType"],
                fr["scanStatus"],
                fr["issuesFound"],
                fr["scanMode"],
                fr["processingTime"],
                fr.get("errorMessage", ""),
                fr.get("skippedReason", ""),
                json.dumps(fr.get("issues", [])),
            )
            for fr in fileResults
        ]
        conn.executemany(
            """INSERT INTO scan_files
               (jobId, fileName, filePath, fileType, codeType, scanStatus,
                issuesFound, scanMode, processingTime, errorMessage, skippedReason, issuesJson)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def getRecentJobs(limit: int = 20) -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM scan_jobs ORDER BY startedAt DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def getJob(jobId: int) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM scan_jobs WHERE id=?", (jobId,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


initDb()
