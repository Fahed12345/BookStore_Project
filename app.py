import os
import pickle
from datetime import datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from models import Book, Cart, Rating, User, db
from recommendation import (
    all_user_ids,
    get_content_recommendations,
    get_hybrid_recommendations,
    get_svd_recommendations,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")

app = Flask(__name__)
app.config.from_object(Config)

try:
    print("Config loaded successfully.")
    print(f"DATABASE URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
except KeyError:
    print("Config NOT loaded! SQLALCHEMY_DATABASE_URI missing.")
    print("Available keys:", list(app.config.keys())[:10])

db.init_app(app)


def get_popular_books(limit=12):
    return Book.query.order_by(Book.rating_count.desc()).limit(limit).all()


def get_user_from_session():
    user_id = session.get("user_id")
    if user_id:
        return User.query.get(user_id)
    return None


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        user = db.session.get(User, session["user_id"])
        if not is_admin(user):
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def is_admin(user):
    return user and user.is_admin


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return "Welcome Admin!"


@app.route("/admin/books")
@admin_required
def admin_books():
    user = get_user_from_session()
    if not is_admin(user):
        flash("Access denied. Admin only.", "danger")
        return redirect(url_for("index"))

    books = Book.query.order_by(Book.id.desc()).all()
    return render_template("admin_books.html", books=books, user=user)


@app.route("/admin/books/delete/<int:book_id>", methods=["POST"])
@admin_required
def admin_delete_book(book_id):
    user = get_user_from_session()
    if not is_admin(user):
        flash("Access denied.", "danger")
        return redirect(url_for("index"))

    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash(f'Book "{book.title}" deleted.', "info")
    return redirect(url_for("admin_books"))


@app.route("/admin/retrain", methods=["POST"])
@admin_required
def retrain_models():
    try:
        from train_models import train_models

        train_models()
        flash("Models retrained successfully!", "success")
    except Exception as e:
        flash(f"Error during retraining: {str(e)}", "danger")
    return redirect(url_for("admin_books"))


@app.route("/admin/books/edit/<int:book_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_book(book_id):
    user = get_user_from_session()
    if not is_admin(user):
        flash("Access denied.", "danger")
        return redirect(url_for("index"))

    book = Book.query.get_or_404(book_id)

    categories_query = (
        db.session.query(Book.category)
        .distinct()
        .filter(Book.category.isnot(None), Book.category != "")
        .all()
    )
    categories = sorted([cat[0] for cat in categories_query if cat[0] is not None])
    if not categories:
        categories = [
            "Fiction",
            "Non-Fiction",
            "Science",
            "History",
            "Romance",
            "Mystery",
            "Fantasy",
            "Biography",
            "Poetry",
            "Travel",
        ]

    if request.method == "POST":
        isbn = request.form.get("isbn", "").strip()
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        publisher = request.form.get("publisher", "").strip()
        year = request.form.get("year", "").strip()
        category = request.form.get("category", "").strip()
        image_url = request.form.get("image_url", "").strip()

        if not title or not author:
            flash("Title and Author are required.", "danger")
            return redirect(url_for("admin_edit_book", book_id=book.id))

        book.isbn = isbn if isbn else book.isbn
        book.title = title
        book.author = author
        book.publisher = publisher if publisher else None
        book.year = int(year) if year and year.isdigit() else None
        book.category = category if category else None
        book.image_url = image_url if image_url else None

        db.session.commit()
        flash(f'Book "{book.title}" updated successfully!', "success")
        return redirect(url_for("admin_books"))

    return render_template("admin_edit_book.html", book=book, user=user, categories=categories)


@app.route('/admin/books/add', methods=['GET', 'POST'])
@admin_required
def admin_add_book():
    user = get_user_from_session()
    if not is_admin(user):
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('index'))

    # جلب التصنيفات (للقائمة المنسدلة)
    categories_query = db.session.query(Book.category).distinct().filter(
        Book.category.isnot(None),
        Book.category != ''
    ).all()
    categories = sorted([cat[0] for cat in categories_query if cat[0] is not None])
    if not categories:
        categories = ['Fiction', 'Non-Fiction', 'Science', 'History', 'Romance', 
                      'Mystery', 'Fantasy', 'Biography', 'Poetry', 'Travel']

    if request.method == 'POST':
        # جلب البيانات من النموذج
        isbn = request.form.get('isbn', '').strip()
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        publisher = request.form.get('publisher', '').strip()
        year = request.form.get('year', '').strip()
        category = request.form.get('category', '').strip()
        image_url = request.form.get('image_url', '').strip()

        # طباعة البيانات في الطرفية للتحقق
        print(f"DEBUG - ISBN: {isbn}, Title: {title}, Author: {author}")

        # التحقق من البيانات الأساسية
        if not title or not author:
            flash('Title and Author are required.', 'danger')
            return render_template('admin_add_book.html', user=user, categories=categories)

        # إنشاء ISBN إذا لم يُدخل
        if not isbn:
            isbn = f"AR-{int(datetime.now().timestamp())}"
        else:
            # تحقق من وجود ISBN مكرر (إذا كان موجوداً بالفعل)
            existing_book = Book.query.filter_by(isbn=isbn).first()
            if existing_book:
                flash(f'Book with ISBN "{isbn}" already exists.', 'danger')
                return render_template('admin_add_book.html', user=user, categories=categories)

        # إنشاء الكتاب
        new_book = Book(
            isbn=isbn,
            title=title,
            author=author,
            publisher=publisher if publisher else None,
            year=int(year) if year and year.isdigit() else None,
            category=category if category else None,
            image_url=image_url if image_url else None,
            rating_avg=0.0,
            rating_count=0
        )

        try:
            db.session.add(new_book)
            db.session.commit()
            flash(f'Book "{title}" added successfully!', 'success')
            return redirect(url_for('admin_books'))  # <-- تأكد من وجود هذا السطر
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding book: {str(e)}', 'danger')
            return render_template('admin_add_book.html', user=user, categories=categories)

    # إذا كان الطلب GET
    return render_template('admin_add_book.html', user=user, categories=categories)
@app.route("/")
def index():
    popular_books = get_popular_books(100)
    user = get_user_from_session()
    return render_template("index.html", books=popular_books, user=user)


@app.route("/book/<isbn>")
def book_detail(isbn):
    book = Book.query.filter_by(isbn=isbn).first_or_404()
    similar_isbns = get_content_recommendations(isbn, top_n=5)
    similar_books = Book.query.filter(Book.isbn.in_(similar_isbns)).all()
    user = get_user_from_session()
    user_rating = None
    if user:
        rating_obj = Rating.query.filter_by(user_id=user.id, book_id=book.id).first()
        if rating_obj:
            user_rating = rating_obj.rating
    return render_template(
        "book_detail.html",
        book=book,
        similar_books=similar_books,
        user=user,
        user_rating=user_rating,
    )


@app.route("/rate/<isbn>", methods=["POST"])
@login_required
def rate_book(isbn):
    user = get_user_from_session()
    book = Book.query.filter_by(isbn=isbn).first_or_404()
    rating_value = float(request.form.get("rating", 0))
    if rating_value < 0 or rating_value > 10:
        flash("Rating must be between 0 and 10.", "danger")
        return redirect(url_for("book_detail", isbn=isbn))

    rating_obj = Rating.query.filter_by(user_id=user.id, book_id=book.id).first()
    if rating_obj:
        rating_obj.rating = rating_value
        rating_obj.created_at = datetime.utcnow()
        flash("Rating updated successfully.", "success")
    else:
        new_rating = Rating(user_id=user.id, book_id=book.id, rating=rating_value)
        db.session.add(new_rating)
        flash("Rating added successfully.", "success")

    avg = db.session.query(db.func.avg(Rating.rating)).filter_by(book_id=book.id).scalar()
    count = db.session.query(Rating).filter_by(book_id=book.id).count()
    book.rating_avg = avg if avg else 0.0
    book.rating_count = count
    db.session.commit()

    return redirect(url_for("book_detail", isbn=isbn))


@app.route("/cart")
@login_required
def cart():
    user = get_user_from_session()
    cart_items = Cart.query.filter_by(user_id=user.id).all()
    total_price = 0.0
    return render_template("cart.html", cart_items=cart_items, total=total_price, user=user)


@app.route("/add_to_cart/<isbn>", methods=["POST"])
@login_required
def add_to_cart(isbn):
    user = get_user_from_session()
    book = Book.query.filter_by(isbn=isbn).first_or_404()
    quantity = int(request.form.get("quantity", 1))

    cart_item = Cart.query.filter_by(user_id=user.id, book_id=book.id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        new_item = Cart(user_id=user.id, book_id=book.id, quantity=quantity)
        db.session.add(new_item)
    db.session.commit()
    flash(f'Added "{book.title}" to cart.', "success")
    return redirect(url_for("cart"))


@app.route("/remove_from_cart/<int:item_id>", methods=["POST"])
@login_required
def remove_from_cart(item_id):
    item = Cart.query.get_or_404(item_id)
    if item.user_id != session["user_id"]:
        flash("You are not authorized to remove this item.", "danger")
        return redirect(url_for("cart"))
    db.session.delete(item)
    db.session.commit()
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart"))


@app.route("/recommendations")
@login_required
def recommendations():
    user = get_user_from_session()

    all_books = Book.query.all()
    all_isbns = [book.isbn for book in all_books]

    user_ratings = {}
    for rating in Rating.query.filter_by(user_id=user.id).all():
        book = Book.query.get(rating.book_id)
        if book:
            user_ratings[book.isbn] = rating.rating

    rec_isbns = get_hybrid_recommendations(
        user_id=str(user.id),
        all_books_isbns=all_isbns,
        user_ratings=user_ratings,
        top_n=10,
        weight_svd=0.9,
        weight_content=0.1,
    )

    if not rec_isbns:
        rec_books = get_popular_books(10)
    else:
        rec_books = Book.query.filter(Book.isbn.in_(rec_isbns)).all()
        order = {isbn: i for i, isbn in enumerate(rec_isbns)}
        rec_books.sort(key=lambda b: order.get(b.isbn, 999))

    return render_template("recommendations.html", books=rec_books, user=user)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_user_from_session()

    categories_query = (
        db.session.query(Book.category)
        .distinct()
        .filter(Book.category.isnot(None), Book.category != "")
        .all()
    )
    categories = sorted([cat[0] for cat in categories_query if cat[0] is not None])
    if not categories:
        categories = [
            "Fiction",
            "Non-Fiction",
            "Science",
            "History",
            "Romance",
            "Mystery",
            "Fantasy",
            "Biography",
            "Poetry",
            "Travel",
        ]

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        age = request.form.get("age", type=int)
        favorite_category = request.form.get("favorite_category", "").strip()
        favorite_book = request.form.get("favorite_book", "").strip()
        favorite_author = request.form.get("favorite_author", "").strip()

        if username and username != user.username:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash("Username already taken.", "danger")
                return redirect(url_for("profile"))
        if email and email != user.email:
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash("Email already registered.", "danger")
                return redirect(url_for("profile"))

        user.username = username or user.username
        user.email = email or user.email
        user.age = age if age else None
        user.favorite_category = favorite_category if favorite_category else None
        user.favorite_book = favorite_book if favorite_book else None
        user.favorite_author = favorite_author if favorite_author else None

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user, categories=categories)


@app.route('/register', methods=['GET', 'POST'])
def register():
    categories = []
    try:
        with open(os.path.join(MODEL_DIR, 'categories_list.pkl'), 'rb') as f:
            categories = pickle.load(f)
            if not isinstance(categories, list):
                categories = list(categories)
    except FileNotFoundError:
        categories = ['Fiction', 'Non-Fiction', 'Science', 'History', 'Romance', 
                      'Mystery', 'Fantasy', 'Biography', 'Poetry', 'Travel']
        print("categories_list.pkl not found, using default categories.")

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        age = request.form.get('age', type=int)
        favorite_category = request.form.get('favorite_category')
        favorite_book = request.form.get('favorite_book')
        favorite_author = request.form.get('favorite_author')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html', categories=categories)

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('register.html', categories=categories)
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html', categories=categories)

        hashed_password = generate_password_hash(password)
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            age=age,
            favorite_category=favorite_category,
            favorite_book=favorite_book,
            favorite_author=favorite_author,
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', categories=categories)

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("index"))

    books = (
        Book.query.filter(
            db.or_(
                Book.title.ilike(f"%{query}%"),
                Book.author.ilike(f"%{query}%"),
                Book.publisher.ilike(f"%{query}%"),
            )
        )
        .order_by(Book.rating_avg.desc())
        .limit(30)
        .all()
    )

    user = get_user_from_session()
    return render_template("search_results.html", books=books, query=query, user=user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('login.html')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("index"))


def populate_database():
    with app.app_context():
        if Book.query.count() > 0:
            print("Books already exist, skipping population.")
            return

        import pandas as pd

        try:
            books_df = pd.read_csv("data/books_clean.csv")
            print(f"Loaded {len(books_df)} rows from CSV.")
        except FileNotFoundError:
            print("CSV file not found at data/books_clean.csv")
            return

        inserted = 0
        errors = []
        for idx, row in books_df.iterrows():
            try:
                year_val = row.get("Year-Of-Publication")
                if pd.notna(year_val):
                    try:
                        year = int(float(year_val))
                    except (ValueError, TypeError):
                        year = None
                else:
                    year = None

                isbn = str(row["ISBN"]).strip()

                if Book.query.filter_by(isbn=isbn).first():
                    errors.append(f"Row {idx}: ISBN {isbn} already exists, skipping.")
                    continue

                image_col = None
                if "Image-URL-M" in row and pd.notna(row["Image-URL-M"]):
                    image_col = row["Image-URL-M"]
                elif "Image-URL-S" in row and pd.notna(row["Image-URL-S"]):
                    image_col = row["Image-URL-S"]
                elif "Image-URL-L" in row and pd.notna(row["Image-URL-L"]):
                    image_col = row["Image-URL-L"]

                book = Book(
                    isbn=isbn,
                    title=str(row["Book-Title"]).strip(),
                    author=str(row["Book-Author"]).strip(),
                    publisher=str(row["Publisher"]).strip() if pd.notna(row["Publisher"]) else None,
                    year=year,
                    image_url=image_col,
                    rating_avg=0.0,
                    rating_count=0,
                )
                db.session.add(book)
                inserted += 1

                if inserted % 50 == 0:
                    db.session.commit()
                    print(f"Committed {inserted} books...")

            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
                db.session.rollback()

        try:
            db.session.commit()
            print("Final commit successful.")
        except Exception as e:
            errors.append(f"Final commit error: {e}")
            db.session.rollback()

        count = Book.query.count()
        print(f"Actual rows in database: {count}")
        print(f"Successfully inserted: {inserted}")
        if errors:
            print(f"Errors encountered ({len(errors)}):")
            for err in errors[:15]:
                print(f"  - {err}")
            if len(errors) > 15:
                print(f"  ... and {len(errors)-15} more errors.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        populate_database()
    app.run(debug=True, host="0.0.0.0", port=5000)