from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    age = db.Column(db.Integer)
    favorite_category = db.Column(db.String(100))
    favorite_book = db.Column(db.String(200))
    favorite_author = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)   # تأكد من وجوده
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ratings = db.relationship('Rating', back_populates='user', lazy='dynamic')
    cart_items = db.relationship('Cart', back_populates='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255))
    publisher = db.Column(db.String(255))
    year = db.Column(db.Integer)
    rating_avg = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    pdf_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image_url = db.Column(db.String(255))
    ratings = db.relationship('Rating', back_populates='book', lazy='dynamic')
    cart_items = db.relationship('Cart', back_populates='book', lazy='dynamic')
    category = db.Column(db.String(100))
    def __repr__(self):
        return f'<Book {self.title}>'

class Rating(db.Model):
    __tablename__ = 'ratings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='ratings')
    book = db.relationship('Book', back_populates='ratings')

    __table_args__ = (db.UniqueConstraint('user_id', 'book_id', name='unique_user_book_rating'),)

    def __repr__(self):
        return f'<Rating user={self.user_id} book={self.book_id} rating={self.rating}>'

class Cart(db.Model):
    __tablename__ = 'cart'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='cart_items')
    book = db.relationship('Book', back_populates='cart_items')

    __table_args__ = (db.UniqueConstraint('user_id', 'book_id', name='unique_user_book_cart'),)

    def __repr__(self):
        return f'<Cart user={self.user_id} book={self.book_id} qty={self.quantity}>'