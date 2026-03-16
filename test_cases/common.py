"""Shared configuration objects for website test-case modules."""

from dataclasses import dataclass, field
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
    click_xpath_selector: Optional[str] = None
    click_opens_new_window: bool = True
    required_xpaths: list[str] = field(default_factory=list)
