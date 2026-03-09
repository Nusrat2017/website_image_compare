"""
Image Search Engine - Core search algorithm implementation
This file contains the main search function that orchestrates the 3-stage pipeline.
"""

import os
import json
import numpy as np
from log_utils import log_ok, log_step

# Import utility functions for image comparison
from utils import (
    ahash_packed_bytes,  # Extract Average Hash (aHash) from image
    dist_to_percent,  # Convert distance to percentage
    load_paths_jsonl,  # Load image paths from index
    extract_deep_features,  # Extract deep learning features
    orb_rerank_with_info,  # Rerank + report if ORB was applicable
    BIT_COUNT_LOOKUP_TABLE,  # Fast bit counting for hash comparison
)


def search_similar_images(query_image: str, index_folder: str, num_results: int = 10, candidates: int = 100):
    """
    Search for similar images using a 3-stage pipeline:
    
    STAGE 1: Deep Learning (33% weight for final ranking)
        - Uses ResNet18 neural network to understand image content
        - Filters top 100 most content-similar images from database
        - Works well with different colors, angles, and lighting
    
    STAGE 2: Average Hash (aHash) (33% weight for final ranking)
        - Fast comparison based on image structure
        - Applied only on filtered candidates from Stage 1
    
    STAGE 3: ORB Features (33% weight for final ranking)
        - Keypoint-based matching for geometric similarity
        - Handles rotations and perspective changes
    
    Args:
        query_image: Path to the image you want to search for
        index_folder: Folder containing pre-built index files
        num_results: How many similar images to return
        candidates: How many images to filter in Stage 1 (higher = slower but more thorough)
    
    Returns:
        List of matching images with scores, sorted by similarity
    """
    # Load all the index files that were created by build_index.py
    meta_path = os.path.join(index_folder, "meta.json")
    paths_path = os.path.join(index_folder, "paths.jsonl")
    hashes_path = os.path.join(index_folder, "hashes.npy")
    features_path = os.path.join(index_folder, "deep_features.npy")

    # Read configuration about how the index was built
    with open(meta_path, "r", encoding="utf-8") as meta_file:
        config = json.load(meta_file)

    hash_size = int(config["hash_size"])  # Size of average hash (aHash)
    max_size = config.get("max_side", 1024)  # Image resize setting

    # Load all data from the index
    image_paths = load_paths_jsonl(paths_path)  # All image file paths
    stored_hashes = np.load(hashes_path, mmap_mode="r")  # Pre-computed hashes
    stored_features = np.load(features_path, mmap_mode="r")  # Pre-computed deep features

    # =========================================================================
    # STAGE 1: Deep Learning Content Filtering (MOST IMPORTANT)
    # =========================================================================
    # This stage understands WHAT is in the image (eyes, animals, objects, etc.)
    # and filters down to the most content-similar images.
    # Works even if color, angle, or lighting is different!
    log_step("Stage 1: Deep learning content filtering")
    
    # Extract semantic features from query image (512 numbers representing content)
    query_features = extract_deep_features(query_image)
    
    # Compare query with ALL indexed images using cosine similarity
    # Higher score = more similar content
    deep_similarity_scores = np.dot(stored_features, query_features)
    
    # Select only the top candidates with highest content similarity
    # This dramatically reduces the search space for next stages
    num_candidates = min(candidates, len(deep_similarity_scores))
    best_indices = np.argpartition(deep_similarity_scores, -num_candidates)[-num_candidates:]  # Find top N
    best_indices = best_indices[np.argsort(deep_similarity_scores[best_indices])[::-1]]  # Sort by score
    log_ok(f"Deep learning filtered: {len(best_indices)} images from {len(deep_similarity_scores)} total")

    # =========================================================================
    # STAGE 2: Average Hash (aHash) Refinement
    # =========================================================================
    # Now refine the filtered candidates using average hash (aHash) comparison.
    # aHash captures overall image structure and layout.
    # Fast and works well for finding visually similar images.
    log_step(f"Stage 2: aHash refinement on {len(best_indices)} filtered candidates")
    
    # Calculate average hash (aHash) for the query image
    query_hash = ahash_packed_bytes(query_image, hash_size=hash_size, max_side=max_size)
    
    # Compare query hash with each filtered candidate
    candidate_matches = []
    for candidate_index in best_indices:
        # Calculate how many bits are different (Hamming distance)
        # Lower distance = more similar structure
        hash_distance_bits = int(np.sum(BIT_COUNT_LOOKUP_TABLE[np.bitwise_xor(stored_hashes[candidate_index], query_hash)]))
        
        # Get the deep learning score from Stage 1
        deep_similarity = float(deep_similarity_scores[candidate_index])
        deep_similarity_pct = ((deep_similarity + 1) / 2) * 100.0  # Convert from [-1,1] to [0,100]
        
        # Store all scores for this match
        candidate_matches.append({
            "path": image_paths[int(candidate_index)],
            "deep_score_pct": deep_similarity_pct,  # From Stage 1
            "hash_distance_bits": hash_distance_bits,  # Raw bit difference
            "hash_similarity_pct": dist_to_percent(hash_distance_bits, hash_size),  # As percentage
            "phash_distance_bits": hash_distance_bits,  # Backward-compatible alias
            "phash_similarity_pct": dist_to_percent(hash_distance_bits, hash_size),  # Backward-compatible alias
        })

    # =========================================================================
    # STAGE 3: ORB Feature Matching for Final Ranking
    # =========================================================================
    # Use keypoint detection to find geometric matches.
    # ORB finds distinctive points (corners, edges) and matches them.
    # Good for handling rotations, scale changes, and perspective shifts.
    if len(candidate_matches) > 0:
        log_step(f"Stage 3: ORB feature matching on all {len(candidate_matches)} candidates")
        
        # Apply ORB matching to ALL candidates (not just top 50)
        # This ensures every candidate gets a proper ORB score for accurate ranking
        paths_to_check = [match_item["path"] for match_item in candidate_matches]
        
        # Detect and match keypoints between query and candidates.
        # For very small / low-detail query images ORB may have no usable keypoints.
        orb_results, query_has_orb = orb_rerank_with_info(query_image, paths_to_check, max_side=1024, nfeatures=5000)
        orb_scores_by_path = {path: score for path, score in orb_results}

        # Add ORB scores to all matches
        for match_item in candidate_matches:
            match_item["orb_score_pct"] = orb_scores_by_path.get(match_item["path"], 0.0) if query_has_orb else None

        # =====================================================================
        # FINAL SCORE CALCULATION
        # =====================================================================
        # If ORB is applicable, use equal-weight 3-model ensemble.
        # If ORB is NOT applicable (common for tiny images), do NOT punish the match
        # with a forced 0% ORB score. Instead combine Deep+Hash only.
        if query_has_orb:
            for match_item in candidate_matches:
                match_item["combined_score"] = (
                    0.33 * match_item["deep_score_pct"]
                    + 0.33 * match_item["hash_similarity_pct"]
                    + 0.34 * float(match_item["orb_score_pct"] or 0.0)  # 0.34 so total = 1.0
                )
        else:
            for match_item in candidate_matches:
                match_item["combined_score"] = 0.5 * match_item["deep_score_pct"] + 0.5 * match_item["hash_similarity_pct"]

        # Sort all results by final combined score (highest first)
        candidate_matches.sort(key=lambda match_item: match_item["combined_score"], reverse=True)
    
    # Return only the top requested number of results
    log_ok(f"Returning top {min(num_results, len(candidate_matches))} results")
    return candidate_matches[:num_results]


# Backward-compatible alias for existing imports.
search = search_similar_images
