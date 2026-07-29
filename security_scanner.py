"""
security_scanner.py
────────────────────────────────────────────────────────────────
Detects sensitive environment files (.env and variants) and common
secret patterns (API keys, tokens, passwords, credentials) in:
  1. Staged/committed files BEFORE a push (local git hook use)
  2. Files already present in a GitHub repository AFTER a push
     (GitHub API use, called from the Flask backend)

Produces structured, professional security recommendations that can
be rendered directly in the GitPulse dashboard.
"""

import re
import requests

# ─── Detection Patterns ───────────────────────────────

# Filenames that are always treated as sensitive, regardless of content.
ENV_FILENAME_PATTERN = re.compile(
    r'(^|/)\.env(\.(local|production|prod|development|dev|test|staging|ci))?$',
    re.IGNORECASE
)

# Other common secret-bearing filenames worth flagging too.
OTHER_SENSITIVE_FILENAME_PATTERN = re.compile(
    r'(^|/)('
    r'id_rsa|id_dsa|id_ecdsa|id_ed25519|'          # SSH private keys
    r'.*\.pem|.*\.pfx|.*\.p12|'                     # cert/key bundles
    r'credentials\.json|service[-_]account.*\.json|' # cloud service accounts
    r'secrets?\.ya?ml|secrets?\.json'
    r')$',
    re.IGNORECASE
)

# Content-based secret detection — catches secrets even if the filename
# itself looks innocent (e.g. config.py, settings.local.py).
SECRET_CONTENT_PATTERN = re.compile(
    r'(?i)('
    r'(api[_-]?key|secret[_-]?key|access[_-]?key|private[_-]?key|'
    r'password|passwd|token|credential)s?'
    r'\s*[:=]\s*[\'"]?[A-Za-z0-9/_\-\.\+]{6,}'
    r'|AKIA[0-9A-Z]{16}'                             # AWS access key id
    r'|sk-[A-Za-z0-9]{20,}'                           # OpenAI/Anthropic-style secret keys
    r'|ghp_[A-Za-z0-9]{36}'                           # GitHub personal access token
    r'|xox[baprs]-[A-Za-z0-9-]{10,}'                  # Slack tokens
    r')'
)

RISK_LEVEL = "High"


# ─── Recommendation Builders ──────────────────────────

def _before_push_recommendation(filename, reason):
    return {
        "status": "Before Push",
        "risk_level": RISK_LEVEL,
        "file": filename,
        "reason": reason,
        "recommended_action": (
            f"Do not push this file. Remove it from the commit "
            f"(`git rm --cached {filename}`), add `{filename}` to .gitignore, "
            f"and re-commit before pushing."
        ),
        "message": (
            f"⚠️ Recommendation: This commit contains a {filename} file that may "
            f"expose sensitive credentials. Do not push this file to the remote "
            f"repository. Add it to .gitignore and remove it from the commit "
            f"before pushing."
        ),
    }


def _already_pushed_recommendation(filename, reason):
    return {
        "status": "Already Pushed",
        "risk_level": RISK_LEVEL,
        "file": filename,
        "reason": reason,
        "recommended_action": (
            f"Remove {filename} from the full repository history (e.g. with "
            f"`git filter-repo` or BFG Repo-Cleaner — a normal `git rm` commit "
            f"is NOT enough), rotate every credential that was exposed, and add "
            f"`{filename}` to .gitignore immediately."
        ),
        "message": (
            f"🚨 Security Recommendation: A {filename} file has already been "
            f"pushed to the repository. This file may contain sensitive "
            f"credentials. Remove it from the repository history, rotate any "
            f"exposed secrets, and add {filename} to .gitignore immediately."
        ),
    }


# ─── File Classification ──────────────────────────────

def _classify_file(filename, content=None):
    """
    Returns a reason string if the file is sensitive, otherwise None.
    `content` is optional — pass it when available for deeper detection.
    """
    if ENV_FILENAME_PATTERN.search(filename):
        return f"Filename matches a known environment/secrets file pattern ({filename})."

    if OTHER_SENSITIVE_FILENAME_PATTERN.search(filename):
        return f"Filename matches a known credential/key file pattern ({filename})."

    if content and SECRET_CONTENT_PATTERN.search(content):
        return "File content matches a known secret pattern (API key, token, password, or credential)."

    return None


# ─── 1. BEFORE PUSH — local staged-file scan ──────────

def scan_staged_files(staged_files):
    """
    staged_files: list of dicts, e.g.
        [{"filename": ".env", "content": "DB_PASS=xxxx"}, ...]
    Returns a list of "Before Push" recommendations.
    Intended to be called from a local git pre-commit/pre-push hook,
    or from a CI job that has access to the diff.
    """
    recommendations = []
    for f in staged_files:
        filename = f.get("filename", "")
        content = f.get("content", "")
        reason = _classify_file(filename, content)
        if reason:
            recommendations.append(_before_push_recommendation(filename, reason))
    return recommendations


# ─── 2. ALREADY PUSHED — remote GitHub repo scan ──────

def scan_repo_for_pushed_secrets(repo_full_name, token, branch=None):
    """
    Scans the full file tree of a GitHub repo (via the Git Trees API) for
    committed .env files and other sensitive filenames. Returns a list of
    "Already Pushed" recommendations.

    Note: only checks filenames for the remote scan (fast, one API call).
    Deep content scanning of every file in a large repo is expensive and
    not done here — extend with a Contents API fetch per match if needed.
    """
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    if not branch:
        repo_resp = requests.get(f"https://api.github.com/repos/{repo_full_name}", headers=headers, timeout=10)
        repo_resp.raise_for_status()
        branch = repo_resp.json().get("default_branch", "main")

    tree_resp = requests.get(
        f"https://api.github.com/repos/{repo_full_name}/git/trees/{branch}?recursive=1",
        headers=headers,
        timeout=15,
    )
    tree_resp.raise_for_status()
    tree = tree_resp.json().get("tree", [])

    recommendations = []
    for entry in tree:
        if entry.get("type") != "blob":
            continue
        path = entry.get("path", "")
        reason = _classify_file(path)  # filename-only check, content not fetched
        if reason:
            recommendations.append(_already_pushed_recommendation(path, reason))

    return recommendations


# ─── 3. Combined scan used by the dashboard ───────────

def run_security_scan(repo_full_name, token, staged_files=None, branch=None):
    """
    Full scan combining both checks. `staged_files` is optional — pass it
    only if you have staged/diff data available (e.g. from a CI webhook).
    """
    recommendations = []

    if staged_files:
        recommendations.extend(scan_staged_files(staged_files))

    recommendations.extend(scan_repo_for_pushed_secrets(repo_full_name, token, branch))

    if not recommendations:
        return {
            "status": "clean",
            "message": "✅ No sensitive environment files detected.",
            "recommendations": [],
        }

    return {
        "status": "warning",
        "message": f"{len(recommendations)} sensitive file(s) detected.",
        "recommendations": recommendations,
    }
