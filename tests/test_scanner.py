"""
tests/test_scanner.py
Unit tests for core scanner components.
Run: python -m pytest tests/ -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.fileClassifier import classifyFile, isBinaryFile, isTextReadable, getFileExtension
from modules.fastScanner import fastScanFile


class TestFileClassifier(unittest.TestCase):

    def test_frontendExtensions(self):
        self.assertEqual(classifyFile("app/index.html"), "Frontend")
        self.assertEqual(classifyFile("styles/main.css"),  "Frontend")
        self.assertEqual(classifyFile("src/app.tsx"),       "Frontend")

    def test_backendExtensions(self):
        self.assertEqual(classifyFile("server/app.py"),   "Backend")
        self.assertEqual(classifyFile("Main.java"),        "Backend")
        self.assertEqual(classifyFile("handler.php"),      "Backend")

    def test_configExtensions(self):
        self.assertEqual(classifyFile("config.yaml"), "Config")
        self.assertEqual(classifyFile(".env"),         "Config")
        self.assertEqual(classifyFile("package.json"), "Config")

    def test_binaryExtensions(self):
        self.assertTrue(isBinaryFile("logo.png"))
        self.assertTrue(isBinaryFile("archive.zip"))
        self.assertEqual(classifyFile("logo.png"), "Binary")

    def test_unknownExtension(self):
        self.assertEqual(classifyFile("notes.xyz"), "Unknown")

    def test_noExtension(self):
        self.assertEqual(classifyFile("Dockerfile"),  "Config")
        self.assertEqual(classifyFile("Makefile"),    "Config")

    def test_getFileExtension(self):
        self.assertEqual(getFileExtension("app.py"),  ".py")
        self.assertEqual(getFileExtension("README"),  "(none)")


class TestFastScanner(unittest.TestCase):

    def _tmpFile(self, content: str, suffix: str = ".py") -> str:
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        )
        f.write(content)
        f.flush()
        f.close()
        return f.name

    def tearDown(self):
        # Clean up temp files
        pass

    def test_detectsEval(self):
        fp = self._tmpFile('result = eval(user_input)')
        result = fastScanFile(fp, 'result = eval(user_input)')
        types = [i["issueType"] for i in result["issues"]]
        self.assertTrue(any("Security" in t for t in types))
        os.unlink(fp)

    def test_detectsHardcodedPassword(self):
        content = 'PASSWORD = "supersecret123"'
        fp = self._tmpFile(content)
        result = fastScanFile(fp, content)
        descriptions = " ".join(i["description"] for i in result["issues"])
        self.assertIn("password", descriptions.lower())
        os.unlink(fp)

    def test_emptyFile(self):
        fp = self._tmpFile("")
        result = fastScanFile(fp, "")
        self.assertTrue(result["isEmpty"])
        types = [i["issueType"] for i in result["issues"]]
        self.assertIn("Empty File", types)
        os.unlink(fp)

    def test_cleanFile(self):
        content = 'def add(a, b):\n    return a + b\n'
        fp = self._tmpFile(content)
        result = fastScanFile(fp, content)
        self.assertEqual(len(result["issues"]), 0)
        os.unlink(fp)

    def test_syntaxError(self):
        content = 'def broken(\n    pass\n'
        fp = self._tmpFile(content)
        result = fastScanFile(fp, content)
        types = [i["issueType"] for i in result["issues"]]
        self.assertIn("Syntax Error", types)
        os.unlink(fp)

    def test_multipleIssuesOnDifferentLines(self):
        content = (
            'password = "abc123"\n'
            'result = eval(x)\n'
            'import os; os.system("ls")\n'
        )
        fp = self._tmpFile(content)
        result = fastScanFile(fp, content)
        self.assertGreaterEqual(len(result["issues"]), 3)
        os.unlink(fp)

    def test_scanTimeRecorded(self):
        fp = self._tmpFile("x = 1")
        result = fastScanFile(fp, "x = 1")
        self.assertGreaterEqual(result["scanTime"], 0)
        os.unlink(fp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
