# main.py
# FastAPI uygulamasının ana giriş noktası

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # CORS yönetimi için

from database import Base, engine # Veritabanı modelimizin temeli ve motoru
# Tüm SQLAlchemy modellerini içe aktarın ki Base.metadata.create_all onları tanısın
import models.user # User modelini içe aktarır
import models.photo # Photo modelini içe aktarır

# Router'ları içe aktarın
from routers import auth, users, photos

# MinIO istemcisini başlatmak ve bucket oluşturmak için storage modülünü import edin
# s3_client'ı da global olarak erişmek için import etmeliyiz.
from storage import initialize_minio_client, create_bucket_if_not_exists, s3_client
import logging # Loglama için
import os # Ortam değişkenleri için (MINIO_BUCKET_NAME için)

logger = logging.getLogger(__name__) # main.py için bir logger oluştur

app = FastAPI(
    title="Photo Gallery API", # API başlığı
    description="A simple photo gallery API with user authentication and photo management.", # API açıklaması
    version="1.0.0", # API versiyonu
)

# CORS (Cross-Origin Resource Sharing) ayarları
origins = [
    "http://localhost",
    "http://localhost:3000",
    # "https://yourfrontenddomain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router'ları ana FastAPI uygulamasına dahil et
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(photos.router)

@app.on_event("startup")
async def startup_event():
    """
    Uygulama başladığında çalışacak olay.
    Veritabanı tablolarını oluşturur ve MinIO istemcisini başlatır/bucket'ı kontrol eder.
    """
    logger.info("Application startup: Creating database tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created (or already existed).")

    logger.info("Application startup: Initializing MinIO client and ensuring bucket...")
    initialize_minio_client() # MinIO istemcisini başlatma fonksiyonunu çağır

    if s3_client is None:
        logger.critical("MinIO client failed to initialize. File upload/management will not function.")
        # Burada uygulamanın tamamen durmasını isterseniz raise RuntimeError("...") kullanabilirsiniz.
    else:
        logger.info("MinIO client successfully initialized. Checking/creating bucket...")
        bucket_name = os.getenv("MINIO_BUCKET_NAME")
        if bucket_name:
            if not create_bucket_if_not_exists(): # Bucket oluşturma/kontrol fonksiyonunu çağır
                logger.critical(f"Failed to ensure MinIO bucket '{bucket_name}' exists. File operations may fail.")
            else:
                logger.info(f"MinIO bucket '{bucket_name}' confirmed.")
        else:
            logger.critical("MINIO_BUCKET_NAME environment variable is not set. Cannot ensure bucket exists.")


@app.get("/", summary="Root endpoint")
async def root():
    """
    API'nin çalıştığını kontrol etmek için basit bir root endpoint.
    """
    return {"message": "Welcome to the Photo Gallery API!"}