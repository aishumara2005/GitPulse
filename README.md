# ⚡ GitPulse — GitHub Team Intelligence Platform

A **Flask-based** web app to monitor GitHub team activity, get AI-powered suggestions, and scan code for errors — with a sleek dark glassmorphism UI.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 **Access Control** | GitHub OAuth + username whitelist (no unauthorized access) |
| 👥 **Team Activity** | Per-member commits, PRs, issues, last active date |
| 🤖 **AI Suggestions** | Claude-powered coaching for inactive/low-activity members |
| 🔍 **Code Scanner** | Detects secrets, SQL injection, eval, bare excepts, debug prints & more |
| 📝 **Commit History** | Recent commit timeline with author info |

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Set up GitHub OAuth App
1. Go to https://github.com/settings/developers → "New OAuth App"
2. **Homepage URL:** `http://localhost:5050`
3. **Callback URL:** `http://localhost:5050/auth/callback`
4. Copy **Client ID** and **Client Secret** to `.env`

### 4. Run the app
```bash
python app.py
```
Open http://localhost:5050

---

## 🔐 Access Control

In `.env`, set:
```
ALLOWED_GITHUB_USERS=alice,bob,charlie
```
- Only listed GitHub usernames can log in
- Leave **empty** to allow all GitHub users
- Anyone not on the list sees a 403 page

### Dev Mode (no OAuth setup needed)
Use a **Personal Access Token** directly on the login page:
1. Generate at https://github.com/settings/tokens
2. Scopes needed: `repo`, `read:org`
3. Paste on the login screen → "Sign in with Token"

---

## 🤖 AI Suggestions

Set your Anthropic API key in `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```
If not set, falls back to rule-based suggestions (still works!).

---

## 📁 Project Structure

```
github_team_monitor/
├── app.py                  # Flask app + routes
├── requirements.txt
├── .env.example
├── config/
│   └── settings.py         # Environment config
├── utils/
│   ├── github_api.py       # GitHub REST API wrapper
│   ├── ai_analyzer.py      # Claude AI suggestions
│   └── code_scanner.py     # Regex-based code scanner
└── templates/
    ├── base.html           # Design system & layout
    ├── login.html          # Login / OAuth page
    ├── dashboard.html      # Main dashboard (4 tabs)
    └── unauthorized.html   # 403 page
```

---

## 🔍 Code Scanner Rules

| Rule | Severity | What it catches |
|---|---|---|
| `HARDCODED_SECRET` | 🔴 Critical | Passwords/keys in code |
| `SQL_INJECTION` | 🔴 High | String-formatted SQL queries |
| `EVAL_USAGE` | 🔴 High | `eval()` calls |
| `SHELL_INJECTION` | 🔴 High | `os.system`, `subprocess` |
| `BARE_EXCEPT` | 🟡 Medium | `except:` without type |
| `MUTABLE_DEFAULT` | 🟡 Medium | `def f(x=[])` pattern |
| `DANGEROUSLYSETHTML` | 🔴 High | React XSS risk |
| `CONSOLE_LOG` | 🔵 Low | Debug console.log |
| `PRINT_DEBUG` | 🔵 Low | Debug print() |
| `TODO_FIXME` | ⚪ Info | Technical debt comments |

Scans: `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.java`, `.go`, `.rb`
