import os
import pickle
import numpy as np
import pandas as pd
from surprise import SVD, Dataset, Reader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app import app
from models import db, Book, Rating

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")


def train_models():
    """
    Train all recommendation models from scratch using the latest data from the database.
    This includes SVD collaborative filtering and content-based similarity (TF-IDF + cosine).
    """
    print("Starting model training...")

    with app.app_context():
        ratings = db.session.query(Rating).all()
        if len(ratings) < 10:
            print("Too few ratings (less than 10). Training aborted.")
            return

        ratings_data = []
        for r in ratings:
            book = Book.query.get(r.book_id)
            if book:
                ratings_data.append(
                    {
                        "User-ID": r.user_id,
                        "ISBN": book.isbn,
                        "Book-Rating": r.rating,
                    }
                )
        ratings_df = pd.DataFrame(ratings_data)
        print(f"Loaded {len(ratings_df)} ratings from database.")

        books = Book.query.all()
        books_data = []
        for b in books:
            books_data.append(
                {
                    "ISBN": b.isbn,
                    "Book-Title": b.title or "",
                    "Book-Author": b.author or "",
                    "Publisher": b.publisher or "",
                    "Year-Of-Publication": str(b.year) if b.year else "",
                    "category": b.category or "",
                }
            )
        books_df = pd.DataFrame(books_data)
        print(f"Loaded {len(books_df)} books from database.")

        reader = Reader(rating_scale=(0, 10))
        data = Dataset.load_from_df(ratings_df[["User-ID", "ISBN", "Book-Rating"]], reader)
        trainset = data.build_full_trainset()
        svd = SVD(n_factors=50, n_epochs=20, lr_all=0.005, reg_all=0.02)
        svd.fit(trainset)

        with open(os.path.join(MODEL_DIR, "svd_model.pkl"), "wb") as f:
            pickle.dump(svd, f)
        print("SVD model trained and saved.")

        user_ids = list(set(ratings_df["User-ID"]))
        isbns = list(set(ratings_df["ISBN"]))
        with open(os.path.join(MODEL_DIR, "user_ids.pkl"), "wb") as f:
            pickle.dump(user_ids, f)
        with open(os.path.join(MODEL_DIR, "isbns.pkl"), "wb") as f:
            pickle.dump(isbns, f)
        print(f"Saved {len(user_ids)} users and {len(isbns)} books.")

        books_df["text_features"] = (
            books_df["Book-Title"]
            + " "
            + books_df["Book-Author"]
            + " "
            + books_df["Publisher"]
            + " "
            + books_df["Year-Of-Publication"]
            + " "
            + books_df["category"]
        )

        tfidf = TfidfVectorizer(stop_words="english", max_features=5000)
        tfidf_matrix = tfidf.fit_transform(books_df["text_features"])
        cosine_sim = cosine_similarity(tfidf_matrix)

        isbn_to_idx = {isbn: i for i, isbn in enumerate(books_df["ISBN"])}
        idx_to_isbn = {i: isbn for isbn, i in isbn_to_idx.items()}

        with open(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"), "wb") as f:
            pickle.dump(tfidf, f)
        with open(os.path.join(MODEL_DIR, "tfidf_matrix.pkl"), "wb") as f:
            pickle.dump(tfidf_matrix, f)
        with open(os.path.join(MODEL_DIR, "isbn_to_idx.pkl"), "wb") as f:
            pickle.dump(isbn_to_idx, f)
        with open(os.path.join(MODEL_DIR, "idx_to_isbn.pkl"), "wb") as f:
            pickle.dump(idx_to_isbn, f)
        with open(os.path.join(MODEL_DIR, "cosine_sim_matrix.pkl"), "wb") as f:
            pickle.dump(cosine_sim, f)

        print("All models trained and saved successfully.")
        print("Training completed.")


if __name__ == "__main__":
    train_models()