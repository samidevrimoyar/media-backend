# models/photo.py
# Fotoğraf veritabanı modeli (SQLAlchemy) ve Pydantic şemaları

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship # İlişkileri tanımlamak için
from pydantic import BaseModel, HttpUrl # Pydantic modelleri ve URL doğrulama için
from datetime import datetime # Tarih ve saat objeleri için
from typing import Optional # Tip ipuçları için

from database import Base # Veritabanı modelimizin temel sınıfı

# SQLAlchemy Photo modeli (Veritabanı tablosu için)
class Photo(Base):
    __tablename__ = "photos" # Veritabanındaki tablo adı

    id = Column(Integer, primary_key=True, index=True) # Benzersiz ID, birincil anahtar
    # MinIO'daki objenin adı (örneğin: 'uploads/abc-123.jpg')
    object_name = Column(String, unique=True, index=True, nullable=False)
    # Fotoğrafın URL'i (genellikle presigned URL veya CDN URL'i olarak oluşturulur)
    # Veritabanında sadece MinIO'daki objenin adını saklayıp URL'i dinamik olarak oluşturmak daha iyidir.
    # Ancak basitlik adına burada saklayabiliriz veya sadece object_name ile yetinebiliriz.
    # Şimdilik object_name'i saklayıp URL'i backend'de oluşturacağız.
    # Eğer isterseniz, burada doğrudan bir 'url' sütunu da tutabilirsiniz.
    # url = Column(String, nullable=False)

    uploaded_at = Column(DateTime, default=datetime.utcnow) # Yükleme tarihi ve saati (UTC)
    owner_id = Column(Integer, ForeignKey("users.id")) # Fotoğrafın sahibi olan kullanıcının ID'si

    # User modeli ile ilişki
    # 'User' modeline bir referans oluşturur ve 'owner' adıyla erişilmesini sağlar.
    owner = relationship("User", back_populates="photos")

    def __repr__(self):
        return f"<Photo(id={self.id}, object_name='{self.object_name}', owner_id={self.owner_id})>"

# Pydantic Şemaları (API istek ve yanıtları için)

# Fotoğraf yükleme/oluşturma şeması
# FastAPI'de dosya yükleme ayrı ele alınacağı için burada doğrudan dosya içeriği değil,
# veritabanına kaydedilecek bilgiler yer alacak.
class PhotoCreate(BaseModel):
    # API'de doğrudan bu model kullanılmayacak, UploadFile objesi kullanılacak.
    # Bu model, genellikle fotoğraf yüklendikten sonra DB'ye kaydedilecek meta verileri temsil eder.
    # Şu an için dosya yükleme sırasında istemciden özel bir veri beklemiyoruz,
    # Sadece fotoğrafın kendisi ve kullanıcı ID'si yeterli olacak.
    # Eğer açıklama, etiket gibi ek veriler olsaydı buraya eklenecekti.
    pass # Şimdilik boş bırakıyoruz, çünkü temel olarak sadece dosya yüklenecek ve DB kaydı backend'de oluşturulacak.

# API yanıtı için fotoğraf şeması (public URL ile)
class PhotoResponse(BaseModel):
    id: int
    object_name: str # MinIO'daki dosya adı
    # Frontend'in kullanacağı doğrudan erişilebilir URL (presigned URL olabilir)
    # Bu alan, API yanıtında dinamik olarak doldurulacaktır.
    url: HttpUrl # URL tipi Pydantic tarafından doğrulanır
    uploaded_at: datetime
    owner_id: int
    # İsteğe bağlı olarak, fotoğraf sahibinin kullanıcı adını da dahil edebiliriz
    owner_username: Optional[str] = None # 'routers/photos.py' içinde doldurulacak

    class Config:
        from_attributes = True # SQLAlchemy modellerinden Pydantic modellerine dönüşüm için
        json_schema_extra = {
            "example": {
                "id": 1,
                "object_name": "uploads/user1/my_image_123.jpg",
                "url": "https://minio.superisi.net/photo-gallery/uploads/user1/my_image_123.jpg?X-Amz...",
                "uploaded_at": "2023-10-27T10:30:00.000000",
                "owner_id": 1,
                "owner_username": "testuser"
            }
        }