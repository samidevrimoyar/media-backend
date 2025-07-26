# routers/words.py
# Kelime dağarcığı yönetimi endpoint'leri

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload # Veritabanı oturumu ve ilişki yükleme için

from database import get_db # Veritabanı oturumu bağımlılığı
from models.user import User # User modelini içe aktarın (ilişki için)
from models.word import Word, WordCreate, WordResponse # Word modeli ve yanıt şemaları
from routers.auth import get_current_user # Kimlik doğrulama bağımlılığı

router = APIRouter(
    prefix="/words", # Tüm endpoint'ler /words ile başlayacak
    tags=["Words"], # Swagger UI'da grup adı
)

@router.post("/", response_model=WordResponse, status_code=status.HTTP_201_CREATED, summary="Add a new word to the vocabulary")
async def create_word(
    word_create: WordCreate, # Yeni kelime verileri (Pydantic modeli)
    db: Session = Depends(get_db), # Veritabanı oturumu
    current_user: User = Depends(get_current_user) # Oturum açmış kullanıcı
):
    """
    Oturum açmış kullanıcı tarafından kelime dağarcığına yeni bir kelime ekler.
    Kelime zaten mevcutsa 409 Conflict hatası döndürür.
    """
    # Kelimenin zaten var olup olmadığını kontrol et
    existing_word = db.query(Word).filter(Word.word == word_create.word).first()
    if existing_word:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Word already exists in the vocabulary."
        )

    # Yeni kelime kaydını oluştur
    new_word = Word(
        word=word_create.word,
        created_by_user_id=current_user.id
    )
    db.add(new_word)
    db.commit()
    db.refresh(new_word)

    # Yanıt modeli için kullanıcı adını ekle
    response_data = WordResponse(
        id=new_word.id,
        word=new_word.word,
        create_date=new_word.create_date,
        created_by_user_id=new_word.created_by_user_id,
        created_by_username=current_user.username # Oluşturan kullanıcı adını ekle
    )
    return response_data

@router.get("/", response_model=List[WordResponse], summary="List all words in the vocabulary (max 100)")
async def list_words(
    skip: int = 0,
    limit: int = 100, # Maksimum 100 kayıt
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Herhangi bir oturum açmış kullanıcı görüntüleyebilir
):
    """
    Kelime dağarcığındaki tüm kelimeleri listeler.
    Kimin eklediğine bakılmaksızın tüm kayıtlara erişilebilir.
    """
    # created_by_user ilişkisini de yükle
    words = db.query(Word).options(joinedload(Word.created_by_user)).offset(skip).limit(limit).all()

    response_words = []
    for word in words:
        word_response = WordResponse(
            id=word.id,
            word=word.word,
            create_date=word.create_date,
            created_by_user_id=word.created_by_user_id,
            created_by_username=word.created_by_user.username if word.created_by_user else None
        )
        response_words.append(word_response)
    return response_words

@router.put("/{word_id}", response_model=WordResponse, summary="Update a word by ID (Only owner can update)")
async def update_word(
    word_id: int,
    word_update: WordCreate, # Yeni kelime değeri
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Oturum açmış kullanıcı
):
    """
    Belirtilen ID'ye sahip bir kelimeyi günceller.
    Sadece kelimenin sahibi güncelleyebilir.
    """
    word_to_update = db.query(Word).options(joinedload(Word.created_by_user)).filter(Word.id == word_id).first()
    if not word_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Word not found")

    # Kelimenin sahibinin kendisi olup olmadığını kontrol et
    if word_to_update.created_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this word."
        )

    # Güncellenmek istenen kelimenin zaten var olup olmadığını kontrol et (farklı bir ID'ye aitse)
    if word_to_update.word != word_update.word: # Eğer kelime değişiyorsa kontrol et
        existing_word = db.query(Word).filter(Word.word == word_update.word).first()
        if existing_word and existing_word.id != word_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="New word value already exists for another entry."
            )

    word_to_update.word = word_update.word
    db.commit()
    db.refresh(word_to_update)

    response_data = WordResponse(
        id=word_to_update.id,
        word=word_to_update.word,
        create_date=word_to_update.create_date,
        created_by_user_id=word_to_update.created_by_user_id,
        created_by_username=word_to_update.created_by_user.username if word_to_update.created_by_user else None
    )
    return response_data

@router.delete("/{word_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a word by ID (Only owner can delete)")
async def delete_word(
    word_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Oturum açmış kullanıcı
):
    """
    Belirtilen ID'ye sahip bir kelimeyi siler.
    Sadece kelimenin sahibi silebilir.
    """
    word_to_delete = db.query(Word).filter(Word.id == word_id).first()
    if not word_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Word not found")

    # Kelimenin sahibinin kendisi olup olmadığını kontrol et
    if word_to_delete.created_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this word."
        )

    db.delete(word_to_delete)
    db.commit()
    return # 204 No Content döndür