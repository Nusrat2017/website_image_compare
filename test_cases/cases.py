"""Reusable website test-case configurations.

Add new cases here as your website test coverage grows.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WebsiteTestCase:
    """Configuration for one website screenshot comparison test."""

    name: str
    description: str
    url: str
    screenshot_path: str
    wait_seconds: float = 2.5
    css_selector: Optional[str] = None
    xpath_selector: Optional[str] = None


WEBSITE_TEST_CASES: dict[str, WebsiteTestCase] = {
    "home_page_header_image_check": WebsiteTestCase(
        name="home_page_header_image_check",
        description="Capture full page and compare with image database",
        url="https://zeissprod.service-now.com/it4u",
        screenshot_path="test_image/home_page_header_image_check.png",
        wait_seconds=2.5,
    ),
    "home_page_footer_image_check": WebsiteTestCase(
        name="home_page_footer_image_check",
        description="Open page, scroll to XPath target in footer section, and capture that element",
        url="https://zeissprod.service-now.com/it4u",
        screenshot_path="test_image/home_page_footer_image_check.png",
        wait_seconds=2.5,
        xpath_selector="//*[@id=\"sp-main-wrapper\"]/section/main/div[7]",
        
    ),
}


DEFAULT_TEST_CASE_NAME = "home_page_header_image_check"


def list_test_cases() -> list[WebsiteTestCase]:
    """Return all available test case definitions."""
    return list(WEBSITE_TEST_CASES.values())


def get_test_case(name: str) -> WebsiteTestCase:
    """Fetch test case config by name."""
    if name not in WEBSITE_TEST_CASES:
        available = ", ".join(sorted(WEBSITE_TEST_CASES.keys()))
        raise ValueError(f"Unknown test case '{name}'. Available: {available}")
    return WEBSITE_TEST_CASES[name]


# Backward-compatible alias for old constant name.
TEST_CASES = WEBSITE_TEST_CASES
