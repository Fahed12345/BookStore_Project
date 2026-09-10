# BookStore_Project
Book Store with recommendation

BookStore - نظام توصية الكتب الهجين

نظام توصية كتب ذكي يجمع بين التصفية التعاونية (SVD) والتصفية القائمة على المحتوى (TF-IDF)، مع تطبيق ويب تفاعلي مبني بـ Flask.

مميزات المشروع

نظام توصية هجين (Weighted Hybrid)
نموذج SVD للتصفية التعاونية
نموذج TF-IDF للتوصية القائمة على المحتوى
تسجيل مستخدمين وتقييم الكتب
سلة كتب شخصية
لوحة تحكم إدارية كاملة
إعادة تدريب النماذج بضغطة زر
معالجة مشكلة البداية الباردة (Cold Start)

المتطلبات الأساسية

قبل البدء، تأكد من تثبيت البرامج التالية على جهازك:
Python 3.9 أو أحدث
pip (يأتي مع Python عادةً)
Git (اختياري، لاستنساخ المشروع)

خطوات التشغيل على جهازك المحلي

الخطوة الأولى: تحميل المشروع

افتح سطر الأوامر (CMD أو Terminal) ونفّذ الأمر التالي:

git clone https://github.com/YOUR_USERNAME/BookStore_project.git
cd BookStore_project

استبدل YOUR_USERNAME باسم المستخدم الخاص بك على GitHub.

الخطوة الثانية: إنشاء بيئة افتراضية

على Windows:

python -m venv venv
venv\Scripts\activate

على Mac أو Linux:

python3 -m venv venv
source venv/bin/activate

بعد التفعيل، ستلاحظ ظهور (venv) على يسار سطر الأوامر.

الخطوة الثالثة: تثبيت المكتبات المطلوبة

pip install -r requirements.txt

إذا لم يكن ملف requirements.txt موجوداً، ثبّت المكتبات يدوياً:

pip install flask flask-sqlalchemy werkzeug pandas numpy scikit-learn scikit-surprise

الخطوة الرابعة: إعداد قاعدة البيانات

شغّل الأمر التالي:

python

ثم داخل بيئة Python، نفّذ:

from app import app, db
with app.app_context():
    db.create_all()
    print("تم إنشاء قاعدة البيانات بنجاح")
exit()

النتيجة: سيتم إنشاء ملف bookstore.db تلقائياً في مجلد المشروع.

الخطوة الخامسة: إضافة بيانات الكتب

تأكد من وجود ملف data/books_clean.csv، ثم نفّذ:

from app import app, populate_database
with app.app_context():
    populate_database()
exit()

النتيجة: سيتم تحميل جميع الكتب إلى قاعدة البيانات.

الخطوة السادسة: إنشاء حساب المدير

نفّذ الأوامر التالية:

from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User(
        username='admin',
        email='admin@example.com',
        password_hash=generate_password_hash('1122509'),
        is_admin=True
    )
    db.session.add(admin)
    db.session.commit()
    print("تم إنشاء حساب المدير")
exit()

بيانات الدخول: اسم المستخدم admin وكلمة المرور 1122509

الخطوة السابعة: تدريب نماذج التوصية

python train_models.py

النتيجة: سيتم إنشاء ملفات النماذج في مجلد models.

الخطوة الثامنة: تشغيل التطبيق

python app.py

افتح المتصفح واذهب إلى:

http://127.0.0.1:5000

مبروك! التطبيق يعمل الآن على جهازك.

بيانات الدخول

الحساب: مدير النظام
اسم المستخدم: admin
كلمة المرور: 1122509

هيكل المشروع

app.py                    التطبيق الرئيسي
models.py                 جداول قاعدة البيانات
recommendation.py         منطق التوصية
train_models.py           سكربت تدريب النماذج
config.py                 إعدادات التطبيق
requirements.txt          المكتبات المطلوبة
templates/                قوالب HTML
static/                   ملفات CSS و JS
data/                     ملفات CSV
models/                   النماذج المدرَّبة
bookstore.db              قاعدة البيانات (تُنشأ تلقائياً)

اختبار النظام

بعد التشغيل:
تصفح الكتب من الصفحة الرئيسية.
أنشئ حساباً جديداً أو سجّل الدخول بحساب المدير.
قيّم بعض الكتب (من 0 إلى 10).
اذهب إلى صفحة التوصيات لرؤية الاقتراحات المخصصة.

حل المشكلات الشائعة

المشكلة: ModuleNotFoundError
الحل: تأكد من تفعيل البيئة الافتراضية ثم أعد تثبيت المكتبات

المشكلة: Table doesn't exist
الحل: نفّذ خطوة إنشاء قاعدة البيانات (الخطوة الرابعة)

المشكلة: Too few ratings
الحل: أضف بعض التقييمات عبر الموقع قبل إعادة التدريب

المشكلة: Port already in use
الحل: أغلق أي تطبيق آخر يستخدم المنفذ 5000

التقنيات المستخدمة

Python 3.9 - لغة البرمجة الأساسية
Flask - إطار العمل للويب
SQLAlchemy - للتعامل مع قاعدة البيانات
Mysql - قاعدة البيانات
scikit-surprise - خوارزمية SVD
scikit-learn - TF-IDF و Cosine Similarity
Bootstrap 5 - تصميم الواجهات

التواصل

للأسئلة والاستفسارات، يرجى التواصل عبر البريد الإلكتروني أو فتح Issue في GitHub.

الترخيص

هذا المشروع مخصص للأغراض الأكاديمية والتعليمية.

---

انسخ هذا النص بالكامل والصقه في ملف README.md على GitHub. بالتوفيق!
