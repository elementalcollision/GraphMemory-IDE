#!/usr/bin/env python3
"""
Test Summary Generator

This script generates comprehensive test summaries from pytest XML results
for integration with CI/CD pipelines.
"""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def parse_xml_results(xml_file: str) -> Dict[str, Any]:
    """Parse pytest XML results and extract summary information"""

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        summary = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "error_tests": 0,
            "test_duration": 0.0,
            "test_suites": [],
            "failures": [],
            "errors": [],
            "skipped": [],
        }

        for testsuite in root.findall("testsuite"):
            suite_name = testsuite.get("name", "unknown")
            suite_tests = int(testsuite.get("tests", 0))
            suite_failures = int(testsuite.get("failures", 0))
            suite_errors = int(testsuite.get("errors", 0))
            suite_skipped = int(testsuite.get("skipped", 0))
            suite_time = float(testsuite.get("time", 0.0))

            summary["total_tests"] += suite_tests
            summary["failed_tests"] += suite_failures
            summary["error_tests"] += suite_errors
            summary["skipped_tests"] += suite_skipped
            summary["test_duration"] += suite_time

            suite_summary = {
                "name": suite_name,
                "total": suite_tests,
                "failures": suite_failures,
                "errors": suite_errors,
                "skipped": suite_skipped,
                "time": suite_time,
            }
            summary["test_suites"].append(suite_summary)

            # Process individual test cases
            for testcase in testsuite.findall("testcase"):
                test_name = testcase.get("name", "unknown")
                test_class = testcase.get("classname", "unknown")
                test_time = float(testcase.get("time", 0.0))

                # Check for failures
                failure = testcase.find("failure")
                if failure is not None:
                    failure_info = {
                        "test_name": test_name,
                        "test_class": test_class,
                        "message": failure.get("message", ""),
                        "type": failure.get("type", ""),
                        "details": failure.text or "",
                    }
                    summary["failures"].append(failure_info)

                # Check for errors
                error = testcase.find("error")
                if error is not None:
                    error_info = {
                        "test_name": test_name,
                        "test_class": test_class,
                        "message": error.get("message", ""),
                        "type": error.get("type", ""),
                        "details": error.text or "",
                    }
                    summary["errors"].append(error_info)

                # Check for skipped tests
                skipped = testcase.find("skipped")
                if skipped is not None:
                    skipped_info = {
                        "test_name": test_name,
                        "test_class": test_class,
                        "message": skipped.get("message", ""),
                        "details": skipped.text or "",
                    }
                    summary["skipped"].append(skipped_info)

        # Calculate passed tests
        summary["passed_tests"] = (
            summary["total_tests"]
            - summary["failed_tests"]
            - summary["error_tests"]
            - summary["skipped_tests"]
        )

        # Calculate success rate
        if summary["total_tests"] > 0:
            summary["success_rate"] = summary["passed_tests"] / summary["total_tests"]
        else:
            summary["success_rate"] = 0.0

        return summary

    except Exception as e:
        print(f"Error parsing XML file {xml_file}: {e}", file=sys.stderr)
        return {
            "error": f"Failed to parse {xml_file}: {str(e)}",
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "error_tests": 0,
            "test_duration": 0.0,
            "success_rate": 0.0,
            "test_suites": [],
            "failures": [],
            "errors": [],
            "skipped": [],
        }


def generate_summary_report(xml_file: str, output_file: str):
    """Generate a comprehensive test summary report"""

    summary = parse_xml_results(xml_file)

    # Add metadata
    summary["generated_at"] = datetime.now().isoformat()
    summary["xml_source"] = xml_file

    # Write summary to JSON file
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Test summary generated: {output_file}")
    print(f"Total tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed_tests']}")
    print(f"Failed: {summary['failed_tests']}")
    print(f"Errors: {summary['error_tests']}")
    print(f"Skipped: {summary['skipped_tests']}")
    print(f"Success rate: {summary['success_rate']:.2%}")
    print(f"Duration: {summary['test_duration']:.2f}s")


def main():
    """Main function"""
    if len(sys.argv) != 3:
        print("Usage: python generate_test_summary.py <xml_file> <output_file>")
        sys.exit(1)

    xml_file = sys.argv[1]
    output_file = sys.argv[2]

    if not Path(xml_file).exists():
        print(f"Error: XML file {xml_file} does not exist", file=sys.stderr)
        sys.exit(1)

    generate_summary_report(xml_file, output_file)


if __name__ == "__main__":
    main()
