# routers/words.py
# Kelime yönetimi endpoint'leri

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session # Veritabanı oturumu için

from database import get_db # Veritabanı oturumu bağımlılığı
from models.word import Word, WordResponse # Word modeli ve yanıt şeması
# Kimlik doğrulama bağımlılıklarını auth router'ından içe aktarın
from routers.auth import get_current_user, get_current_admin_user

router = APIRouter(
    prefix="/words", # Tüm endpoint'ler /words ile başlayacak
    tags=["Words"], # Swagger UI'da grup adı
)


# Yeni kelime oluşturma endpoint'i
@router.post("/", response_model=WordResponse, status_code=status.HTTP_201_CREATED, summary="Create a new word entry")
async def create_word(
    word: WordCreate, # Kelime oluşturma şeması (Pydantic modeli)
    db: Session = Depends(get_db), # Veritabanı oturumu bağımlılığı
    current_user: User = Depends(get_current_user) # Mevcut kullanıcı bağımlılığı (kimlik doğrulama)
):
    """
    Yeni bir kelime girişi oluşturur. Sadece oturum açmış kullanıcılar kelime ekleyebilir.
    """
    # Kelimenin zaten var olup olmadığını kontrol et
    existing_word = db.query(Word).filter(Word.word_text == word.word_text).first()
    if existing_word:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Word with this text already exists."
        )

    # Yeni Word veritabanı objesini oluştur
    db_word = Word(
        word_text=word.word_text,
        create_date=word.create_date,
        editor=current_user.id # Kelimeyi oluşturan kullanıcının ID'si
    )
    db.add(db_word) # Objeyi oturuma ekle
    db.commit() # Değişiklikleri veritabanına kaydet
    db.refresh(db_word) # Oluşturulan objeyi güncel verilerle yenile
    return db_word # Oluşturulan kelime objesini döndür (WordResponse şemasına göre dönüştürülür)

@router.get("/", response_model=List[WordResponse], summary="Retrieve all word entries")
async def get_words(
    db: Session = Depends(get_db), # Veritabanı oturumu bağımlılığı
    skip: int = Query(0, ge=0), # Listelemede atlanacak kayıt sayısı (varsayılan 0, negatif olamaz)
    limit: int = Query(100, ge=1, le=100) # Listelenecek maksimum kayıt sayısı (varsayılan 100, 1-100 arası)
):
    """
    Tüm sözlük kelimelerini listeler. Sayfalama (pagination) destekler.
    """
    # Veritabanından kelimeleri al (ilişkili kullanıcı verisini de yükleyerek)
    words = db.query(Word).options(joinedload(Word.creator)).offset(skip).limit(limit).all()
    return words # Kelime listesini döndür

@router.get("/{word_id}", response_model=WordResponse, summary="Retrieve a single word entry by ID")
async def get_word(
    word_id: int, # URL'den gelen kelime ID'si
    db: Session = Depends(get_db) # Veritabanı oturumu bağımlılığı
):
    """
    Belirtilen ID'ye sahip sözlük kelimesini döndürür.
    """
    # Kelimeyi veritabanından ID'ye göre bul
    word = db.query(Word).options(joinedload(Word.creator)).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Word not found."
        )
    return word # Bulunan kelimeyi döndür

@router.put("/{word_id}", response_model=WordResponse, summary="Update an existing word entry")
async def update_word(
    word_id: int, # URL'den gelen kelime ID'si
    word_update: WordUpdate, # Kelime güncelleme şeması (Pydantic modeli)
    db: Session = Depends(get_db), # Veritabanı oturumu bağımlılığı
    current_user: User = Depends(get_current_user) # Mevcut kullanıcı bağımlılığı
):
    """
    Mevcut bir kelimeyi günceller. Sadece kelimeyi oluşturan kullanıcı veya bir admin güncelleyebilir.
    """
    # Kelimeyi veritabanından bul
    db_word = db.query(Word).filter(Word.id == word_id).first()
    if not db_word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Word not found."
        )

    # Yetkilendirme kontrolü: Kelimeyi oluşturan mı yoksa admin mi?
    if db_word.editor != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this word. You must be the creator or an admin."
        )

    # Güncellenecek alanları belirle ve uygula
    update_data = word_update.model_dump(exclude_unset=True) # Sadece gönderilen alanları al
    for key, value in update_data.items():
        setattr(db_word, key, value) # Model objesinin ilgili alanını güncelle

    db.add(db_word) # Değişiklikleri kaydetmek için tekrar ekle (bazı durumlarda gerekli)
    db.commit() # Değişiklikleri veritabanına kaydet
    db.refresh(db_word) # Güncellenen objeyi yenile
    return db_word # Güncellenen kelimeyi döndür
