"""Security-incident page specific website test-case configurations and checks."""

from test_cases.common import WebsiteTestCase
from search import run_website_search_pipeline


HEADER_CLICK_XPATH = "/html/body/div/div/section/main/div[3]/div/sp-page-row/div/div[2]/span/div/div/div/a[2]"


WEBSITE_TEST_CASES: dict[str, WebsiteTestCase] = {
    "security_incident_page_image_check": WebsiteTestCase(
        name="security_incident_page_image_check",
        description=(
            "Open IT4U home page, click Security Incident card from header area, "
            "capture the landing page, and compare with stored images"
        ),
        url="https://zeissprod.service-now.com/it4u",
        screenshot_path="test_image/security_incident_page_image_check.png",
        wait_seconds=2.5,
        click_xpath_selector=HEADER_CLICK_XPATH,
        click_opens_new_window=False,
    ),
}


def list_test_cases() -> list[WebsiteTestCase]:
    """Return all available security-incident test case definitions."""
    return list(WEBSITE_TEST_CASES.values())


def get_test_case(name: str) -> WebsiteTestCase:
    """Fetch security-incident test case config by name."""
    if name not in WEBSITE_TEST_CASES:
        available = ", ".join(sorted(WEBSITE_TEST_CASES.keys()))
        raise ValueError(f"Unknown security-incident test case '{name}'. Available: {available}")
    return WEBSITE_TEST_CASES[name]


def run_security_incident_page_xpath_test(
    test_case_name: str = "security_incident_page_image_check",
    headless: bool = True,
    index_folder: str = "index",
    source_folder: str = "image_database/stored_image",
    similarity_threshold: float = 70.0,
    limit: int = 10,
    filter_size: int = 100,
) -> None:
    """Run the standard screenshot-compare flow for the Security Incident page.

    Flow:
    1) Open IT4U page
    2) Verify header XPath exists and click it
    3) Switch to new window if opened
    4) Capture landing-page screenshot and compare against stored images

    Raises:
        RuntimeError/AssertionError: when navigation or comparison setup fails.
    """
    selected_case = get_test_case(test_case_name)

    run_website_search_pipeline(
        index_folder=index_folder,
        limit=limit,
        filter_size=filter_size,
        source_folder=source_folder,
        similarity_threshold=similarity_threshold,
        url=selected_case.url,
        screenshot_path=selected_case.screenshot_path,
        wait_seconds=selected_case.wait_seconds,
        headless=headless,
        capture_click_xpath_new_window=selected_case.click_xpath_selector,
    )
