"""
Dedicated entry point for website screenshot testing.

This script captures a screenshot from a target website URL and compares it
against the local image database using the existing 3-stage search pipeline.
"""

import argparse

from search import run_search_with_defaults


# Set your website here if you prefer code-based configuration over CLI.
DEFAULT_TARGET_URL = "https://zeissprod.service-now.com/it4u"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for website testing mode."""
    parser = argparse.ArgumentParser(
        description="Capture website screenshot and compare with image database"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_TARGET_URL,
        help="Target website URL to capture (defaults to DEFAULT_TARGET_URL in this file)",
    )
    parser.add_argument(
        "--screenshot-path",
        default="test_image/website_capture.png",
        help="Path to save website screenshot",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=2.5,
        help="Wait time after page load before screenshot",
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
        default=50.0,
        help="Threshold for positive/negative result",
    )
    return parser.parse_args()


def main() -> None:
    """Run website testing flow using the existing comparison pipeline."""
    args = parse_args()
    run_search_with_defaults(
        index_folder=args.index_folder,
        limit=args.limit,
        filter_size=args.filter_size,
        source_folder=args.source_folder,
        similarity_threshold=args.similarity_threshold,
        url=args.url,
        screenshot_path=args.screenshot_path,
        wait_seconds=args.wait_seconds,
        headless=not args.headed,
    )


if __name__ == "__main__":
    main()
