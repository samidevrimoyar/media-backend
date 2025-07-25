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

@app.on_event("startup")
async def startup_event():
    """
    Uygulama başladığında çalışacak olay.
    Veritabanı tablolarını oluşturur.
    """
    print("Application startup: Creating database tables if they don't exist...")
    # Veritabanında tanımlı tüm modeller için tabloları oluştur
    # (Eğer tablolar zaten varsa, tekrar oluşturulmazlar)
    Base.metadata.create_all(bind=engine)
    print("Database tables created (or already existed).")

@app.get("/", summary="Root endpoint")
async def root():
    """
    API'nin çalıştığını kontrol etmek için basit bir root endpoint.
    """
    return {"message": "Welcome to the Photo Gallery API!"}