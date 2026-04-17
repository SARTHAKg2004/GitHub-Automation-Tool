"""
modules/scanner.py
Core orchestration: clone → enumerate → fast scan → (optional) deep scan.
Enhanced with incremental scanning + GitHub Actions support.
"""

import os
import time
import shutil
import tempfile
import traceback
import chardet
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Callable

import git

from modules.config import Config
from modules.logger import getLogger
from modules.fileClassifier import (
    classifyFile, isBinaryFile, getFileExtension
)
from modules.fastScanner import fastScanFile
from modules.deepScanner import deepScanFile

logger = getLogger()


# 🔥 NEW: Code file extensions for incremental filtering
_CODE_EXTENSIONS = (
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".kt", ".go", ".rb", ".rs", ".cpp", ".c",
    ".html", ".css", ".json", ".yaml", ".yml", ".xml"
)


# 🔥 NEW: Helper function for incremental scanning
def get_changed_files(file_path="changed_files.txt"):
    if not os.path.isfile(file_path):
        return None

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        files = [line.strip() for line in f.readlines() if line.strip()]

    if not files:
        return None

    files = [f for f in files if os.path.splitext(f)[1].lower() in _CODE_EXTENSIONS]

    return files if files else None


class RepositoryScanner:
    def __init__(
        self,
        maxWorkers: int = None,
        deepScanThreshold: int = None,
        progressCallback: Optional[Callable[[int, int, str], None]] = None,
    ):
        self.maxWorkers = maxWorkers or Config.MAX_WORKERS
        self.deepScanThreshold = deepScanThreshold or Config.DEEP_SCAN_THRESHOLD
        self.progressCallback = progressCallback
        self._stopRequested = False

    def scanRepository(
        self,
        repoUrl: str,
        changed_files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:

        overallStart = time.time()
        cloneDir = None

        try:
            repoUrl = self._sanitizeUrl(repoUrl)

            # 🔥 NEW: GitHub Actions detection
            in_github = os.getenv("GITHUB_ACTIONS") == "true"

            if in_github:
                repoRoot = os.getcwd()
                logger.info(f"Using GitHub Actions repo at: {repoRoot}")
            else:
                cloneDir = self._cloneRepository(repoUrl)
                repoRoot = cloneDir

            # 🔥 NEW: Incremental scan logic
            if changed_files:
                logger.info(f"⚡ Incremental scan: {len(changed_files)} files")

                allFiles = []
                for rel_path in changed_files:
                    abs_path = os.path.join(repoRoot, rel_path)
                    if os.path.isfile(abs_path):
                        allFiles.append(abs_path)
                    else:
                        logger.warning(f"Skipped missing file: {rel_path}")

                if not allFiles:
                    logger.warning("No valid changed files → fallback to full scan")
                    allFiles = self._enumerateFiles(repoRoot)

            else:
                logger.info("🔄 Full scan")
                allFiles = self._enumerateFiles(repoRoot)

            logger.info(f"Found {len(allFiles)} files to scan in {repoUrl}")

            fileResults = self._scanAllFiles(allFiles, repoRoot)

            summary = self._buildSummary(fileResults)
            summary["repoUrl"] = repoUrl
            summary["totalTime"] = round(time.time() - overallStart, 2)
            summary["scanType"] = "Incremental" if changed_files else "Full"

            return {"files": fileResults, "summary": summary}

        except Exception as e:
            logger.error(f"scanRepository failed: {e}\n{traceback.format_exc()}")
            raise

        finally:
            if cloneDir and os.path.exists(cloneDir):
                shutil.rmtree(cloneDir, ignore_errors=True)
                logger.info(f"Cleaned up clone directory: {cloneDir}")

    def stopScan(self):
        self._stopRequested = True

    @staticmethod
    def _sanitizeUrl(url: str) -> str:
        url = url.strip()
        if not url.startswith("http"):
            raise ValueError(f"Invalid repository URL: {url}")
        if url.endswith(".git"):
            url = url[:-4]
        return url

    def _cloneRepository(self, repoUrl: str) -> str:
        cloneDir = tempfile.mkdtemp(prefix="ghvalidator_", dir=Config.UPLOAD_DIR)
        logger.info(f"Cloning {repoUrl} → {cloneDir}")
        try:
            git.Repo.clone_from(repoUrl, cloneDir, depth=Config.GIT_DEPTH)
            return cloneDir
        except git.exc.GitCommandError as e:
            shutil.rmtree(cloneDir, ignore_errors=True)
            raise RuntimeError(f"Git clone failed: {e}") from e

    @staticmethod
    def _enumerateFiles(rootDir: str) -> List[str]:
        files = []
        skipDirs = {".git", "__pycache__", "node_modules", ".venv", "venv"}
        for dirPath, dirNames, fileNames in os.walk(rootDir):
            dirNames[:] = [d for d in dirNames if d not in skipDirs]
            for fileName in fileNames:
                files.append(os.path.join(dirPath, fileName))
        return files

    def _scanAllFiles(self, filePaths: List[str], repoRoot: str) -> List[Dict[str, Any]]:
        results = []
        total = len(filePaths)
        completed = 0

        with ThreadPoolExecutor(max_workers=self.maxWorkers) as executor:
            futureMap = {
                executor.submit(self._scanSingleFile, fp, repoRoot): fp
                for fp in filePaths
            }

            for future in as_completed(futureMap):
                if self._stopRequested:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                filePath = futureMap[future]

                try:
                    result = future.result(timeout=Config.LLM_TIMEOUT_SECONDS + 10)
                except Exception as e:
                    result = self._buildErrorResult(filePath, repoRoot, str(e))

                results.append(result)
                completed += 1

                if self.progressCallback:
                    self.progressCallback(completed, total, os.path.basename(filePath))

        return results

    def _scanSingleFile(self, filePath: str, repoRoot: str) -> Dict[str, Any]:
        relPath = os.path.relpath(filePath, repoRoot)
        fileName = os.path.basename(filePath)
        extension = getFileExtension(filePath)
        codeType = classifyFile(filePath)
        fileStart = time.time()

        baseResult = {
            "fileName": fileName,
            "filePath": relPath,
            "fileType": extension,
            "codeType": codeType,
            "scanStatus": "Success",
            "issuesFound": 0,
            "issues": [],
            "scanMode": "Fast",
            "errorMessage": "",
            "skippedReason": "",
            "processingTime": 0.0,
            "truncated": False,
            "lineCount": 0,
            "linesScanned": 0,
        }

        if codeType == "Binary" or isBinaryFile(filePath):
            baseResult["scanStatus"] = "Skipped"
            baseResult["skippedReason"] = "Binary file"
            baseResult["processingTime"] = round(time.time() - fileStart, 4)
            return baseResult

        content, error = self._readFile(filePath)
        if error:
            baseResult["scanStatus"] = "Skipped"
            baseResult["errorMessage"] = error
            return baseResult

        fastResult = fastScanFile(filePath, content)
        issues = fastResult["issues"]

        if len(issues) >= self.deepScanThreshold and Config.ANTHROPIC_API_KEY:
            deepResult = deepScanFile(filePath, content, issues)
            issues = deepResult["issues"]

        baseResult.update({
            "issuesFound": len(issues),
            "issues": issues,
            "scanStatus": "Clean" if not issues else "Success",
            "processingTime": round(time.time() - fileStart, 4),
        })

        return baseResult

    @staticmethod
    def _readFile(filePath: str):
        try:
            with open(filePath, "rb") as f:
                raw = f.read()

            try:
                return raw.decode("utf-8"), None
            except:
                return raw.decode("latin-1", errors="replace"), None

        except Exception as e:
            return None, str(e)

    @staticmethod
    def _buildErrorResult(filePath, repoRoot, error):
        return {
            "fileName": os.path.basename(filePath),
            "filePath": os.path.relpath(filePath, repoRoot),
            "scanStatus": "Failed",
            "errorMessage": error,
            "issuesFound": 0,
            "issues": []
        }

    @staticmethod
    def _buildSummary(results):
        return {
            "totalFiles": len(results),
            "totalIssues": sum(r["issuesFound"] for r in results),
            "cleanFiles": sum(1 for r in results if r["scanStatus"] == "Clean"),
            "failedFiles": sum(1 for r in results if r["scanStatus"] == "Failed"),
            "skippedFiles": sum(1 for r in results if r["scanStatus"] == "Skipped"),
        }