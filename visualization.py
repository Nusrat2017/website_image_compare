"""
Image Visualization Module
Side-by-side comparison and difference display functions for the image search system.
"""

import os
import cv2
import numpy as np
from log_utils import log_error, log_info


def show_side_by_side_comparison(query_image_path, match_image_path, similarity_score=100.0, title="Image Comparison"):
    """
    Display two images side by side with OpenCV for visual comparison.
    Shows a difference map when similarity is not 100%.
    
    Args:
        query_image_path: Path to the first image (query image)
        match_image_path: Path to the second image (matching image)
        similarity_score: Similarity percentage (0-100)
        title: Window title
    """
    # Load both images
    query_image = cv2.imread(query_image_path)
    match_image = cv2.imread(match_image_path)
    
    if query_image is None or match_image is None:
        log_error("Could not load images for comparison")
        return

    def _shorten_label(text: str, max_chars: int = 28) -> str:
        text = str(text)
        if len(text) <= max_chars:
            return text
        return text[: max(0, max_chars - 1)] + "…"

    def _put_bottom_right_label(image: np.ndarray, label: str, *, pad: int = 8) -> np.ndarray:
        """Draw a readable label in the bottom-right corner of a BGR image."""
        label = _shorten_label(label)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.55
        thickness = 2
        (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        image_height, image_width = image.shape[:2]
        x2 = max(pad, image_width - pad)
        y2 = max(pad, image_height - pad)
        x1 = max(pad, x2 - tw - (pad * 2))
        y1 = max(pad, y2 - th - baseline - (pad * 2))

        # Background rectangle for contrast
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 0), -1)
        # Text
        cv2.putText(image, label, (x1 + pad, y2 - pad), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        return image
    
    # Set maximum display dimensions to fit on screen.
    max_display_height = 800  # Maximum height for the comparison window
    max_display_width = 1400  # Maximum total width for the comparison window

    divider_w = 5
    panel_w = max(1, (max_display_width - (2 * divider_w)) // 3)

    # Use a stable panel height so narrow/wide crops (e.g., footer strips)
    # don't collapse into unreadable thin visualizations.
    target_height = min(420, max_display_height)

    def _fit_to_panel(image: np.ndarray, width: int, height: int) -> np.ndarray:
        """Fit image into a fixed panel using letterboxing while preserving aspect ratio."""
        ih, iw = image.shape[:2]
        scale = min(width / max(1, iw), height / max(1, ih))
        new_w = max(1, int(iw * scale))
        new_h = max(1, int(ih * scale))
        resized = cv2.resize(image, (new_w, new_h))

        panel = np.zeros((height, width, 3), dtype=np.uint8)
        y0 = (height - new_h) // 2
        x0 = (width - new_w) // 2
        panel[y0:y0 + new_h, x0:x0 + new_w] = resized
        return panel

    # Normalize both sides to consistent panel size.
    query_resized = _fit_to_panel(query_image, panel_w, target_height)
    match_resized = _fit_to_panel(match_image, panel_w, target_height)
    
    def _blend_mask(base: np.ndarray, mask: np.ndarray, color: tuple[int, int, int], alpha: float) -> np.ndarray:
        overlay = base.copy()
        overlay[mask > 0] = color
        return cv2.addWeighted(base, 1.0 - alpha, overlay, alpha, 0)

    def _add_panel_title(panel: np.ndarray, text: str) -> np.ndarray:
        title_h = 34
        strip = np.full((title_h, panel.shape[1], 3), 26, dtype=np.uint8)
        cv2.putText(strip, text, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (235, 235, 235), 2, cv2.LINE_AA)
        return np.vstack((strip, panel))

    # Calculate binary masks for matched/unmatched regions.
    difference = cv2.absdiff(query_resized, match_resized)
    difference_gray = cv2.cvtColor(difference, cv2.COLOR_BGR2GRAY)
    difference_gray = cv2.GaussianBlur(difference_gray, (5, 5), 0)

    _, unmatched_mask = cv2.threshold(difference_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((3, 3), np.uint8)
    unmatched_mask = cv2.morphologyEx(unmatched_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    unmatched_mask = cv2.morphologyEx(unmatched_mask, cv2.MORPH_DILATE, kernel, iterations=1)
    matched_mask = cv2.bitwise_not(unmatched_mask)

    # Panel 1: plain query image (no overlay).
    query_plain = query_resized.copy()

    # Panel 2: best match with only matched regions highlighted.
    match_with_matched = _blend_mask(match_resized.copy(), matched_mask, (40, 180, 70), 0.30)

    # Panel 3: best match with only unmatched regions highlighted.
    match_with_unmatched = _blend_mask(match_resized.copy(), unmatched_mask, (40, 40, 230), 0.40)
    unmatched_contours, _ = cv2.findContours(unmatched_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in unmatched_contours:
        if cv2.contourArea(contour) < 40:
            continue
        cv2.drawContours(match_with_unmatched, [contour], -1, (0, 0, 255), 1)

    _put_bottom_right_label(query_plain, os.path.basename(query_image_path))
    _put_bottom_right_label(match_with_matched, os.path.basename(match_image_path))
    _put_bottom_right_label(match_with_unmatched, os.path.basename(match_image_path))

    query_panel = _add_panel_title(query_plain, "Query Image")
    match_panel = _add_panel_title(match_with_matched, f"Best Match - Matched Parts ({similarity_score:.1f}%)")
    heat_panel = _add_panel_title(match_with_unmatched, "Best Match - Unmatched Parts")

    divider = np.full((query_panel.shape[0], divider_w, 3), 210, dtype=np.uint8)
    side_by_side_comparison = np.hstack((query_panel, divider, match_panel, divider, heat_panel))

    # Footer legend bar
    legend_h = 34
    legend = np.full((legend_h, side_by_side_comparison.shape[1], 3), 20, dtype=np.uint8)
    cv2.putText(legend, "Panel 2 (Green): matched regions on best match", (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (130, 230, 130), 1, cv2.LINE_AA)
    cv2.putText(legend, "Panel 3 (Red): unmatched regions on best match", (650, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (120, 120, 255), 1, cv2.LINE_AA)
    side_by_side_comparison = np.vstack((side_by_side_comparison, legend))
    
    # Scale down the final comparison if it's too wide to fit on screen
    comparison_height, comparison_width = side_by_side_comparison.shape[:2]
    if comparison_width > max_display_width or comparison_height > max_display_height:
        scale_factor = min(max_display_width / comparison_width, max_display_height / comparison_height)
        new_width = int(comparison_width * scale_factor)
        new_height = int(comparison_height * scale_factor)
        side_by_side_comparison = cv2.resize(side_by_side_comparison, (new_width, new_height))
        log_info(f"Scaled comparison to fit screen: {new_width}x{new_height}")
    
    # Display the comparison
    cv2.imshow(title, side_by_side_comparison)
    log_info("Side-by-side comparison displayed")
    log_info("Panel 2 (green) shows matched regions on best match")
    log_info("Panel 3 (red) shows unmatched regions on best match")
    log_info("Press any key to close")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
