# database.py
# PostgreSQL veritabanı bağlantısını ve SQLAlchemy oturum yönetimini sağlar.

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv # .env dosyasını yüklemek için

# .env dosyasını yükle
load_dotenv()

# Veritabanı URL'sini ortam değişkeninden al
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise Exception("DATABASE_URL environment variable is not set.")

# SQLAlchemy Engine'i oluştur
# 'connect_args' parametresi, SQLite gibi bazı veritabanları için gereklidir,
# PostgreSQL için genellikle doğrudan kullanılabilir.
# production ortamında pool_pre_ping=True kullanılması bağlantı sorunlarını azaltabilir.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# Her veritabanı isteği için bir oturum oluşturmak için SessionLocal sınıfı
# autoflush=False: SQLAlchemy'nin her işlemde oturumu otomatik olarak temizlemesini engeller.
#                   Bu, bazı durumlarda gereksiz sorguları önleyebilir.
# autocommit=False: Her işlemi açıkça commit etmeniz veya geri almanız gerektiği anlamına gelir.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Veritabanı modelleri için temel sınıf
Base = declarative_base()

# FastAPI bağımlılığı olarak kullanılacak veritabanı oturumu sağlayıcı fonksiyon
def get_db():
    db = SessionLocal() # Yeni bir veritabanı oturumu oluştur
    try:
        yield db # Oturumu istek işleyiciye (route handler) gönder
    finally:
        db.close() # İstek tamamlandığında oturumu kapat