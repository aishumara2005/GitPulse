import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict

GITHUB_API = "https://api.github.com"

class GitHubAPI:
    def __init__(self, token: str):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get(self, path: str, params: dict = None):
        r = requests.get(f"{GITHUB_API}{path}", headers=self.headers, params=params)
        r.raise_for_status()
        return r.json()

    def get_user_repos(self):
        """List repos the authenticated user has access to"""
        repos = []
        page = 1
        while True:
            batch = self._get("/user/repos", {"per_page": 100, "page": page, "sort": "updated"})
            if not batch:
                break
            repos.extend([
                {
                    "full_name": r["full_name"],
                    "name": r["name"],
                    "description": r.get("description"),
                    "private": r["private"],
                    "updated_at": r["updated_at"],
                    "language": r.get("language"),
                    "stargazers_count": r["stargazers_count"],
                    "open_issues_count": r["open_issues_count"],
                }
                for r in batch
            ])
            if len(batch) < 100:
                break
            page += 1
        return repos

    def get_team_activity(self, repo: str):
        """Get per-member commit/PR/issue activity for last 30 days"""
        since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        # ── Commits ──────────────────────────────────────────────────────────
        commits = []
        try:
            commits = self._get(f"/repos/{repo}/commits", {"since": since, "per_page": 100})
        except Exception:
            pass

        member_stats = defaultdict(lambda: {
            "commits": 0, "prs_opened": 0, "issues_opened": 0,
            "last_commit": None, "avatar": None, "profile": None,
            "commit_dates": [],
        })

        for c in commits:
            author = c.get("author")
            if not author:
                continue
            login = author.get("login", "unknown")
            member_stats[login]["commits"] += 1
            member_stats[login]["avatar"] = author.get("avatar_url")
            member_stats[login]["profile"] = author.get("html_url")
            date = c["commit"]["author"]["date"]
            member_stats[login]["commit_dates"].append(date)
            if not member_stats[login]["last_commit"] or date > member_stats[login]["last_commit"]:
                member_stats[login]["last_commit"] = date

        # ── Pull Requests ─────────────────────────────────────────────────────
        try:
            prs = self._get(f"/repos/{repo}/pulls", {"state": "all", "per_page": 100})
            for pr in prs:
                if pr["created_at"] >= since:
                    login = pr["user"]["login"]
                    member_stats[login]["prs_opened"] += 1
        except Exception:
            pass

        # ── Issues ────────────────────────────────────────────────────────────
        try:
            issues = self._get(
                f"/repos/{repo}/issues",
                {"state": "all", "since": since, "per_page": 100}
            )
            for issue in issues:
                if "pull_request" not in issue:
                    login = issue["user"]["login"]
                    member_stats[login]["issues_opened"] += 1
        except Exception:
            pass

        # ── Collaborators ─────────────────────────────────────────────────────
        try:
            collabs = self._get(f"/repos/{repo}/collaborators", {"per_page": 100})
            for c in collabs:
                login = c["login"]
                if login not in member_stats:
                    member_stats[login] = {
                        "commits": 0, "prs_opened": 0, "issues_opened": 0,
                        "last_commit": None, "commit_dates": [],
                        "avatar": c.get("avatar_url"),
                        "profile": c.get("html_url"),
                    }
                else:
                    member_stats[login]["avatar"] = member_stats[login].get("avatar") or c.get("avatar_url")
        except Exception:
            pass

        return {
            "repo": repo,
            "since": since,
            "members": dict(member_stats),
        }

    def get_recent_commits(self, repo: str, per_page: int = 20):
        try:
            commits = self._get(f"/repos/{repo}/commits", {"per_page": per_page})
            return [
                {
                    "sha": c["sha"][:7],
                    "message": c["commit"]["message"].split("\n")[0][:80],
                    "author": c["commit"]["author"]["name"],
                    "login": c["author"]["login"] if c.get("author") else "unknown",
                    "date": c["commit"]["author"]["date"],
                    "url": c["html_url"],
                }
                for c in commits
            ]
        except Exception:
            return []

    def get_file_content(self, repo: str, path: str):
        import base64
        try:
            data = self._get(f"/repos/{repo}/contents/{path}")
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        except Exception:
            pass
        return None

    def get_repo_tree(self, repo: str):
        """Get flat file tree of default branch"""
        try:
            repo_info = self._get(f"/repos/{repo}")
            branch = repo_info.get("default_branch", "main")
            tree = self._get(f"/repos/{repo}/git/trees/{branch}?recursive=1")
            return [
                item["path"]
                for item in tree.get("tree", [])
                if item["type"] == "blob"
            ]
        except Exception:
            return []
