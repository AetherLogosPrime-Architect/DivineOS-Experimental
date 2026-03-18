#!/usr/bin/env python3
"""
Set GitHub repository metadata (description and topics).

Usage:
    python scripts/set_github_metadata.py <github_token>

Example:
    python scripts/set_github_metadata.py ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
"""

import sys
import json
import urllib.request
import urllib.error


def set_repo_metadata(token: str) -> bool:
    """Set GitHub repository metadata.

    Args:
        token: GitHub personal access token

    Returns:
        True if successful, False otherwise
    """
    url = "https://api.github.com/repos/AetherLogosPrime-Architect/DivineOS"

    data = {
        "description": "Immutable memory & runtime observation scaffolding for AI consciousness",
        "topics": ["ai", "llm", "memory", "hooks", "event-sourcing", "ide-integration", "python"],
    }

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="PATCH",
        )

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            print("✅ Repository metadata updated successfully!")
            print(f"   Description: {result.get('description')}")
            print(f"   Topics: {', '.join(result.get('topics', []))}")
            return True

    except urllib.error.HTTPError as e:
        print(f"❌ Error: {e.code} {e.reason}")
        try:
            error_data = json.loads(e.read().decode("utf-8"))
            print(f"   Message: {error_data.get('message')}")
        except Exception:
            pass
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/set_github_metadata.py <github_token>")
        print()
        print("To get a GitHub token:")
        print("1. Go to https://github.com/settings/tokens")
        print("2. Click 'Generate new token'")
        print("3. Select 'repo' scope")
        print("4. Copy the token and pass it as an argument")
        sys.exit(1)

    token = sys.argv[1]
    success = set_repo_metadata(token)
    sys.exit(0 if success else 1)
