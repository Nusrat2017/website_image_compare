"""
Website screenshot capture helpers for website testing workflows.
"""

import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from log_utils import log_info, log_ok


def _create_chrome_driver(chrome_options: Options) -> webdriver.Chrome:
    """Create a Chrome WebDriver with enterprise-friendly fallbacks.

    Priority:
    1) `CHROMEDRIVER_PATH` environment variable if provided.
    2) Selenium Manager auto-resolution.
    3) webdriver-manager download (with optional SSL verify override).
    """
    custom_driver_path = os.environ.get("CHROMEDRIVER_PATH", "").strip()
    if custom_driver_path:
        if not os.path.exists(custom_driver_path):
            raise RuntimeError(f"CHROMEDRIVER_PATH does not exist: {custom_driver_path}")
        log_info(f"Using CHROMEDRIVER_PATH: {custom_driver_path}")
        return webdriver.Chrome(service=Service(custom_driver_path), options=chrome_options)

    # Auto-detect local driver placed under project ./drivers/.
    local_driver_candidates = sorted(
        Path.cwd().glob("drivers/chromedriver-*/chromedriver-win64/chromedriver.exe"),
        reverse=True,
    )
    if local_driver_candidates:
        local_driver = str(local_driver_candidates[0])
        log_info(f"Using local project ChromeDriver: {local_driver}")
        return webdriver.Chrome(service=Service(local_driver), options=chrome_options)

    try:
        # Selenium Manager can use an already-installed driver/browser pair.
        return webdriver.Chrome(options=chrome_options)
    except Exception:
        # For restricted corporate SSL/proxy environments, allow opt-out via env.
        os.environ.setdefault("WDM_SSL_VERIFY", "0")
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)


def capture_website_screenshot(
    url: str,
    output_path: str,
    wait_seconds: float = 2.5,
    headless: bool = True,
    page_load_timeout: int = 40,
) -> str:
    """Open a URL in Chrome and save a full-page screenshot.

    Returns:
        Absolute path to the saved screenshot.
    """
    if not url or not str(url).strip():
        raise ValueError("URL is required for website screenshot capture")

    normalized_url = url.strip()
    if not normalized_url.startswith(("http://", "https://")):
        normalized_url = f"https://{normalized_url}"

    abs_output = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_output), exist_ok=True)

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")

    browser_driver = None
    try:
        log_info(f"Opening website: {normalized_url}")
        browser_driver = _create_chrome_driver(chrome_options)
        browser_driver.set_page_load_timeout(int(page_load_timeout))
        browser_driver.get(normalized_url)

        # Allow dynamic page content to settle before capture.
        if wait_seconds > 0:
            time.sleep(wait_seconds)

        total_width = browser_driver.execute_script("return Math.max(document.body.scrollWidth, document.documentElement.scrollWidth);")
        total_height = browser_driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);")
        total_width = max(1280, int(total_width or 1280))
        total_height = max(1080, int(total_height or 1080))
        browser_driver.set_window_size(total_width, total_height)

        if not browser_driver.save_screenshot(abs_output):
            raise RuntimeError(f"Could not save screenshot to {abs_output}")

        log_ok(f"Website screenshot saved: {abs_output}")
        return abs_output
    except WebDriverException as exc:
        raise RuntimeError(
            "Website capture failed. Ensure Chrome is installed and driver resolution works. "
            "If your network blocks downloads, set CHROMEDRIVER_PATH to a local chromedriver.exe."
        ) from exc
    finally:
        if browser_driver is not None:
            try:
                browser_driver.quit()
            except Exception:
                pass


def capture_website_element_screenshot(
    url: str,
    output_path: str,
    css_selector: str,
    wait_seconds: float = 2.5,
    headless: bool = True,
    page_load_timeout: int = 40,
    element_wait_timeout: int = 12,
) -> str:
    """Open a URL in Chrome and save a screenshot of one element.

    Returns:
        Absolute path to the saved screenshot.
    """
    if not css_selector or not css_selector.strip():
        raise ValueError("css_selector is required for element screenshot capture")

    if not url or not str(url).strip():
        raise ValueError("URL is required for website screenshot capture")

    normalized_url = url.strip()
    if not normalized_url.startswith(("http://", "https://")):
        normalized_url = f"https://{normalized_url}"

    abs_output = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_output), exist_ok=True)

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")

    browser_driver = None
    try:
        log_info(f"Opening website: {normalized_url}")
        log_info(f"Capturing element with selector: {css_selector}")
        browser_driver = _create_chrome_driver(chrome_options)
        browser_driver.set_page_load_timeout(int(page_load_timeout))
        browser_driver.get(normalized_url)

        if wait_seconds > 0:
            time.sleep(wait_seconds)

        # Wait for footer/target block to appear before browsing to it.
        try:
            wait = WebDriverWait(browser_driver, element_wait_timeout)
            target_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
        except NoSuchElementException as exc:
            raise RuntimeError(f"Could not find element using selector: {css_selector}") from exc
        except Exception as exc:
            raise RuntimeError(
                f"Timed out waiting for visible element with selector: {css_selector}"
            ) from exc

        log_info("Browsing to target page section before screenshot")
        browser_driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_element)
        time.sleep(0.3)

        if not target_element.screenshot(abs_output):
            raise RuntimeError(f"Could not save element screenshot to {abs_output}")

        log_ok(f"Element screenshot saved: {abs_output}")
        return abs_output
    except WebDriverException as exc:
        raise RuntimeError(
            "Website capture failed. Ensure Chrome is installed and driver resolution works. "
            "If your network blocks downloads, set CHROMEDRIVER_PATH to a local chromedriver.exe."
        ) from exc
    finally:
        if browser_driver is not None:
            try:
                browser_driver.quit()
            except Exception:
                pass


def capture_website_xpath_screenshot(
    url: str,
    output_path: str,
    xpath: str,
    wait_seconds: float = 2.5,
    headless: bool = True,
    page_load_timeout: int = 40,
    element_wait_timeout: int = 12,
) -> str:
    """Open a URL, scroll to an XPath element, and save that element screenshot."""
    if not xpath or not xpath.strip():
        raise ValueError("xpath is required for xpath element screenshot capture")

    if not url or not str(url).strip():
        raise ValueError("URL is required for website screenshot capture")

    normalized_url = url.strip()
    if not normalized_url.startswith(("http://", "https://")):
        normalized_url = f"https://{normalized_url}"

    abs_output = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_output), exist_ok=True)

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")

    browser_driver = None
    try:
        log_info(f"Opening website: {normalized_url}")
        log_info(f"Capturing element with xpath: {xpath}")
        browser_driver = _create_chrome_driver(chrome_options)
        browser_driver.set_page_load_timeout(int(page_load_timeout))
        browser_driver.get(normalized_url)

        if wait_seconds > 0:
            time.sleep(wait_seconds)

        try:
            wait = WebDriverWait(browser_driver, element_wait_timeout)
            target_element = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
        except NoSuchElementException as exc:
            raise RuntimeError(f"Could not find element using xpath: {xpath}") from exc
        except Exception as exc:
            raise RuntimeError(
                f"Timed out waiting for visible element with xpath: {xpath}"
            ) from exc

        log_info("Browsing to target page section before screenshot")
        browser_driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_element)
        time.sleep(0.3)

        if not target_element.screenshot(abs_output):
            raise RuntimeError(f"Could not save element screenshot to {abs_output}")

        log_ok(f"Element screenshot saved: {abs_output}")
        return abs_output
    except WebDriverException as exc:
        raise RuntimeError(
            "Website capture failed. Ensure Chrome is installed and driver resolution works. "
            "If your network blocks downloads, set CHROMEDRIVER_PATH to a local chromedriver.exe."
        ) from exc
    finally:
        if browser_driver is not None:
            try:
                browser_driver.quit()
            except Exception:
                pass
