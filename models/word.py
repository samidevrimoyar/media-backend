# models/word.py
# Kelime veritabanı modeli (SQLAlchemy) ve Pydantic şemaları

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship # İlişkileri tanımlamak için
from pydantic import BaseModel, EmailStr # Pydantic modelleri ve e-posta doğrulama için
from typing import List, Optional # Tip ipuçları için
import DateTime

from database import Base # Veritabanı modelimizin temel sınıfı

# SQLAlchemy User modeli (Veritabanı tablosu için)
class Word(Base):
    __tablename__ = "words" # Veritabanındaki tablo adı

    word_id = Column(Integer, primary_key=True, index=True) # Benzersiz ID, birincil anahtar
    word_text = Column(String(15), unique=True, index=True, nullable=False) # Kelime, benzersiz, boş olamaz
    create_date = Column(DateTime, default=datetime.utcnow)
    editor = Column(Integer, ForeignKey("users.id"), nullable=False)

    def __repr__(self):
        return f"<Word(word_id={self.word_id}, word='{self.word}', editor='{self.editor}',create_date={self.create_date})>"

# Pydantic Şemaları (API istek ve yanıtları için)

# Kelime oluşturma isteği için şema (Client'tan gelen veri)
class WordCreate(PydanticBaseModel):
    """
    Yeni bir kelime kaydı oluşturmak için kullanılan veri şeması.
    Client'ın göndereceği verileri tanımlar.
    """
    word_text: str # Zorunlu: Kelimenin metni

    class Config:
        json_schema_extra = {
            "example": {
                "word_text": "testword"
            }
        }

class WordUpdate(PydanticBaseModel):
    """
    Mevcut bir kelime kaydını güncellemek için kullanılan veri şeması.
    Alanlar Optional olduğu için sadece gönderilen alanlar güncellenir.
    """
    word_text: Optional[str] = None # İsteğe bağlı: Kelimenin metni

    class Config:
        json_schema_extra = {
            "example": {
                "word_id": "1",
                "word_text": "testword"
            }
        }

class WordResponse(PydanticBaseModel):
    """
    API'dan kelime kaydı döndürülürken kullanılan veri şeması.
    Veritabanındaki tüm ilgili alanları içerir.
    """
    word_id: int # Kelime ID'si
    word_text: str # Kelimenin metni
    editor: int # Kelimeyi ekleyen kullanıcının ID'si
    created_at: datetime # Oluşturulma zamanı (BaseModel'den gelir)

    class Config:
        json_schema_extra = {
            "example": {
                "word_id": "1",
                "word_text": "testword",
                "create_date": "23/08/2006",
                "editor": "1"
            }
        }
