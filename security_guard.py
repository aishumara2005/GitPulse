import os
import sys
import subprocess
import requests


def get_current_repo_name():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.basename(current_dir)
    except Exception:
        return "github_team_monitor"


def get_staged_files_with_content():
    """
    Local check: files staged/committed but not yet pushed.
    Mirrors the 'Before Push' detection — runs entirely on this machine,
    nothing is sent anywhere except filenames+content to your own local
    Flask server below.
    """
    try:
        try:
            remote_ref = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            diff_range = f"{remote_ref}..HEAD"
        except subprocess.CalledProcessError:
            diff_range = "HEAD"

        output = subprocess.check_output(["git", "diff", "--name-only", diff_range]).decode().strip()
        filenames = [f for f in output.splitlines() if f]

        staged = []
        for filename in filenames:
            try:
                content = subprocess.check_output(
                    ["git", "show", f"HEAD:{filename}"], stderr=subprocess.DEVNULL
                ).decode(errors="ignore")
            except subprocess.CalledProcessError:
                content = ""
            staged.append({"filename": filename, "content": content})
        return staged
    except Exception:
        return []


try:
    repo_name = get_current_repo_name()
    print(f"🔄 GitPulse Security Guard: Scanning '{repo_name}' for exposed secrets...")

    staged_files = get_staged_files_with_content()

    response = requests.post(
        "http://127.0.0.1:5050/api/security-scan",
        json={"repo": repo_name, "staged_files": staged_files},
    )
    res = response.json()

    if res.get("status") == "error":
        print(f"⚠️ Security scan error: {res.get('error_message')}")
        sys.exit(0)  # don't block push if the scanner itself failed to run

    recommendations = res.get("recommendations", [])

    if not recommendations:
        print("✅ No sensitive environment files detected.")
        sys.exit(0)

    print("\n--- Security Scan Results ---")
    blocking = False
    for rec in recommendations:
        print(f"\nRisk Level: {rec['risk_level']}")
        print(f"File: {rec['file']}")
        print(f"Reason: {rec['reason']}")
        print(f"Recommended Action: {rec['recommended_action']}")
        print(f"Status: {rec['status']}")
        print(rec["message"])
        if rec["status"] == "Before Push":
            blocking = True

    if blocking:
        print("\n❌ Push Blocked by GitPulse Security Guard.")
        print("Fix the sensitive file(s) above before pushing.")
        sys.exit(1)
    else:
        print("\n⚠️ Sensitive file(s) already on GitHub — see 'Already Pushed' items above.")
        print("Push not blocked locally, but please remediate immediately.")
        sys.exit(0)

except Exception as e:
    print(f"⚠️ Scanner engine connection status offline: {e}")
    print("💡 Please make sure your Flask app (app.py) is running on port 5050.")
    sys.exit(0)
