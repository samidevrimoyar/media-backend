# main.py
# FastAPI uygulamasının ana giriş noktası

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # CORS yönetimi için

from database import Base, engine # Veritabanı modelimizin temeli ve motoru
# Tüm SQLAlchemy modellerini içe aktarın ki Base.metadata.create_all onları tanısın
import models.user # User modelini içe aktarır
import models.photo # Photo modelini içe aktarır
import models.word # Word modelini içe aktarır

# Router'ları içe aktarın
from routers import auth, users, photos, words

# MinIO istemcisini başlatmak ve bucket oluşturmak için storage modülünü import edin
# s3_client'ı artık doğrudan import ETMİYORUZ. Onun yerine get_s3_client kullanacağız.
from storage import initialize_minio_client, create_bucket_if_not_exists, get_s3_client
import logging # Loglama için
import os # Ortam değişkenleri için (MINIO_BUCKET_NAME için)

logger = logging.getLogger(__name__) # main.py için bir logger oluştur

app = FastAPI(
    title="Photo Gallery API", # API başlığı
    description="A simple photo gallery API with user authentication and photo management.", # API açıklaması
    version="1.0.0", # API versiyonu
)

# CORS (Cross-Origin Resource Sharing) ayarları
# Frontend'inizin veya diğer domain'lerden gelen isteklerin bu API'ye erişmesine izin verir.
# Güvenlik amacıyla, production ortamında 'allow_origins' listesini kısıtlamalısınız.
origins = [
    "http://localhost", # Geliştirme ortamı için localhost'a izin ver
    "http://localhost:3000", # React/Vue/Angular gibi frontend uygulamaları için
    # Eğer bir domain'iniz varsa, buraya ekleyin:
    # "https://yourfrontenddomain.com",
    # "https://api.yourbackenddomain.com", # Eğer API'niz de farklı bir subdomain'den çalışıyorsa
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # İzin verilen kaynaklar
    allow_credentials=True, # Çerezlere izin ver (kimlik doğrulama için gerekli olabilir)
    allow_methods=["*"], # Tüm HTTP metotlarına (GET, POST, PUT, DELETE, vb.) izin ver
    allow_headers=["*"], # Tüm başlıklara izin ver
)

# Router'ları ana FastAPI uygulamasına dahil et
app.include_router(auth.router) # Kimlik doğrulama router'ı
app.include_router(users.router) # Kullanıcı router'ı
app.include_router(photos.router) # Fotoğraf router'ı
app.include_router(words.router) # Kelime router'ı

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

    # Şimdi s3_client'ın durumunu kontrol etmek için get_s3_client() kullanıyoruz.
    if get_s3_client() is None:
        logger.critical("MinIO client failed to initialize. File upload/management will not function.")
        # Uygulamanın MinIO olmadan çalışmasını istemiyorsanız burada bir hata fırlatabilirsiniz:
        # raise RuntimeError("MinIO client initialization failed.")
    else:
        logger.info("MinIO client successfully initialized. Checking/creating bucket...")
        bucket_name = os.getenv("MINIO_BUCKET_NAME")
        if bucket_name:
            # create_bucket_if_not_exists artık içeride get_s3_client() kullandığı için
            # burada ekstra bir parametre geçmeye gerek yok.
            if not create_bucket_if_not_exists():
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