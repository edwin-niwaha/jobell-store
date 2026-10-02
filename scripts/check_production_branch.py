"""Reject production releases without a verified main GitHub branch."""

import os
import sys


def main():
    branch = os.environ.get("RAILWAY_GIT_BRANCH", "").strip()
    if branch != "main":
        print(
            f"Production deployment blocked: expected branch 'main', got {branch or 'unknown'!r}. "
            "Merge changes into main and deploy through the GitHub integration.",
            file=sys.stderr,
        )
        return 1
    print("Production branch verified: main.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
