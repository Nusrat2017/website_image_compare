"""
Website image comparison pipeline runner.
Captures from a website (full page or CSS-selected element) and compares against indexed images.
"""

import argparse
import os
from typing import Optional
from log_utils import log_info, log_ok, log_section, log_warn
from search_engine import search_similar_images  # Import the core search function
from utils import classify_image_content  # For image content analysis
from visualization import show_side_by_side_comparison  # Image comparison display
from negative_search import handle_negative_search_result  # Negative search detection
from positive_search import handle_positive_search_result  # Positive search detection
from build_index import needs_reindex, build_index  # Auto-indexing
from website_capture import (
    capture_website_element_screenshot,
    capture_website_screenshot,
    capture_website_xpath_screenshot,
)


def run_website_search_pipeline(
    index_folder: str = "index",
    limit: int = 10,
    filter_size: int = 100,
    source_folder: str = "image_database/stored_image",
    similarity_threshold: float = 50.0,
    url: str = "",
    screenshot_path: str = "test_image/website_capture.png",
    wait_seconds: float = 2.5,
    headless: bool = True,
    capture_selector: Optional[str] = None,
    capture_xpath: Optional[str] = None,
):
    """
    Website-only function to run screenshot capture and image comparison.
    """
    # =========================================================================
    # STEP 0: Capture website screenshot as query image
    # =========================================================================
    if not url or not str(url).strip():
        raise ValueError("url is required for website-only pipeline")
    if capture_selector and capture_xpath:
        raise ValueError("Use either capture_selector or capture_xpath, not both")

    log_section("WEBSITE CAPTURE")
    if capture_xpath:
        active_query_path = capture_website_xpath_screenshot(
            url=url,
            output_path=screenshot_path,
            xpath=capture_xpath,
            wait_seconds=wait_seconds,
            headless=headless,
        )
    elif capture_selector:
        active_query_path = capture_website_element_screenshot(
            url=url,
            output_path=screenshot_path,
            css_selector=capture_selector,
            wait_seconds=wait_seconds,
            headless=headless,
        )
    else:
        active_query_path = capture_website_screenshot(
            url=url,
            output_path=screenshot_path,
            wait_seconds=wait_seconds,
            headless=headless,
        )

    # =========================================================================
    # STEP 1: Auto-indexing - Check if index needs to be updated
    # =========================================================================
    needs_update, changes = needs_reindex(source_folder, index_folder)
    
    if needs_update:
        log_section("INDEX STATUS")
        if 'reason' in changes:
            log_info(f"Indexing required: {changes['reason']}")
        else:
            messages = []
            if changes['new'] > 0:
                messages.append(f" {changes['new']} new image(s) added")
            if changes['renamed'] > 0:
                messages.append(f" {changes['renamed']} image(s) renamed")
            if changes['deleted'] > 0 and changes['renamed'] == 0:
                messages.append(f"  {changes['deleted']} image(s) deleted")
            log_info("Indexing required:")
            for msg in messages:
                log_info(msg.strip())
        build_index(source_folder, index_folder, hash_size=32, max_size=None)
        log_ok("Indexing completed - ready to search")
    else:
        log_section("INDEX STATUS")
        log_ok(f"Index up to date - {changes['reason']}")

    # =========================================================================
    # STEP 2: Analyze what's in the query image
    # =========================================================================
    # Identify the content (e.g., "eyes", "animal", "flower")
    # This helps understand what the deep learning model is looking for
    log_section("QUERY IMAGE CONTENT ANALYSIS")
    try:
        # Get top 5 predictions about what's in the image
        predictions = classify_image_content(active_query_path, top_k=5)
        log_info(f"Query image: {os.path.abspath(active_query_path)}")
        log_info("Detected content:")
        for i, (label, confidence) in enumerate(predictions, 1):
            log_info(f"{i}. {label.replace('_', ' ').title()}: {confidence:.1f}%")
    except Exception as e:
        log_warn(f"Could not classify image: {e}")

    # =========================================================================
    # STEP 3: Run the 3-stage search pipeline
    # =========================================================================
    search_results = search_similar_images(active_query_path, index_folder, num_results=limit, candidates=filter_size)
    # this search function is from search_engine.py

    # =========================================================================
    # STEP 4: Display results with all scores
    # =========================================================================
    log_section("TOP MATCHING IMAGES")

    # Check for negative search result (no good matches)
    is_negative_match = handle_negative_search_result(search_results, active_query_path, similarity_threshold=similarity_threshold)

    # If it IS a good match, show a green popup (similar to the red popup for negative search)
    if not is_negative_match:
        handle_positive_search_result(search_results, active_query_path, similarity_threshold=similarity_threshold)
    
    log_info(f"Top {len(search_results)} matches")
    log_info("Score breakdown:")
    log_info("- Deep: Content similarity from neural network")
    log_info("- Hash: Average hash (aHash) similarity (structure)")
    log_info("- ORB: Keypoint matching (geometric similarity)")
    log_info("- Combined: Final score (33% each)")
    
    for rank, match in enumerate(search_results, 1):
        orb_score = match["orb_score_pct"]
        deep_score = match.get("deep_score_pct", 0.0)
        final_score = match["combined_score"]
        orb_text = f"{orb_score:5.1f}%" if orb_score is not None else " n/a "
        deep_text = f"{deep_score:5.1f}%"
        
        # Highlight results based on the 50% threshold
        if final_score >= similarity_threshold:
            log_ok(f"{rank:02d}. Hash:{match['hash_similarity_pct']:5.1f}% Deep:{deep_text} ORB:{orb_text} => Combined:{final_score:5.1f}% | {match['path']}")
        else:
            log_warn(f"{rank:02d}. Hash:{match['hash_similarity_pct']:5.1f}% Deep:{deep_text} ORB:{orb_text} => Combined:{final_score:5.1f}% | {match['path']}")

    # =========================================================================
    # STEP 5: Show side-by-side comparison of query and best match
    # =========================================================================
    if search_results:
        log_section("VISUAL COMPARISON")
        
        # Get similarity score from best match
        best_match_score = search_results[0]['combined_score']
        
        # Display message
        if not is_negative_match:
            log_info("Displaying query image vs. best match side by side")
        
        # Display side-by-side comparison using OpenCV with difference visualization
        show_side_by_side_comparison(active_query_path, search_results[0]['path'], 
                                     similarity_score=best_match_score,
                                     title="Query vs Best Match")


def parse_args() -> argparse.Namespace:
    """Parse CLI args for website-only search mode."""
    parser = argparse.ArgumentParser(description="Run website screenshot similarity search")
    parser.add_argument("--url", required=True, help="Website URL to capture and compare")
    parser.add_argument("--screenshot-path", default="test_image/website_capture.png", help="Path to save website screenshot")
    parser.add_argument("--wait-seconds", type=float, default=2.5, help="Wait time after page load before screenshot")
    parser.add_argument("--css-selector", default=None, help="Optional CSS selector for element-only screenshot capture")
    parser.add_argument("--xpath", default=None, help="Optional XPath for element-only screenshot capture")
    parser.add_argument("--headed", action="store_true", help="Run browser with visible window (not headless)")
    parser.add_argument("--index-folder", default="index", help="Index folder path")
    parser.add_argument("--source-folder", default="image_database/stored_image", help="Image database folder")
    parser.add_argument("--limit", type=int, default=10, help="Number of results to return")
    parser.add_argument("--filter-size", type=int, default=100, help="Stage-1 candidate count")
    parser.add_argument("--similarity-threshold", type=float, default=50.0, help="Threshold for positive/negative result")
    return parser.parse_args()

# Entry point: Run the search when this script is executed directly
if __name__ == "__main__":
    args = parse_args()
    run_website_search_pipeline(
        index_folder=args.index_folder,
        limit=args.limit,
        filter_size=args.filter_size,
        source_folder=args.source_folder,
        similarity_threshold=args.similarity_threshold,
        url=args.url,
        screenshot_path=args.screenshot_path,
        wait_seconds=args.wait_seconds,
        headless=not args.headed,
        capture_selector=args.css_selector,
        capture_xpath=args.xpath,
    )


# Backward-compatible alias for older imports.
run_search_with_defaults = run_website_search_pipeline
