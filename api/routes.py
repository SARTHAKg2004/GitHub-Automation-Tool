"""
api/routes.py
Flask REST API endpoints consumed by the dashboard.
"""

import os
import json
import threading
import time
from flask import Blueprint, request, jsonify, send_file, current_app

from modules.scanner import RepositoryScanner
from modules.reportGenerator import generateExcelReport
from modules.logger import getLogger
from database.db import createJob, completeJob, failJob, saveFileResults, getRecentJobs, getJob

logger = getLogger()

api = Blueprint("api", __name__, url_prefix="/api")

# In-memory progress store: { jobId: { completed, total, currentFile, status } }
_scanProgress: dict = {}
_scanLock = threading.Lock()


# ── Scan ──────────────────────────────────────────────────────────────────

@api.route("/scan", methods=["POST"])
def startScan():
    data = request.get_json(silent=True) or {}
    repoUrl = (data.get("repoUrl") or "").strip()

    if not repoUrl:
        return jsonify({"error": "repoUrl is required"}), 400

    # Basic URL validation
    if not repoUrl.startswith("http"):
        return jsonify({"error": "Invalid URL — must start with http(s)://"}), 400

    jobId = createJob(repoUrl)

    with _scanLock:
        _scanProgress[jobId] = {
            "completed"  : 0,
            "total"      : 0,
            "currentFile": "",
            "status"     : "running",
            "startTime"  : time.time(),
        }

    def progressCallback(completed, total, fileName):
        with _scanLock:
            _scanProgress[jobId] = {
                **_scanProgress.get(jobId, {}),
                "completed"  : completed,
                "total"      : total,
                "currentFile": fileName,
                "status"     : "running",
            }

    def runScan():
        try:
            scanner = RepositoryScanner(progressCallback=progressCallback)
            results = scanner.scanRepository(repoUrl)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            reportPath = os.path.join("uploads", f"report_{jobId}_{timestamp}.xlsx")
            generateExcelReport(results, reportPath)

            saveFileResults(jobId, results["files"])
            completeJob(jobId, results["summary"], reportPath)

            with _scanLock:
                _scanProgress[jobId]["status"] = "completed"
                _scanProgress[jobId]["reportPath"] = reportPath
                _scanProgress[jobId]["summary"] = results["summary"]

        except Exception as e:
            logger.error(f"Scan job {jobId} failed: {e}")
            failJob(jobId, str(e))
            with _scanLock:
                _scanProgress[jobId]["status"] = "failed"
                _scanProgress[jobId]["error"] = str(e)

    t = threading.Thread(target=runScan, daemon=True)
    t.start()

    return jsonify({"jobId": jobId, "message": "Scan started"}), 202


@api.route("/scan/<int:jobId>/progress", methods=["GET"])
def scanProgress(jobId):
    with _scanLock:
        prog = _scanProgress.get(jobId)
    if not prog:
        job = getJob(jobId)
        if job:
            return jsonify({"status": job["status"]})
        return jsonify({"error": "Job not found"}), 404
    return jsonify(prog)


@api.route("/scan/<int:jobId>/results", methods=["GET"])
def scanResults(jobId):
    with _scanLock:
        prog = _scanProgress.get(jobId, {})

    if prog.get("status") == "completed":
        return jsonify({
            "status" : "completed",
            "summary": prog.get("summary", {}),
        })
    elif prog.get("status") == "failed":
        return jsonify({"status": "failed", "error": prog.get("error", "Unknown error")}), 500

    return jsonify({"status": prog.get("status", "unknown")})


@api.route("/scan/<int:jobId>/report", methods=["GET"])
def downloadReport(jobId):
    with _scanLock:
        prog = _scanProgress.get(jobId, {})

    reportPath = prog.get("reportPath")
    if not reportPath:
        job = getJob(jobId)
        if job:
            reportPath = job.get("reportPath")

    if not reportPath or not os.path.exists(reportPath):
        return jsonify({"error": "Report not found or scan not complete"}), 404

    return send_file(
        os.path.abspath(reportPath),
        as_attachment=True,
        download_name=f"scan_report_job{jobId}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── History ───────────────────────────────────────────────────────────────

@api.route("/history", methods=["GET"])
def scanHistory():
    jobs = getRecentJobs()
    return jsonify(jobs)


# ── Health ────────────────────────────────────────────────────────────────

@api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})
