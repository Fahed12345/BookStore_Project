import pandas as pd
from app import app, db
from models import User, Rating, Book

def load_users_from_ratings():
    """إدراج جميع المستخدمين الموجودين في ملف التقييمات (إذا لم يكونوا موجودين)"""
    df = pd.read_csv('data/ratings_clean.csv')
    user_ids = df['User-ID'].unique()
    count = 0
    for uid in user_ids:
        user_id = int(uid)
        user = User.query.get(user_id)
        if user is None:
            new_user = User(
                id=user_id,
                username=f"user_{user_id}",
                email=f"user_{user_id}@example.com",
                password_hash="dummy_hash",
                age=None
            )
            db.session.add(new_user)
            count += 1
    db.session.commit()
    print(f"✅ Inserted {count} new users (from ratings file).")

def load_ratings():
    """إدراج التقييمات من ملف ratings_clean.csv"""
    df = pd.read_csv('data/ratings_clean.csv')
    count = 0
    for _, row in df.iterrows():
        book = Book.query.filter_by(isbn=row['ISBN']).first()
        if not book:
            continue  # تخطى إذا كان الكتاب غير موجود
        existing = Rating.query.filter_by(
            user_id=row['User-ID'],
            book_id=book.id
        ).first()
        if not existing:
            rating = Rating(
                user_id=row['User-ID'],
                book_id=book.id,
                rating=row['Book-Rating']
            )
            db.session.add(rating)
            count += 1
    db.session.commit()
    print(f"✅ Inserted {count} new ratings.")

if __name__ == '__main__':
    with app.app_context():
        # 1. إدراج المستخدمين أولاً (لتجنب مشكلة المفتاح الأجنبي)
        load_users_from_ratings()
        # 2. إدراج التقييمات
        load_ratings()