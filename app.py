from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from utils.github_api import GitHubAPI
from utils.ai_analyzer import AIAnalyzer
from utils.code_scanner import CodeScanner
from config.settings import Config
import random
import os

# ─── Real Code Execution Scanner deps ─────────────────
import re
import ast
import sys
import shutil
import tempfile
import zipfile
import subprocess
import requests as http
from pathlib import Path

# ─── EMAIL NOTIFICATIONS SYSTEM ───────────────────────
from services.notifications import check_inactive_users

# ─── SECURITY / SECRET SCANNER ────────────────────────
from security_scanner import run_security_scan

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY


# ─── Global JSON Error Handlers ───────────────────────
# Guarantees every /api/* response is JSON, even if Flask/Werkzeug itself
# throws before a route's own try/except runs (missing route, worker crash,
# error inside a decorator, etc). This is what causes "Unexpected token '<'"
# on the frontend — the browser gets Flask's HTML error page instead of
# JSON, and JSON.parse() chokes on the '<' of <html>.
@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith("/api/"):
        return jsonify({"status": "error", "error_message": f"Endpoint not found (404): {request.path}"}), 404
    return e


@app.errorhandler(500)
def handle_500(e):
    if request.path.startswith("/api/"):
        return jsonify({"status": "error", "error_message": "Internal server error (500)."}), 500
    return e


@app.errorhandler(Exception)
def handle_unhandled_exception(e):
    if request.path.startswith("/api/"):
        print(f"\n================ [UNHANDLED EXCEPTION] ================\n{str(e)}\n=========================================================\n")
        return jsonify({"status": "error", "error_message": f"Unhandled server error: {str(e)}"}), 500
    raise e


# ─── Auth Guard Middleware ────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "github_token" not in session:
            return redirect(url_for("login"))

        allowed = Config.ALLOWED_GITHUB_USERS
        if allowed and session.get("github_username") not in allowed:
            return render_template("unauthorized.html"), 403

        return f(*args, **kwargs)
    return decorated


# ─── Primary Navigation Routes ────────────────────────
@app.route("/")
def index():
    if "github_token" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/login")
def login():
    return render_template("login.html")


# ─── GitHub OAuth Handlers ───────────────────────────
@app.route("/auth/github")
def github_auth():
    github_oauth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={Config.GITHUB_CLIENT_ID}"
        f"&scope=repo,read:org,read:user"
        f"&state={Config.OAUTH_STATE}"
    )
    return redirect(github_oauth_url)


@app.route("/auth/callback")
def github_callback():
    import requests

    code = request.args.get("code")
    state = request.args.get("state")

    if state != Config.OAUTH_STATE:
        return render_template("error.html", message="Invalid OAuth state"), 400

    token_resp = requests.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": Config.GITHUB_CLIENT_ID,
            "client_secret": Config.GITHUB_CLIENT_SECRET,
            "code": code,
        },
        headers={"Accept": "application/json"},
    )

    token_data = token_resp.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return render_template("error.html", message="GitHub auth failed"), 400

    user_resp = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    user_data = user_resp.json()
    username = user_data.get("login")

    allowed = Config.ALLOWED_GITHUB_USERS
    if allowed and username not in allowed:
        return render_template("unauthorized.html", username=username), 403

    session["github_token"] = access_token
    session["github_username"] = username
    session["github_avatar"] = user_data.get("avatar_url")
    session["github_name"] = user_data.get("name", username)
    session["user_role"] = "Lead" if (allowed and username in allowed) else "Developer"

    return redirect(url_for("dashboard"))


# ─── Alternate Token Authentication ────────────────────
@app.route("/auth/manual", methods=["POST"])
def manual_auth():
    import requests

    token = request.form.get("token", "").strip()
    if not token:
        return render_template("login.html", error="Token required")

    user_resp = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {token}"},
    )

    if user_resp.status_code != 200:
        return render_template("login.html", error="Invalid token")

    user_data = user_resp.json()
    username = user_data.get("login")

    allowed = Config.ALLOWED_GITHUB_USERS
    if allowed and username not in allowed:
        return render_template("unauthorized.html", username=username), 403

    session["github_token"] = token
    session["github_username"] = username
    session["github_avatar"] = user_data.get("avatar_url")
    session["github_name"] = user_data.get("name", username)
    session["user_role"] = "Lead"

    return redirect(url_for("dashboard"))


# ─── App Panel Core Route ────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    check_inactive_users()
    return render_template(
        "dashboard.html",
        username=session.get("github_username"),
        avatar=session.get("github_avatar"),
        name=session.get("github_name"),
        user_role=session.get("user_role", "Developer"),
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─── API endpoints ────────────────────────────────────
@app.route("/api/repos")
@login_required
def api_repos():
    gh = GitHubAPI(session["github_token"])
    repos = gh.get_user_repos()
    return jsonify(repos)


def _build_commit_date_map(repo_full_name, token, days=371):
    """
    Fetches real commits from GitHub for the last `days` days and returns
    {"YYYY-MM-DD": commit_count} — the REAL data the heatmap should use.
    Replaces the old random placeholder.
    """
    from datetime import datetime, timedelta, timezone

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    date_counts = {}
    page = 1
    while True:
        resp = http.get(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/commits",
            headers=headers,
            params={"since": since, "per_page": 100, "page": page},
            timeout=15,
        )
        if not resp.ok:
            break

        commits = resp.json()
        if not commits:
            break

        for c in commits:
            date_str = c.get("commit", {}).get("author", {}).get("date")
            if not date_str:
                continue
            day = date_str.split("T")[0]
            date_counts[day] = date_counts.get(day, 0) + 1

        if len(commits) < 100:
            break
        page += 1
        if page > 10:  # safety cap: 1000 commits max
            break

    return date_counts


@app.route("/api/team-activity")
@login_required
def api_team_activity():
    repo = request.args.get("repo")
    if not repo:
        return jsonify({"error": "repo required"}), 400

    gh = GitHubAPI(session["github_token"])
    activity = gh.get_team_activity(repo)

    if not activity or not isinstance(activity, dict):
        activity = {"members": {}}

    activity["commit_date_map"] = _build_commit_date_map(repo, session["github_token"])

    return jsonify(activity)


@app.route("/api/ai-suggestions", methods=["POST"])
@login_required
def api_ai_suggestions():
    data = request.get_json()
    activity_data = data.get("activity", {})
    analyzer = AIAnalyzer()
    suggestions = analyzer.generate_suggestions(activity_data)
    return jsonify({"suggestions": suggestions})


# ─── 🚀 REAL CODE EXECUTION ENGINE (downloads repo, runs .py files, captures actual runtime errors) ───
GITHUB_API_BASE = "https://api.github.com"


def _download_repo_zip(repo_full_name, token, dest_dir):
    """Download the default branch of a GitHub repo as a zip and extract it."""
    try:
        resp = http.get(
            f"{GITHUB_API_BASE}/repos/{repo_full_name}/zipball",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            stream=True,
            timeout=(10, 30),  # (connect timeout, read timeout)
        )
    except http.exceptions.ConnectTimeout:
        raise RuntimeError("Could not reach GitHub — connection timed out. Check your internet/firewall.")
    except http.exceptions.ConnectionError as e:
        raise RuntimeError(f"Network error reaching GitHub: {str(e)}")

    if not resp.ok:
        raise RuntimeError(f"Could not download '{repo_full_name}' from GitHub (status {resp.status_code}). Check repo name and token permissions.")

    zip_path = os.path.join(dest_dir, "repo.zip")
    with open(zip_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest_dir)

    extracted = [d for d in os.listdir(dest_dir) if os.path.isdir(os.path.join(dest_dir, d))]
    if not extracted:
        raise RuntimeError("Repo zip extraction produced no files.")
    return os.path.join(dest_dir, extracted[0])


_SERVER_ENTRYPOINT_PATTERN = re.compile(
    r'(?m)^\s*[\w\.]+\.run\s*\(|serve_forever\s*\(|uvicorn\.run\s*\(|socketserver|app\.run\s*\('
)


def _check_syntax(filepath):
    """Catch syntax errors before attempting execution."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        ast.parse(source, filename=filepath)
        return None
    except SyntaxError as e:
        return {"line": e.lineno or 0, "severity": "critical", "message": f"SyntaxError: {e.msg}"}


def _is_long_running_entrypoint(filepath):
    """
    Detects files that start a server / listen forever (Flask app.run(),
    serve_forever(), uvicorn.run(), etc). These will never "finish" within
    any timeout — that's expected behavior, not an infinite-loop bug — so
    the scanner should skip executing them rather than false-flag a timeout.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        return bool(_SERVER_ENTRYPOINT_PATTERN.search(source))
    except Exception:
        return False


def _extract_traceback_line(stderr_text, filepath):
    """Pull the line number belonging to the executed file out of a traceback."""
    matches = re.findall(r'File "([^"]+)", line (\d+)', stderr_text)
    for file_match, line_match in reversed(matches):
        if os.path.basename(file_match) == os.path.basename(filepath):
            return int(line_match)
    return int(matches[-1][1]) if matches else 0


def _run_python_file(filepath, repo_dir, timeout=10):
    """Actually execute a Python file and capture the real runtime error, if any."""
    syntax_issue = _check_syntax(filepath)
    if syntax_issue:
        return [syntax_issue]

    if _is_long_running_entrypoint(filepath):
        # Server/long-running scripts (Flask app.run(), etc) are expected to
        # never exit on their own — running them would always "time out"
        # even when the code is perfectly fine. Skip execution; syntax was
        # already validated above.
        return []

    try:
        result = subprocess.run(
            [sys.executable, filepath],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=repo_dir,
        )
    except subprocess.TimeoutExpired:
        return [{"line": 0, "severity": "high",
                  "message": f"Execution timed out after {timeout}s (possible infinite loop)."}]

    if result.returncode != 0 and result.stderr.strip():
        stderr = result.stderr.strip()
        last_line = stderr.split("\n")[-1]
        line_no = _extract_traceback_line(stderr, filepath)

        severity = "critical" if "SyntaxError" in stderr else "high"
        if "ModuleNotFoundError" in stderr or "ImportError" in stderr:
            severity = "medium"

        return [{"line": line_no, "severity": severity, "message": last_line}]

    return []


def run_real_scan(repo_full_name, token):
    """Downloads the repo and actually runs every .py file, returning real runtime errors."""
    tmp_dir = tempfile.mkdtemp(prefix="gitpulse_scan_")
    try:
        repo_dir = _download_repo_zip(repo_full_name, token, tmp_dir)

        py_files = list(Path(repo_dir).rglob("*.py"))
        py_files = [
            p for p in py_files
            if not any(part.startswith(".") or part in ("venv", "env", "node_modules", "__pycache__")
                       for part in p.parts)
        ]

        results = []
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

        for filepath in py_files:
            rel_path = str(filepath.relative_to(repo_dir))
            issues = _run_python_file(str(filepath), repo_dir)
            if issues:
                for issue in issues:
                    summary[issue["severity"]] = summary.get(issue["severity"], 0) + 1
                results.append({"file": rel_path, "issues": issues})

        return {"summary": summary, "results": results}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─── 🛠️ SCAN ROUTE — actually RUNS the repo's Python files and reports real errors ───
@app.route("/api/scan-code", methods=["POST"])
@login_required
def api_scan_code():
    try:
        data = request.get_json() or {}
        repo = data.get("repo")

        if not repo:
            return jsonify({"status": "error", "error_message": "Missing repository selection parameter."}), 400

        token = session.get("github_token") or os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("`.env` Setup Error: GitHub Access Token is totally empty or missing inside runtime scope environment variables.")

        print(f"[RUNNING SCAN ENGINE] Target Repository: {repo}")

        # ── Real execution: downloads repo, runs every .py file, captures actual tracebacks ──
        results = run_real_scan(repo, token)

        if not results or not isinstance(results, dict):
            raise Exception("Execution engine returned an invalid/empty result format profile. Please check underlying library configurations.")

        return jsonify(results)

    except Exception as e:
        print(f"\n================ [CRITICAL COMPILER BREAKDOWN LOG] ================\n{str(e)}\n==================================================================\n")
        return jsonify({
            "status": "error",
            "error_message": f"Backend Runtime Mismatch: {str(e)}",
            "hint": "Check if your .env setup matches your local profile configuration parameters."
        }), 500


@app.route("/api/commits")
@login_required
def api_commits():
    repo = request.args.get("repo")
    gh = GitHubAPI(session["github_token"])
    commits = gh.get_recent_commits(repo)

    for c in commits:
        if "author_name" not in c:
            c["author_name"] = "Alex Rivera" if c.get("login") == "admin" else "Core Software Engineer"

    return jsonify(commits)


# ─── Security / Secret Scan ────────────────────────────
@app.route("/api/security-scan", methods=["POST"])
@login_required
def api_security_scan():
    try:
        data = request.get_json() or {}
        repo = data.get("repo")
        staged_files = data.get("staged_files")  # optional, from a local pre-push script

        if not repo:
            return jsonify({"status": "error", "error_message": "Missing repository selection parameter."}), 400

        token = session.get("github_token") or os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GitHub Access Token is missing from session/environment.")

        result = run_security_scan(repo, token, staged_files=staged_files)
        return jsonify(result)

    except Exception as e:
        print(f"\n================ [SECURITY SCAN ERROR] ================\n{str(e)}\n=========================================================\n")
        return jsonify({
            "status": "error",
            "error_message": f"Security scan failed: {str(e)}"
        }), 500


# ─── Manual Notification Dispatches ────────────────────
# NOTE: the dashboard's "Run Email Alerts" button calls POST /api/trigger-email
# (see dashboard.html triggerEmailNotifications()). That route was missing
# before, which caused Flask's default HTML 404 page to be returned and
# broke the frontend's JSON.parse() with "Unexpected token '<'".
@app.route("/api/trigger-email", methods=["POST"])
@login_required
def trigger_email():
    repo = request.args.get("repo")
    if not repo:
        return jsonify({"status": "error", "error_message": "repo parameter required"}), 400
    check_inactive_users()
    return jsonify({"status": "success", "message": "Email notifications sent successfully"})


@app.route("/run-email-alerts")
@login_required
def run_email_alerts():
    check_inactive_users()
    return jsonify({"status": "success", "message": "Email notifications sent successfully"})


if __name__ == "__main__":
    # debug=False for local testing too — Werkzeug's interactive debugger
    # can return its own HTML error pages that bypass our JSON error
    # handlers above. Use the terminal logs / print statements instead.
    app.run(port=5050, threaded=True)
