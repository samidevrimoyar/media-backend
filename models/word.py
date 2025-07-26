# models/word.py
# Kelime veritabanı modeli (SQLAlchemy) ve Pydantic şemaları

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship # İlişkileri tanımlamak için
from pydantic import BaseModel # Pydantic modelleri için
from datetime import datetime # Tarih ve saat objeleri için
from typing import Optional # Tip ipuçları için

from database import Base # Veritabanı modelimizin temel sınıfı

# SQLAlchemy Word modeli (Veritabanı tablosu için)
class Word(Base):
    __tablename__ = "words" # Veritabanındaki tablo adı

    id = Column(Integer, primary_key=True, index=True, name="word_id") # Benzersiz ID, birincil anahtar
    word = Column(String(15), unique=True, index=True, nullable=False) # Kelime, benzersiz ve boş olamaz
    create_date = Column(DateTime, default=datetime.utcnow) # Oluşturulma tarihi ve saati (UTC)
    created_by_user_id = Column(Integer, ForeignKey("users.id")) # Kelimeyi oluşturan kullanıcının ID'si

    # User modeli ile ilişki
    # 'User' modeline bir referans oluşturur ve 'created_by_user' adıyla erişilmesini sağlar.
    created_by_user = relationship("User", back_populates="words")

    def __repr__(self):
        return f"<Word(id={self.id}, word='{self.word}', created_by_user_id={self.created_by_user_id})>"

# Pydantic Şemaları (API istek ve yanıtları için)

# Yeni kelime oluşturma isteği şeması
class WordCreate(BaseModel):
    word: str

    class Config:
        json_schema_extra = {
            "example": {
                "word": "Merhaba"
            }
        }

# API yanıtı için kelime şeması
class WordResponse(BaseModel):
    id: int # word_id'ye karşılık gelir
    word: str
    create_date: datetime
    created_by_user_id: int
    created_by_username: Optional[str] = None # Kelimeyi oluşturan kullanıcının kullanıcı adı

    class Config:
        from_attributes = True # SQLAlchemy modellerinden Pydantic modellerine dönüşüm için
        json_schema_extra = {
            "example": {
                "id": 1,
                "word": "Elma",
                "create_date": "2023-10-27T10:30:00.000000",
                "created_by_user_id": 1,
                "created_by_username": "testuser"
            }
        }