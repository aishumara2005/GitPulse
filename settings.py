import os
import secrets

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))

    # GitHub OAuth App credentials
    GITHUB_CLIENT_ID     = os.environ.get("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
    OAUTH_STATE          = os.environ.get("OAUTH_STATE", secrets.token_hex(16))

    # Whitelist: comma-separated GitHub usernames
    # e.g. ALLOWED_GITHUB_USERS=alice,bob,charlie
    # Leave blank to allow ALL authenticated users
    _raw_allowed = os.environ.get("ALLOWED_GITHUB_USERS", "")
    ALLOWED_GITHUB_USERS = (
        [u.strip() for u in _raw_allowed.split(",") if u.strip()]
        if _raw_allowed else []
    )

    # Anthropic API key for AI suggestions
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
