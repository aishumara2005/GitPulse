import os
import json
import requests
from datetime import datetime, timezone, timedelta
from config.settings import Config

CLAUDE_API = "https://api.anthropic.com/v1/messages"

class AIAnalyzer:
    def __init__(self):
        self.api_key = Config.ANTHROPIC_API_KEY

    def _call_claude(self, prompt: str) -> str:
        if not self.api_key:
            return self._local_analysis_fallback(prompt)
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            r = requests.post(CLAUDE_API, headers=headers, json=body, timeout=30)
            r.raise_for_status()
            data = r.json()
            return data["content"][0]["text"]
        except Exception as e:
            return f"AI analysis unavailable: {str(e)}"

    def generate_suggestions(self, activity_data: dict) -> list[dict]:
        members = activity_data.get("members", {})
        since = activity_data.get("since", "")
        repo = activity_data.get("repo", "")
        now = datetime.now(timezone.utc)

        # Build summary for AI
        summary_lines = []
        for login, stats in members.items():
            last = stats.get("last_commit")
            days_since = "Never committed"
            if last:
                try:
                    dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                    diff = (now - dt).days
                    days_since = f"{diff} days ago"
                except Exception:
                    days_since = last
            summary_lines.append(
                f"- {login}: {stats['commits']} commits, "
                f"{stats['prs_opened']} PRs, "
                f"{stats['issues_opened']} issues, "
                f"last commit: {days_since}"
            )

        summary = "\n".join(summary_lines)
        prompt = f"""You are a GitHub team productivity coach. Analyze this team activity for repo '{repo}' (last 30 days):

{summary}

For each member, give a short, constructive, friendly suggestion in JSON format. Consider:
- Inactive members (0 commits in 30 days) → motivate them
- Low PR participation → suggest code review
- High commits but no PRs → suggest PR workflow
- Good performers → praise and suggest stretch goals

Return ONLY a JSON array, no markdown:
[
  {{
    "member": "username",
    "status": "active|moderate|inactive",
    "suggestion": "Your 1-2 sentence suggestion here",
    "priority": "high|medium|low"
  }}
]"""

        raw = self._call_claude(prompt)
        
        # Parse response
        try:
            # Strip any markdown fences if present
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            return json.loads(clean.strip())
        except Exception:
            # Fallback: rule-based suggestions
            return self._rule_based_suggestions(members, now)

    def _rule_based_suggestions(self, members: dict, now: datetime) -> list[dict]:
        suggestions = []
        for login, stats in members.items():
            commits = stats.get("commits", 0)
            prs = stats.get("prs_opened", 0)
            last = stats.get("last_commit")
            
            days_since = 999
            if last:
                try:
                    dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                    days_since = (now - dt).days
                except Exception:
                    pass

            if commits == 0 or days_since > 14:
                status = "inactive"
                priority = "high"
                suggestion = (
                    f"@{login} hasn't committed in {days_since} days. "
                    "Reach out to check if they need help or are blocked."
                )
            elif commits < 3:
                status = "moderate"
                priority = "medium"
                suggestion = (
                    f"@{login} has low activity ({commits} commits). "
                    "Consider assigning more tasks or pairing with an active member."
                )
            elif prs == 0 and commits > 5:
                status = "active"
                priority = "medium"
                suggestion = (
                    f"@{login} commits a lot but hasn't opened PRs. "
                    "Encourage using pull requests for better code review."
                )
            else:
                status = "active"
                priority = "low"
                suggestion = (
                    f"@{login} is doing great! "
                    "Consider mentoring less active team members."
                )

            suggestions.append({
                "member": login,
                "status": status,
                "suggestion": suggestion,
                "priority": priority,
            })
        return suggestions

    def _local_analysis_fallback(self, prompt: str) -> str:
        return "[]"
