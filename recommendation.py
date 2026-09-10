import os
import pickle
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")

print("Loading recommendation models...")

with open(os.path.join(MODEL_DIR, "svd_model.pkl"), "rb") as f:
    svd_model = pickle.load(f)
print("SVD model loaded.")

with open(os.path.join(MODEL_DIR, "user_ids.pkl"), "rb") as f:
    all_user_ids = pickle.load(f)
with open(os.path.join(MODEL_DIR, "isbns.pkl"), "rb") as f:
    all_isbns = pickle.load(f)
print(f"Loaded {len(all_user_ids)} users and {len(all_isbns)} books (reference).")

with open(os.path.join(MODEL_DIR, "isbn_to_idx.pkl"), "rb") as f:
    isbn_to_idx = pickle.load(f)
with open(os.path.join(MODEL_DIR, "idx_to_isbn.pkl"), "rb") as f:
    idx_to_isbn = pickle.load(f)
with open(os.path.join(MODEL_DIR, "cosine_sim_matrix.pkl"), "rb") as f:
    cosine_sim = pickle.load(f)
print(f"Similarity matrix shape: {cosine_sim.shape}")

try:
    with open(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"), "rb") as f:
        tfidf_vectorizer = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "tfidf_matrix.pkl"), "rb") as f:
        tfidf_matrix = pickle.load(f)
    print("TF-IDF models loaded.")
except FileNotFoundError:
    print("TF-IDF models not found; new books will not be supported.")
    tfidf_vectorizer = None
    tfidf_matrix = None


def get_svd_recommendations(user_id, top_n=10):
    """Generate SVD recommendations for a user."""
    if user_id not in all_user_ids:
        return []
    predictions = []
    for isbn in all_isbns:
        pred = svd_model.predict(user_id, isbn)
        predictions.append((isbn, pred.est))
    predictions.sort(key=lambda x: x[1], reverse=True)
    return [isbn for isbn, _ in predictions[:top_n]]


def get_content_recommendations(isbn, top_n=10):
    """Generate content-based recommendations for a book."""
    if isbn not in isbn_to_idx:
        return []
    idx = isbn_to_idx[isbn]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:top_n + 1]
    return [idx_to_isbn[i[0]] for i in sim_scores if i[0] in idx_to_isbn]


def get_hybrid_recommendations(user_id, all_books_isbns, user_ratings=None, top_n=10,
                               weight_svd=0.9, weight_content=0.1):
    """
    Generate hybrid recommendations combining SVD and content-based filtering.

    Parameters:
        user_id: User identifier (string).
        all_books_isbns: List of all ISBNs in the current database.
        user_ratings: Dictionary {isbn: rating} with the user's current ratings.
        top_n: Number of recommendations to return.
        weight_svd: Weight for SVD predictions.
        weight_content: Weight for content-based predictions.
    """
    svd_recs = get_svd_recommendations(user_id, top_n=top_n * 2)
    using_svd = bool(svd_recs)

    combined_scores = {}
    if using_svd:
        for isbn in svd_recs:
            combined_scores[isbn] = combined_scores.get(isbn, 0) + weight_svd

    if user_ratings:
        for rated_isbn, rating in user_ratings.items():
            similar = get_content_recommendations(rated_isbn, top_n=top_n * 2)
            norm_rating = (rating - 5) / 5.0
            for sim_isbn in similar:
                if sim_isbn in combined_scores:
                    combined_scores[sim_isbn] += weight_content * norm_rating * 0.5
                else:
                    combined_scores[sim_isbn] = weight_content * norm_rating * 0.5 + 0.05

    if not combined_scores:
        return all_books_isbns[:top_n]

    sorted_items = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    return [isbn for isbn, _ in sorted_items[:top_n]]

print("Recommendation module loaded successfully.")