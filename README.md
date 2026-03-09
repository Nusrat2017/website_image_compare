# Website Image Compare — Website-Only Pipeline (Deep Learning + aHash + ORB)

This repo captures screenshots from websites and compares them to a local image database using a 3-stage ensemble:

1) **Deep Learning (ResNet18)**: content/semantic similarity (filters candidates)
2) **Average Hash (aHash)**: fast structural similarity (Hamming distance)
3) **OpenCV ORB**: keypoint/geometric similarity (reranking)

It prints Top-N matches with score breakdown and shows OpenCV popups + a side-by-side comparison.

## Website testing workflow

This project now supports website screenshot testing:

1) Open a target website URL in an automated Chrome browser
2) Capture a screenshot
3) Compare that screenshot against images in `image_database/stored_image`
4) Show a green popup + visual comparison when a match is found
5) Show a red popup + visual comparison when no good match is found

## Folder layout

- `image_database/`  → database images (subfolders allowed)
- `test_image/`      → captured website screenshots
- `index/`           → generated index files (rebuild locally)
- `image_info.py`    → shared image metadata helpers (size/resolution)

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Build the index

```bash
python build_index.py
```

Creates/updates:

- `index/paths.jsonl`
- `index/hashes.npy`
- `index/deep_features.npy`
- `index/meta.json`

Note: `index/` is treated as generated output and is ignored by Git in this repo. Rebuild it locally when needed.

## Run Website Tests

What it does:

- Auto-checks whether the index needs rebuilding (new/deleted/renamed images).
- Captures a website screenshot (full page or selected element).
- Runs the 3-stage pipeline and prints results.
- Shows:
  - Red popup if no good match (below threshold)
  - Green popup if match found (above threshold)
  - Side-by-side comparison (Query | Best Match | Differences heatmap)

Direct website-only runner:

```bash
python search.py --url https://example.com --screenshot-path test_image/site.png --wait-seconds 3
python search.py --url https://example.com --css-selector "footer" --screenshot-path test_image/footer.png
```

Dedicated website-test entry point (recommended for reusable test cases):

```bash
python website_test.py --list-test-cases
python website_test.py --test-case home_page_full
python website_test.py --test-case footer_image_check
```

If you want to see the browser window while capturing:

```bash
python website_test.py --test-case footer_image_check --headed
```

Override test-case defaults from CLI when needed:

```bash
python website_test.py --test-case footer_image_check --url https://example.com --css-selector "footer img" --wait-seconds 3
```

Notes:

- Google Chrome must be installed.
- First run may download a matching ChromeDriver automatically.

Test-case definitions live in `test_cases/cases.py`. Add new cases there to grow your coverage.

## Notes on scores

- **Deep %**: content similarity from ResNet18 features
- **Hash %**: aHash similarity derived from Hamming distance
- **ORB %**: keypoint matching score (may show as `n/a` for tiny/low-detail queries)
- **Combined %**: final score used for ranking

Scoring behavior when ORB is unavailable:

- If ORB finds keypoints in the query image, combined score uses Deep + Hash + ORB.
- If ORB is not applicable for tiny/low-detail queries, combined score falls back to Deep + Hash only.

Small/low-resolution query images:

- ORB can fail to find keypoints; in that case ORB is shown as `n/a` and the combined score falls back to Deep+Hash (so ORB does not unfairly penalize matches).

## Recent cleanup updates

- Removed unused imports in `search_engine.py` (no behavior change).
- Extracted duplicated image-info helpers from `positive_search.py` and `negative_search.py` into shared `image_info.py`.
- Optimized incremental index path matching in `build_index.py` with O(1) lookup map (faster on larger datasets).
- Clarified `utils.phash_packed_bytes` documentation: function name is legacy, implementation intentionally uses **Average Hash (aHash)**.

## Tips

- First run may download ResNet18 weights (internet needed unless already cached).
- Secure download note: by default, legacy compatibility mode may disable SSL verification for model download. To enforce verification, set `IMG_COMPARE_VERIFY_SSL=1` before running.
- If the database changes, rerun `python build_index.py` (or run `python search.py` and let it auto-index).

## Logging style

To keep console output clean and consistent across modules, use shared helpers from `log_utils.py` instead of raw `print(...)` calls.

- `log_section("...")` for major blocks/headings
- `log_step("...")` for pipeline stages
- `log_info("...")` for neutral runtime information
- `log_ok("...")` for successful outcomes
- `log_warn("...")` for recoverable issues
- `log_error("...")` for hard failures

Conventions:

- Keep messages short and action-focused.
- Do not mix emoji and plain-text styles in logs.
- Use one log line per event.

