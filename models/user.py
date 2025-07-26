# models/user.py
# Kullanıcı veritabanı modeli (SQLAlchemy) ve Pydantic şemaları

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship # İlişkileri tanımlamak için
from pydantic import BaseModel, EmailStr # Pydantic modelleri ve e-posta doğrulama için
from typing import List, Optional # Tip ipuçları için

from database import Base # Veritabanı modelimizin temel sınıfı

# SQLAlchemy User modeli (Veritabanı tablosu için)
class User(Base):
    __tablename__ = "users" # Veritabanındaki tablo adı

    id = Column(Integer, primary_key=True, index=True) # Benzersiz ID, birincil anahtar
    username = Column(String, unique=True, index=True, nullable=False) # Kullanıcı adı, benzersiz, boş olamaz
    hashed_password = Column(String, nullable=False) # Hashlenmiş şifre, boş olamaz
    is_admin = Column(Boolean, default=False) # Yönetici mi? Varsayılan: Hayır

    # Kullanıcının sahip olduğu fotoğraflarla ilişki
    # 'Photo' modelini henüz tanımlamadık, bu yüzden bir string olarak referans veriyoruz.
    # uselist=True: varsayılan, bir kullanıcı birden fazla fotoğrafa sahip olabilir.
    photos = relationship("Photo", back_populates="owner")
    words = relationship("Word", back_populates="created_by_user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', is_admin={self.is_admin})>"

# Pydantic Şemaları (API istek ve yanıtları için)

# Temel kullanıcı şeması
class UserBase(BaseModel):
    username: str # Kullanıcı adı

# Kullanıcı oluşturma şeması (kayıt için)
class UserCreate(UserBase):
    password: str # Şifre (hashlenmeden önce)
    is_admin: Optional[bool] = False # Admin olarak oluşturma seçeneği, varsayılan false

    class Config:
        json_schema_extra = {
            "example": {
                "username": "testuser",
                "password": "securepassword123",
                "is_admin": False
            }
        }

# Kullanıcı girişi şeması
class UserLogin(UserBase):
    password: str # Şifre

    class Config:
        json_schema_extra = {
            "example": {
                "username": "testuser",
                "password": "securepassword123"
            }
        }

# API yanıtı için kullanıcı şeması (şifre hash'ini göstermez)
class UserResponse(UserBase):
    id: int # Kullanıcı ID'si
    is_admin: bool # Yönetici durumu

    class Config:
        from_attributes = True # SQLAlchemy modellerinden Pydantic modellerine dönüşüm için (eski adıyla orm_mode = True)
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "testuser",
                "is_admin": False
            }
        }

# Token için Pydantic şemaları
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None