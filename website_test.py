"""
Dedicated entry point for website screenshot test cases.

This runner loads test cases from modules under test_cases/ and supports both:
- Full-page screenshot checks
- Element-level checks (e.g., footer image/logo by CSS selector)
"""

import argparse

from log_utils import log_info, log_section
from search import run_website_search_pipeline
from test_cases.create_ticket_testcases import (
    get_test_case as get_create_ticket_test_case,
    list_test_cases as list_create_ticket_test_cases,
)
from test_cases.it4u_home_testcases import (
    get_test_case as get_it4u_home_test_case,
    list_test_cases as list_it4u_home_test_cases,
)
from test_cases.security_incident_page_testcases import (
    get_test_case as get_security_incident_page_test_case,
    list_test_cases as list_security_incident_page_test_cases,
)


def list_test_cases():
    """Return all website test cases across modules."""
    return [
        *list_it4u_home_test_cases(),
        *list_create_ticket_test_cases(),
        *list_security_incident_page_test_cases(),
    ]


def get_test_case(name: str):
    """Fetch a test case by name across all configured modules."""
    available = []
    for getter, lister in (
        (get_it4u_home_test_case, list_it4u_home_test_cases),
        (get_create_ticket_test_case, list_create_ticket_test_cases),
        (get_security_incident_page_test_case, list_security_incident_page_test_cases),
    ):
        available.extend(case.name for case in lister())
        try:
            return getter(name)
        except ValueError:
            continue

    listed = ", ".join(sorted(set(available)))
    raise ValueError(f"Unknown test case '{name}'. Available: {listed}")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for website test-case execution."""
    parser = argparse.ArgumentParser(
        description="Run website screenshot test cases and compare with image database"
    )
    parser.add_argument(
        "--list-test-cases",
        action="store_true",
        help="List available test case names and exit",
    )
    parser.add_argument(
        "--test-case",
        default=None,
        help="Optional single test case name from test_cases modules",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Override URL from selected test case",
    )
    parser.add_argument(
        "--screenshot-path",
        default=None,
        help="Override screenshot path from selected test case",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=None,
        help="Override wait time from selected test case",
    )
    parser.add_argument(
        "--css-selector",
        default=None,
        help="Override CSS selector from selected test case (element-only capture)",
    )
    parser.add_argument(
        "--xpath-selector",
        default=None,
        help="Override XPath selector from selected test case (element-only capture)",
    )
    parser.add_argument(
        "--click-xpath-selector",
        default=None,
        help="Override click XPath from selected test case (click and capture opened window)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser with visible window (default is headless)",
    )
    parser.add_argument("--index-folder", default="index", help="Index folder path")
    parser.add_argument(
        "--source-folder",
        default="image_database/stored_image",
        help="Image database folder",
    )
    parser.add_argument("--limit", type=int, default=10, help="Number of results to return")
    parser.add_argument(
        "--filter-size",
        type=int,
        default=100,
        help="Stage-1 candidate count",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=70.0,
        help="Threshold for positive/negative result",
    )
    return parser.parse_args()


def _print_test_cases() -> None:
    """Log available website test-case definitions."""
    log_section("AVAILABLE WEBSITE TEST CASES")
    for test_case in list_test_cases():
        if test_case.xpath_selector:
            selector_text = f"xpath: {test_case.xpath_selector}"
        elif getattr(test_case, "click_xpath_selector", None):
            selector_text = f"click xpath + new window: {test_case.click_xpath_selector}"
        elif test_case.css_selector:
            selector_text = f"css: {test_case.css_selector}"
        else:
            selector_text = "<full page>"
        log_info(f"- {test_case.name}: {test_case.description}")
        log_info(f"  URL: {test_case.url}")
        log_info(f"  Capture: {selector_text}")
        if getattr(test_case, "required_xpaths", None):
            log_info(f"  Required xpaths: {len(test_case.required_xpaths)}")


def main() -> None:
    """Run one test case or all configured test cases."""
    args = parse_args()

    if args.list_test_cases:
        _print_test_cases()
        return

    if args.test_case:
        cases_to_run = [get_test_case(args.test_case)]
    else:
        cases_to_run = list_test_cases()
        log_section("RUNNING ALL WEBSITE TEST CASES")
        log_info(f"Total test cases: {len(cases_to_run)}")

    for selected_case in cases_to_run:
        target_url = args.url if args.url else selected_case.url
        screenshot_path = args.screenshot_path if args.screenshot_path else selected_case.screenshot_path
        wait_seconds = args.wait_seconds if args.wait_seconds is not None else selected_case.wait_seconds
        css_selector = args.css_selector if args.css_selector is not None else selected_case.css_selector
        xpath_selector = args.xpath_selector if args.xpath_selector is not None else selected_case.xpath_selector
        click_xpath_selector = (
            args.click_xpath_selector
            if args.click_xpath_selector is not None
            else getattr(selected_case, "click_xpath_selector", None)
        )
        click_opens_new_window = bool(getattr(selected_case, "click_opens_new_window", True))
        required_xpaths = list(getattr(selected_case, "required_xpaths", []))

        if sum(bool(value) for value in (css_selector, xpath_selector, click_xpath_selector)) > 1:
            raise ValueError(
                "Use only one selector mode: css_selector, xpath_selector, or click_xpath_selector"
            )

        log_section("RUNNING WEBSITE TEST CASE")
        log_info(f"Test case: {selected_case.name}")
        log_info(f"Description: {selected_case.description}")
        log_info(f"URL: {target_url}")
        if xpath_selector:
            capture_text = f"xpath: {xpath_selector}"
        elif click_xpath_selector:
            if click_opens_new_window:
                capture_text = f"click xpath + new window: {click_xpath_selector}"
            else:
                capture_text = f"click xpath + same window navigation: {click_xpath_selector}"
        elif css_selector:
            capture_text = f"css: {css_selector}"
        else:
            capture_text = "<full page>"
        log_info(f"Capture selector: {capture_text}")
        if required_xpaths:
            log_info(f"Required xpaths to validate: {len(required_xpaths)}")

        run_website_search_pipeline(
            index_folder=args.index_folder,
            limit=args.limit,
            filter_size=args.filter_size,
            source_folder=args.source_folder,
            similarity_threshold=args.similarity_threshold,
            url=target_url,
            screenshot_path=screenshot_path,
            wait_seconds=wait_seconds,
            headless=not args.headed,
            capture_selector=css_selector,
            capture_xpath=xpath_selector,
            capture_click_xpath_new_window=click_xpath_selector,
            click_opens_new_window=click_opens_new_window,
            required_xpaths=required_xpaths,
        )


if __name__ == "__main__":
    main()
