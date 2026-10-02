import os
import subprocess
import sys
import unittest
from pathlib import Path


class ProductionBranchTests(unittest.TestCase):
    def test_only_main_can_deploy(self):
        guard = Path(__file__).with_name("check_production_branch.py")
        for branch in ("main", "dev", "feature/toasts", "", None):
            with self.subTest(branch=branch):
                environment = os.environ.copy()
                environment.pop("RAILWAY_GIT_BRANCH", None)
                if branch is not None:
                    environment["RAILWAY_GIT_BRANCH"] = branch
                result = subprocess.run(
                    [sys.executable, str(guard)], env=environment,
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 0 if branch == "main" else 1)


if __name__ == "__main__":
    unittest.main()
