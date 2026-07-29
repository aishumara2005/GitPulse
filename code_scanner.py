"""
Code Scanner: Scans GitHub repo files for common errors and bad practices.
No external linting tools required – pure Python regex + heuristics.
"""
import re
from utils.github_api import GitHubAPI

SCANNABLE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb"}

PATTERNS = [
    # Security
    {"id": "HARDCODED_SECRET", "severity": "critical",
     "pattern": r'(?i)(password|secret|api_key|token|passwd)\s*=\s*["\'][^"\']{4,}["\']',
     "message": "Possible hardcoded secret/password detected"},
    {"id": "SQL_INJECTION", "severity": "high",
     "pattern": r'(?i)(execute|query)\s*\(\s*["\'].*%s.*["\']',
     "message": "Possible SQL injection via string formatting"},
    {"id": "EVAL_USAGE", "severity": "high",
     "pattern": r'\beval\s*\(',
     "message": "Use of eval() is dangerous"},
    {"id": "SHELL_INJECTION", "severity": "high",
     "pattern": r'(?i)(os\.system|subprocess\.call|popen)\s*\(',
     "message": "Shell command execution – ensure inputs are sanitized"},

    # Python specifics
    {"id": "BARE_EXCEPT", "severity": "medium",
     "pattern": r'except\s*:',
     "message": "Bare except clause catches all exceptions including SystemExit"},
    {"id": "PRINT_DEBUG", "severity": "low",
     "pattern": r'^\s*print\s*\(',
     "message": "Debug print statement found"},
    {"id": "TODO_FIXME", "severity": "info",
     "pattern": r'(?i)#\s*(todo|fixme|hack|xxx)\b',
     "message": "TODO/FIXME comment – technical debt"},
    {"id": "MUTABLE_DEFAULT", "severity": "medium",
     "pattern": r'def \w+\([^)]*=\s*[\[\{]',
     "message": "Mutable default argument in function definition"},

    # JS/TS
    {"id": "CONSOLE_LOG", "severity": "low",
     "pattern": r'\bconsole\.(log|debug|warn|error)\s*\(',
     "message": "Console statement found – remove before production"},
    {"id": "DANGEROUSLYSETHTML", "severity": "high",
     "pattern": r'dangerouslySetInnerHTML',
     "message": "dangerouslySetInnerHTML can lead to XSS vulnerabilities"},
]

MAX_LINES_PER_FILE = 500
MAX_FILES_TO_SCAN  = 50

class CodeScanner:
    def __init__(self, gh: GitHubAPI):
        self.gh = gh

    def scan_repository(self, repo: str) -> dict:
        all_files = self.gh.get_repo_tree(repo)
        scannable = [
            f for f in all_files
            if any(f.endswith(ext) for ext in SCANNABLE_EXTENSIONS)
        ][:MAX_FILES_TO_SCAN]

        results = []
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        files_scanned = 0

        for filepath in scannable:
            content = self.gh.get_file_content(repo, filepath)
            if not content:
                continue
            files_scanned += 1
            lines = content.splitlines()[:MAX_LINES_PER_FILE]
            file_issues = []

            for lineno, line in enumerate(lines, start=1):
                for pat in PATTERNS:
                    if re.search(pat["pattern"], line):
                        issue = {
                            "line": lineno,
                            "code": line.strip()[:120],
                            "rule_id": pat["id"],
                            "severity": pat["severity"],
                            "message": pat["message"],
                        }
                        file_issues.append(issue)
                        summary[pat["severity"]] += 1

            if file_issues:
                results.append({"file": filepath, "issues": file_issues})

        return {
            "repo": repo,
            "files_scanned": files_scanned,
            "files_with_issues": len(results),
            "summary": summary,
            "total_issues": sum(summary.values()),
            "results": results,
        }
