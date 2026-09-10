import pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

books_df = pd.read_csv('data/books_clean.csv')
# إنشاء عمود النص المدمج (مثلما فعلنا في التقييم)
books_df['text_features'] = (
    books_df['Book-Title'].fillna('') + ' ' +
    books_df['Book-Author'].fillna('') + ' ' +
    books_df['Publisher'].fillna('') + ' ' +
    books_df['Year-Of-Publication'].astype(str)
)

tfidf = TfidfVectorizer(stop_words='english', max_features=5000)
tfidf_matrix = tfidf.fit_transform(books_df['text_features'])

with open('models/tfidf_vectorizer.pkl', 'wb') as f:
    pickle.dump(tfidf, f)
with open('models/tfidf_matrix.pkl', 'wb') as f:
    pickle.dump(tfidf_matrix, f)