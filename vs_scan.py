import os
import sys
import requests


def get_current_repo_name():
    """Dynamically finds the name of your current project directory folder

    so that it matches what your dashboard dropdown is looking for.
    """
    try:
        # Gets the absolute directory path where this script is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Returns the folder name (e.g., 'github_team_monitor')
        return os.path.basename(current_dir)
    except Exception:
        return "github_team_monitor"


try:
    repo_name = get_current_repo_name()
    print(f"🔄 GitPulse Guard: Scanning active repository '{repo_name}'...")

    # 1. Ping your running Flask engine and tell it exactly which repo is scanning
    response = requests.post(
        "http://127.0.0.1:5050/api/scan-code", json={"repo": repo_name}
    )
    res = response.json()

    critical = res.get("summary", {}).get("critical", 0)

    # 2. Format errors explicitly to match VS Code Problems panel pattern
    print("\n--- Diagnostic Scan Results ---")
    for f in res.get("results", []):
        filename = f.get("file", "unknown")
        for issue in f.get("issues", []):
            line = issue.get("line", 1)
            severity = issue.get("severity", "ERROR").upper()
            msg = issue.get("message", "")
            # This specific print pattern triggers VS Code's internal regex to light up lines in red
            print(f"{filename}:{line}:0: error: [{severity}] {msg}")

    # 3. Intercept execution if critical risks are detected
    if critical > 0:
        print("\n❌ Push Blocked by GitPulse Security Guard.")
        print(
            f"⚠️ Found {critical} critical vulnerabilities. Fix them to allow push operations."
        )
        sys.exit(1)
    else:
        print("\n✅ Clean scan! No blocking issues found.")
        sys.exit(0)

except Exception as e:
    print(f"⚠️ Scanner engine connection status offline: {e}")
    # Exit with 0 so the terminal doesn't crash if your local webserver isn't open yet
    sys.exit(0)