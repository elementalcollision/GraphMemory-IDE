#!/usr/bin/env python3
"""
Compatibility Summary Generator

This script generates comprehensive compatibility test summaries
for API compatibility testing framework results.
"""

import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def parse_compatibility_results(xml_files: list) -> Dict[str, Any]:
    """Parse compatibility test results and generate summary"""

    summary = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "skipped_tests": 0,
        "compatibility_score": 0.0,
        "api_contract_score": 0.0,
        "behavioral_parity_score": 0.0,
        "dynamic_feature_score": 0.0,
        "test_suites": {},
        "failures": [],
        "warnings": [],
        "performance_regressions": [],
    }

    for xml_file in xml_files:
        if not Path(xml_file).exists():
            print(f"Warning: XML file {xml_file} does not exist", file=sys.stderr)
            continue

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            suite_name = Path(xml_file).stem
            suite_tests = 0
            suite_failures = 0
            suite_errors = 0
            suite_skipped = 0
            suite_time = 0.0

            for testsuite in root.findall("testsuite"):
                suite_tests += int(testsuite.get("tests", 0))
                suite_failures += int(testsuite.get("failures", 0))
                suite_errors += int(testsuite.get("errors", 0))
                suite_skipped += int(testsuite.get("skipped", 0))
                suite_time += float(testsuite.get("time", 0.0))

                # Process test cases for detailed analysis
                for testcase in testsuite.findall("testcase"):
                    test_name = testcase.get("name", "unknown")
                    test_class = testcase.get("classname", "unknown")

                    # Check for failures
                    failure = testcase.find("failure")
                    if failure is not None:
                        failure_info = {
                            "test_name": test_name,
                            "test_class": test_class,
                            "suite": suite_name,
                            "message": failure.get("message", ""),
                            "type": failure.get("type", ""),
                            "details": failure.text or "",
                        }
                        summary["failures"].append(failure_info)

            summary["total_tests"] += suite_tests
            summary["failed_tests"] += suite_failures + suite_errors
            summary["skipped_tests"] += suite_skipped

            # Store suite summary
            summary["test_suites"][suite_name] = {
                "total": suite_tests,
                "failures": suite_failures,
                "errors": suite_errors,
                "skipped": suite_skipped,
                "time": suite_time,
            }

        except Exception as e:
            print(f"Error parsing {xml_file}: {e}", file=sys.stderr)

    # Calculate passed tests
    summary["passed_tests"] = (
        summary["total_tests"] - summary["failed_tests"] - summary["skipped_tests"]
    )

    # Calculate scores
    if summary["total_tests"] > 0:
        summary["compatibility_score"] = (
            summary["passed_tests"] / summary["total_tests"]
        )

        # Calculate specific scores based on test suite results
        api_contract_tests = summary["test_suites"].get("compatibility", {})
        behavioral_tests = summary["test_suites"].get("behavioral-parity", {})
        dynamic_tests = summary["test_suites"].get("dynamic-feature", {})

        if api_contract_tests.get("total", 0) > 0:
            summary["api_contract_score"] = (
                api_contract_tests["total"]
                - api_contract_tests["failures"]
                - api_contract_tests["errors"]
            ) / api_contract_tests["total"]

        if behavioral_tests.get("total", 0) > 0:
            summary["behavioral_parity_score"] = (
                behavioral_tests["total"]
                - behavioral_tests["failures"]
                - behavioral_tests["errors"]
            ) / behavioral_tests["total"]

        if dynamic_tests.get("total", 0) > 0:
            summary["dynamic_feature_score"] = (
                dynamic_tests["total"]
                - dynamic_tests["failures"]
                - dynamic_tests["errors"]
            ) / dynamic_tests["total"]

    return summary


def generate_compatibility_report(xml_files: list, output_file: str):
    """Generate a comprehensive compatibility test report"""

    summary = parse_compatibility_results(xml_files)

    # Add metadata
    summary["generated_at"] = datetime.now().isoformat()
    summary["xml_sources"] = xml_files

    # Add analysis
    summary["analysis"] = {
        "overall_status": "PASS" if summary["compatibility_score"] >= 0.95 else "FAIL",
        "api_contract_status": (
            "PASS" if summary["api_contract_score"] >= 0.95 else "FAIL"
        ),
        "behavioral_parity_status": (
            "PASS" if summary["behavioral_parity_score"] >= 0.98 else "FAIL"
        ),
        "dynamic_feature_status": (
            "PASS" if summary["dynamic_feature_score"] >= 0.90 else "FAIL"
        ),
    }

    # Write summary to JSON file
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Compatibility summary generated: {output_file}")
    print(f"Total tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed_tests']}")
    print(f"Failed: {summary['failed_tests']}")
    print(f"Skipped: {summary['skipped_tests']}")
    print(f"Overall compatibility score: {summary['compatibility_score']:.2%}")
    print(f"API contract score: {summary['api_contract_score']:.2%}")
    print(f"Behavioral parity score: {summary['behavioral_parity_score']:.2%}")
    print(f"Dynamic feature score: {summary['dynamic_feature_score']:.2%}")
    print(f"Overall status: {summary['analysis']['overall_status']}")


def main():
    """Main function"""
    if len(sys.argv) < 3:
        print(
            "Usage: python generate_compatibility_summary.py <xml_file1> <xml_file2> ... <output_file>"
        )
        sys.exit(1)

    xml_files = sys.argv[1:-1]
    output_file = sys.argv[-1]

    generate_compatibility_report(xml_files, output_file)


if __name__ == "__main__":
    main()
