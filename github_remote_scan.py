import sys
import requests

# 1. Flask scanner engine URL (Unga local port matching)
FLASK_SCAN_URL = "http://127.0.0.1:5050/api/scan-code"

# 2. Unga GitHub repository name-ai inga kudunga
# (Unga dashboard dropdown-la enna name kaatutho athe name exact-ah irukanum)
TARGET_REPO = "github_team_monitor" 

try:
    print(f"🔄 GitHub Remote Scan Started for: '{TARGET_REPO}'...")

    # Flask engine-ku target repo-vai API moolama anupugirom
    response = requests.post(
        FLASK_SCAN_URL, 
        json={"repo": TARGET_REPO}
    )
    
    # Auth session validation checking
    if response.status_code in [302, 401]:
        print("❌ Error: Authentication Required! Browser-la Flask dashboard-ai login panni vainga.")
        sys.exit(1)
        
    if response.status_code != 200:
        print(f"❌ Server Error: Status code {response.status_code}")
        sys.exit(1)

    res = response.json()
    critical = res.get("summary", {}).get("critical", 0)

    print("\n--- Diagnostic GitHub Scan Results ---")
    
    # 3. GitHub repository errors-ai loop panni parse seigirom
    scan_results = res.get("results", [])
    if not scan_results:
        print("✅ No issues found or repository is clean!")

    for f in scan_results:
        filename = f.get("file", "unknown")
        for issue in f.get("issues", []):
            line = issue.get("line", 1)
            severity = issue.get("severity", "ERROR").upper()
            msg = issue.get("message", "")
            
            # VS Code Problems panel-la red color-la highlight aaga intha specific pattern:
            print(f"{filename}:{line}:0: error: [{severity}] {msg}")

    # Push block check logic 
    if critical > 0:
        print(f"\n❌ Scan Blocked: Found {critical} critical errors on GitHub!")
        sys.exit(1)
    else:
        print("\n✅ Clean scan! Ready to push.")
        sys.exit(0)

except Exception as e:
    print(f"⚠️ Scanner Offline: {e}")
    print("💡 Please make sure your Flask app (app.py) is running on port 5050.")
    sys.exit(0)