#!/usr/bin/env python3
"""
Repository Security Verification Script

This script verifies that the repository doesn't contain sensitive information
that should not be committed to git.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


class SecurityVerifier:
    def __init__(self):
        self.repo_root = Path.cwd()
        self.sensitive_patterns = [
            r'password\s*[:=]\s*["\'][^"\']+["\']',
            r'secret\s*[:=]\s*["\'][^"\']+["\']',
            r'token\s*[:=]\s*["\'][^"\']+["\']',
            r'key\s*[:=]\s*["\'][^"\']+["\']',
            r'api_key\s*[:=]\s*["\'][^"\']+["\']',
            r'private_key\s*[:=]\s*["\'][^"\']+["\']',
            r'jwt_secret\s*[:=]\s*["\'][^"\']+["\']',
            r'database_url\s*[:=]\s*["\'][^"\']+["\']',
            r'redis_url\s*[:=]\s*["\'][^"\']+["\']',
        ]

        self.sensitive_files = [
            "config/development_secrets.json",
            "config/production_secrets.json",
            "config/staging_secrets.json",
            "config/testing_secrets.json",
            "kubernetes/manifests/configmaps-secrets.yaml",
        ]

        self.ignored_extensions = {".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe"}
        self.ignored_dirs = {".git", "node_modules", "codon-dev-env", "__pycache__"}

    def check_git_tracking(self) -> List[str]:
        """Check if sensitive files are being tracked by git."""
        issues = []

        try:
            result = subprocess.run(
                ["git", "ls-files"], capture_output=True, text=True, cwd=self.repo_root
            )

            if result.returncode != 0:
                issues.append(f"Failed to get git files: {result.stderr}")
                return issues

            tracked_files = result.stdout.strip().split("\n")

            for sensitive_file in self.sensitive_files:
                if sensitive_file in tracked_files:
                    issues.append(f"CRITICAL: {sensitive_file} is tracked by git!")

        except Exception as e:
            issues.append(f"Error checking git tracking: {e}")

        return issues

    def check_git_ignore(self) -> List[str]:
        """Verify that sensitive files are properly ignored."""
        issues = []

        try:
            for sensitive_file in self.sensitive_files:
                result = subprocess.run(
                    ["git", "check-ignore", sensitive_file],
                    capture_output=True,
                    text=True,
                    cwd=self.repo_root,
                )

                if result.returncode != 0:
                    issues.append(f"WARNING: {sensitive_file} is not ignored by git")

        except Exception as e:
            issues.append(f"Error checking git ignore: {e}")

        return issues

    def scan_for_sensitive_content(self) -> List[str]:
        """Scan tracked files for sensitive content patterns."""
        issues = []

        try:
            result = subprocess.run(
                ["git", "ls-files"], capture_output=True, text=True, cwd=self.repo_root
            )

            if result.returncode != 0:
                issues.append(f"Failed to get git files: {result.stderr}")
                return issues

            tracked_files = result.stdout.strip().split("\n")

            for file_path in tracked_files:
                if not file_path or self._should_skip_file(file_path):
                    continue

                full_path = self.repo_root / file_path
                if not full_path.exists():
                    continue

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    for pattern in self.sensitive_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            issues.append(
                                f"POTENTIAL SENSITIVE CONTENT: {file_path} contains pattern '{pattern}'"
                            )
                            break

                except Exception as e:
                    issues.append(f"Error reading {file_path}: {e}")

        except Exception as e:
            issues.append(f"Error scanning for sensitive content: {e}")

        return issues

    def _should_skip_file(self, file_path: str) -> bool:
        """Determine if a file should be skipped during scanning."""
        path = Path(file_path)

        # Skip binary files and certain extensions
        if path.suffix in self.ignored_extensions:
            return True

        # Skip ignored directories
        for part in path.parts:
            if part in self.ignored_dirs:
                return True

        # Skip template files (they're supposed to contain placeholders)
        if file_path.endswith(".template"):
            return True

        return False

    def check_environment_files(self) -> List[str]:
        """Check for environment files that shouldn't be tracked."""
        issues = []

        env_files = [
            ".env",
            ".env.local",
            ".env.development",
            ".env.production",
            ".env.staging",
            ".env.testing",
        ]

        for env_file in env_files:
            if (self.repo_root / env_file).exists():
                issues.append(
                    f"ENVIRONMENT FILE FOUND: {env_file} exists in repository"
                )

        return issues

    def run_all_checks(self) -> Tuple[bool, List[str]]:
        """Run all security checks and return results."""
        all_issues = []

        print("🔍 Running repository security verification...")
        print()

        # Check git tracking
        print("1. Checking git tracking...")
        issues = self.check_git_tracking()
        if issues:
            all_issues.extend(issues)
            print("   ❌ Issues found")
        else:
            print("   ✅ No sensitive files tracked by git")

        # Check git ignore
        print("2. Checking git ignore...")
        issues = self.check_git_ignore()
        if issues:
            all_issues.extend(issues)
            print("   ❌ Issues found")
        else:
            print("   ✅ Sensitive files properly ignored")

        # Check for sensitive content
        print("3. Scanning for sensitive content...")
        issues = self.scan_for_sensitive_content()
        if issues:
            all_issues.extend(issues)
            print("   ❌ Issues found")
        else:
            print("   ✅ No sensitive content patterns found")

        # Check environment files
        print("4. Checking environment files...")
        issues = self.check_environment_files()
        if issues:
            all_issues.extend(issues)
            print("   ❌ Issues found")
        else:
            print("   ✅ No environment files found")

        print()

        if all_issues:
            print("🚨 SECURITY ISSUES FOUND:")
            print("=" * 50)
            for issue in all_issues:
                print(f"• {issue}")
            print("=" * 50)
            return False, all_issues
        else:
            print("✅ REPOSITORY SECURITY VERIFICATION PASSED")
            print("All security checks completed successfully.")
            return True, []


def main():
    """Main function to run security verification."""
    verifier = SecurityVerifier()
    success, issues = verifier.run_all_checks()

    if not success:
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("1. Remove any tracked sensitive files: git rm --cached <file>")
        print("2. Update .gitignore to exclude sensitive files")
        print("3. Use template files for configuration structure")
        print("4. Store actual secrets in environment variables")
        print("5. Review and fix any identified issues")
        sys.exit(1)
    else:
        print("\n🎉 Repository is ready for secure deployment!")
        sys.exit(0)


if __name__ == "__main__":
    main()
