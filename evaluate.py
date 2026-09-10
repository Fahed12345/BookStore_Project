import os
import pickle
import numpy as np
import pandas as pd
from surprise import SVD, Dataset, Reader, accuracy
from surprise.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app import app
from models import db, Book

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 1. تحميل ملف التقييمات
ratings_path = os.path.join(DATA_DIR, "ratings_clean.csv")
if not os.path.exists(ratings_path):
    possible = ["ratings.csv", "BX-Book-Ratings.csv"]
    for p in possible:
        full = os.path.join(DATA_DIR, p)
        if os.path.exists(full):
            ratings_path = full
            break

if not os.path.exists(ratings_path):
    raise FileNotFoundError("Ratings file not found.")

ratings_df = pd.read_csv(ratings_path)
print(f"Loaded {len(ratings_df)} ratings.")

# 2. تحميل الكتب من قاعدة البيانات
print("Loading books from database...")
with app.app_context():
    books_query = Book.query.all()
    books_data = []
    for book in books_query:
        books_data.append(
            {
                "ISBN": book.isbn,
                "Book-Title": book.title or "",
                "Book-Author": book.author or "",
                "Publisher": book.publisher or "",
                "Year-Of-Publication": str(book.year) if book.year else "",
                "category": book.category or "",
            }
        )
    books_df = pd.DataFrame(books_data)
    print(f"Loaded {len(books_df)} books from database.")

# 3. توحيد أسماء الأعمدة في ملف التقييمات
if "User-ID" not in ratings_df.columns:
    if "user_id" in ratings_df.columns:
        ratings_df.rename(columns={"user_id": "User-ID"}, inplace=True)
    elif "User" in ratings_df.columns:
        ratings_df.rename(columns={"User": "User-ID"}, inplace=True)

if "ISBN" not in ratings_df.columns:
    if "isbn" in ratings_df.columns:
        ratings_df.rename(columns={"isbn": "ISBN"}, inplace=True)

if "Book-Rating" not in ratings_df.columns:
    if "rating" in ratings_df.columns:
        ratings_df.rename(columns={"rating": "Book-Rating"}, inplace=True)
    elif "Rating" in ratings_df.columns:
        ratings_df.rename(columns={"Rating": "Book-Rating"}, inplace=True)

# 4. تدريب SVD
reader = Reader(rating_scale=(0, 10))
data = Dataset.load_from_df(ratings_df[["User-ID", "ISBN", "Book-Rating"]], reader)
trainset, testset = train_test_split(data, test_size=0.2, random_state=42)

svd = SVD(n_factors=50, n_epochs=20, lr_all=0.005, reg_all=0.02)
svd.fit(trainset)
predictions_svd = svd.test(testset)
rmse_svd = accuracy.rmse(predictions_svd)
mae_svd = accuracy.mae(predictions_svd)   # <-- تم تصحيح الخطأ هنا (كان mae_saccuracy)
print(f"SVD - RMSE: {rmse_svd:.4f}, MAE: {mae_svd:.4f}")

# 5. بناء نموذج المحتوى (TF‑IDF + Cosine Similarity)
# تصحيح السطر الذي به خطأ:
books_df["text_features"] = (
    books_df["Book-Title"].fillna("") + " " +
    books_df["Book-Author"].fillna("") + " " +
    books_df["Publisher"].fillna("") + " " +
    books_df["Year-Of-Publication"].astype(str) + " " +
    books_df["category"].fillna("")
)

tfidf = TfidfVectorizer(stop_words="english", max_features=5000)
tfidf_matrix = tfidf.fit_transform(books_df["text_features"])
cosine_sim = cosine_similarity(tfidf_matrix)

isbn_to_idx = {isbn: i for i, isbn in enumerate(books_df["ISBN"])}
idx_to_isbn = {i: isbn for isbn, i in isbn_to_idx.items()}

# 6. دالة التنبؤ للمحتوى
def predict_content(uid, isbn, trainset_df, k=15):
    if isbn not in isbn_to_idx:
        return 5.0
    idx = isbn_to_idx[isbn]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1 : k + 1]
    user_ratings = trainset_df[trainset_df["User-ID"] == uid]
    total = 0.0
    count = 0.0
    for sim_idx, score in sim_scores:
        sim_isbn = idx_to_isbn[sim_idx]
        rating = user_ratings[user_ratings["ISBN"] == sim_isbn]["Book-Rating"].mean()
        if not np.isnan(rating):
            total += rating * score
            count += score
    return total / count if count > 0 else 5.0

# 7. تحضير بيانات التدريب لتقييم الهجين
trainset_df = pd.DataFrame(
    [(trainset.to_raw_uid(uid), trainset.to_raw_iid(iid), rating)
     for uid, iid, rating in trainset.all_ratings()],
    columns=["User-ID", "ISBN", "Book-Rating"]
)

# 8. اختبار أوزان مختلفة للهجين
weights = [0.1, 0.15, 0.2, 0.25, 0.3]
results = []

for wc in weights:
    ws = 1 - wc
    hybrid_preds = []
    for uid, isbn, true_r, est_svd, _ in predictions_svd:
        est_content = predict_content(uid, isbn, trainset_df)
        est_hybrid = ws * est_svd + wc * est_content
        est_hybrid = max(0, min(10, est_hybrid))
        # Surprise expects predictions as list of tuples (uid, iid, true_r, est, details)
        hybrid_preds.append((uid, isbn, true_r, est_hybrid, {}))
    rmse_h = accuracy.rmse(hybrid_preds, verbose=False)
    mae_h = accuracy.mae(hybrid_preds, verbose=False)
    results.append({"weight_content": wc, "weight_svd": ws, "RMSE": rmse_h, "MAE": mae_h})
    print(f"weight_content={wc:.2f}, weight_svd={ws:.2f} -> RMSE={rmse_h:.4f}, MAE={mae_h:.4f}")

# 9. عرض النتائج
results_df = pd.DataFrame(results)
print("\nWeight tuning results (with categories):")
print(results_df.to_string(index=False))

best_rmse = results_df.loc[results_df["RMSE"].idxmin()]
best_mae = results_df.loc[results_df["MAE"].idxmin()]
print(f"\nBest RMSE at weight_content={best_rmse['weight_content']:.2f} (RMSE={best_rmse['RMSE']:.4f})")
print(f"Best MAE at weight_content={best_mae['weight_content']:.2f} (MAE={best_mae['MAE']:.4f})")

# 10. حفظ النتائج
results_df.to_csv("weight_tuning_results_with_categories.csv", index=False)