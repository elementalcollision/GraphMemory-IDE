"""
Codon CLI integration utilities for testing framework.
Provides robust Codon compilation and execution capabilities with proper error handling.
"""

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CodonTestResult:
    """Result of Codon CLI operation"""

    success: bool
    return_code: int
    stdout: str
    stderr: str
    execution_time: float
    command: List[str]


class CodonCLIRunner:
    """Robust Codon CLI runner with error handling and testing utilities"""

    def __init__(self, cli_path: Path, python_path: str):
        self.cli_path = cli_path
        self.python_path = python_path
        self.last_result: Optional[CodonTestResult] = None

    def run_codon(self, args: List[str], timeout: float = 30.0) -> CodonTestResult:
        """Run Codon CLI command and return result"""
        command = [str(self.cli_path)] + args
        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={
                    **os.environ,
                    "CODON_PYTHON": self.python_path,
                    "PYTHONNOUSERSITE": "True",
                },
            )

            execution_time = time.time() - start_time

            self.last_result = CodonTestResult(
                success=result.returncode == 0,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=execution_time,
                command=command,
            )

            return self.last_result

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            self.last_result = CodonTestResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                execution_time=execution_time,
                command=command,
            )
            return self.last_result

        except Exception as e:
            execution_time = time.time() - start_time
            self.last_result = CodonTestResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                command=command,
            )
            return self.last_result

    def compile_codon_file(
        self, source_file: Path, output_file: Optional[Path] = None
    ) -> CodonTestResult:
        """Compile a Codon source file"""
        args = ["build", str(source_file)]
        if output_file:
            args.extend(["-o", str(output_file)])
        return self.run_codon(args)

    def run_codon_file(self, source_file: Path, *args) -> CodonTestResult:
        """Run a Codon source file directly"""
        cmd_args = ["run", str(source_file)] + list(args)
        return self.run_codon(cmd_args)

    def check_codon_version(self) -> CodonTestResult:
        """Check Codon version"""
        return self.run_codon(["--version"])

    def assert_compilation_success(
        self, result: CodonTestResult, error_msg: str = "Codon compilation failed"
    ):
        """Assert that Codon compilation was successful"""
        assert result.success, f"{error_msg}: {result.stderr}"
        assert result.return_code == 0, f"{error_msg}: return code {result.return_code}"

    def assert_compilation_failure(
        self, result: CodonTestResult, expected_error: Optional[str] = None
    ):
        """Assert that Codon compilation failed as expected"""
        assert (
            not result.success
        ), f"Expected compilation to fail, but it succeeded: {result.stdout}"
        if expected_error:
            assert (
                expected_error in result.stderr
            ), f"Expected error '{expected_error}' not found in: {result.stderr}"


class CodonEnvironmentManager:
    """Manages Codon test environment setup and teardown"""

    def __init__(self, virtual_env_path: Path):
        self.virtual_env_path = virtual_env_path
        self.original_env = dict(os.environ)

    def setup_environment(self) -> Dict[str, str]:
        """Setup Codon test environment"""
        os.environ["CODON_PYTHON"] = str(self.virtual_env_path)
        os.environ["PYTHONNOUSERSITE"] = "True"

        return {"CODON_PYTHON": str(self.virtual_env_path), "PYTHONNOUSERSITE": "True"}

    def cleanup_environment(self):
        """Cleanup Codon test environment"""
        os.environ.clear()
        os.environ.update(self.original_env)

    def __enter__(self):
        """Context manager entry"""
        return self.setup_environment()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup_environment()


class CodonErrorHandler:
    """Handles Codon compilation and execution errors"""

    @staticmethod
    def parse_compilation_error(stderr: str) -> Dict[str, Any]:
        """Parse Codon compilation error output"""
        error_info = {
            "error_type": "unknown",
            "line_number": None,
            "column_number": None,
            "message": stderr.strip(),
            "file_path": None,
        }

        # Try to extract line and column information
        lines = stderr.split("\n")
        for line in lines:
            if ":" in line and any(char.isdigit() for char in line):
                parts = line.split(":")
                if len(parts) >= 3:
                    try:
                        error_info["file_path"] = parts[0].strip()
                        error_info["line_number"] = int(parts[1].strip())
                        error_info["column_number"] = int(parts[2].strip())
                        error_info["message"] = ":".join(parts[3:]).strip()
                        break
                    except (ValueError, IndexError):
                        continue

        return error_info

    @staticmethod
    def is_compilation_error(result: CodonTestResult) -> bool:
        """Check if result indicates a compilation error"""
        return not result.success and "error" in result.stderr.lower()

    @staticmethod
    def is_runtime_error(result: CodonTestResult) -> bool:
        """Check if result indicates a runtime error"""
        return not result.success and result.return_code != 0 and result.stderr


def create_codon_runner(cli_path: Path, python_path: str) -> CodonCLIRunner:
    """Factory function to create a Codon CLI runner"""
    return CodonCLIRunner(cli_path, python_path)


def create_environment_manager(virtual_env_path: Path) -> CodonEnvironmentManager:
    """Factory function to create a Codon environment manager"""
    return CodonEnvironmentManager(virtual_env_path)
