"""Create-ticket specific website test-case configurations."""

from test_cases.common import WebsiteTestCase


WEBSITE_TEST_CASES: dict[str, WebsiteTestCase] = {
    "create_ticket_xpath_new_window_match": WebsiteTestCase(
        name="create_ticket_xpath_new_window_match",
        description=(
            "Open IT4U home page, verify and click create-ticket XPath, switch to opened window, "
            "capture screenshot, and compare with stored images"
        ),
        url="https://zeissprod.service-now.com/it4u",
        screenshot_path="test_image/create_ticket_xpath_new_window_match.png",
        wait_seconds=2.5,
        click_xpath_selector="//*[@id=\"x9a6dbdab1be48810893e7669cd4bcb04\"]/div/div/a/div/h2",
    ),
}


def list_test_cases() -> list[WebsiteTestCase]:
    """Return all available create-ticket test case definitions."""
    return list(WEBSITE_TEST_CASES.values())


def get_test_case(name: str) -> WebsiteTestCase:
    """Fetch create-ticket test case config by name."""
    if name not in WEBSITE_TEST_CASES:
        available = ", ".join(sorted(WEBSITE_TEST_CASES.keys()))
        raise ValueError(f"Unknown create-ticket test case '{name}'. Available: {available}")
    return WEBSITE_TEST_CASES[name]
