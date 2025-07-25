# routers/photos.py
# Fotoğraf yükleme ve yönetimi endpoint'leri

from typing import List, Optional
from io import BytesIO
from uuid import uuid4 # Benzersiz dosya adları oluşturmak için

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload # Veritabanı oturumu ve ilişki yükleme için

from database import get_db # Veritabanı oturumu bağımlılığı
from models.user import User # User modelini içe aktarın (ilişki için)
from models.photo import Photo, PhotoResponse # Photo modeli ve yanıt şeması
from routers.auth import get_current_user, get_current_admin_user # Kimlik doğrulama bağımlılıkları
from storage import upload_file, get_presigned_url, delete_file # MinIO depolama işlevleri

# Loglama için
import logging
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/photos", # Tüm endpoint'ler /photos ile başlayacak
    tags=["Photos"], # Swagger UI'da grup adı
)

@router.post("/upload", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED, summary="Upload a new photo")
async def upload_photo(
    file: UploadFile = File(...), # Yüklenecek dosya
    db: Session = Depends(get_db), # Veritabanı oturumu
    current_user: User = Depends(get_current_user) # Oturum açmış kullanıcı (sahip)
):
    """
    Kullanıcı tarafından yeni bir fotoğraf yükler.
    Sadece oturum açmış kullanıcılar fotoğraf yükleyebilir.
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed."
        )

    # Benzersiz bir dosya adı oluştur
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    object_name = f"uploads/{current_user.username}/{uuid4()}.{file_extension}" # Örn: uploads/testuser/a1b2c3d4-e5f6-7890-1234-567890abcdef.jpg

    # Dosya içeriğini belleğe oku
    file_content = await file.read()
    file_data_io = BytesIO(file_content)

    # MinIO'ya yükle
    uploaded_object_name = upload_file(file_data_io, object_name, file.content_type)

    if not uploaded_object_name:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload photo to storage."
        )

    # Veritabanına fotoğraf kaydını oluştur
    new_photo = Photo(
        object_name=uploaded_object_name,
        owner_id=current_user.id
    )
    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)

    # Ön-imzalı URL oluştur ve yanıtla
    photo_url = get_presigned_url(new_photo.object_name)
    if not photo_url:
        logger.error(f"Failed to generate presigned URL for {new_photo.object_name} after successful upload.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Photo uploaded but failed to generate access URL."
        )

    # Pydantic yanıt modelini, tüm gerekli alanları manuel olarak sağlayarak oluşturun.
    # new_photo'yu doğrudan PhotoResponse'a vermek yerine, alanları eşleştirelim.
    response_data = PhotoResponse(
        id=new_photo.id,
        object_name=new_photo.object_name,
        url=photo_url, # URL'i burada sağlıyoruz
        uploaded_at=new_photo.uploaded_at,
        owner_id=new_photo.owner_id,
        owner_username=current_user.username # Sahip kullanıcı adını ekle
    )

    return response_data

@router.get("/", response_model=List[PhotoResponse], summary="List all photos or photos by a specific user")
async def list_photos(
    owner_id: Optional[int] = Query(None, description="Filter photos by owner ID"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Oturum açmış her kullanıcı bu listeye erişebilir
):
    """
    Sistemdeki tüm fotoğrafları listeler.
    Eğer `owner_id` sağlanırsa, sadece belirli bir kullanıcıya ait fotoğrafları listeler.
    Admin olmayan kullanıcılar sadece kendi fotoğraflarını listeleyebilir.
    """
    query = db.query(Photo).options(joinedload(Photo.owner)) # owner ilişkisini de yükle

    if owner_id:
        # Admin olmayan kullanıcılar sadece kendi fotoğraflarını isteyebilir
        if not current_user.is_admin and owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own photos or list all photos as an admin."
            )
        query = query.filter(Photo.owner_id == owner_id)
    else:
        # Admin olmayan kullanıcılar sadece kendi fotoğraflarını görür
        if not current_user.is_admin:
            query = query.filter(Photo.owner_id == current_user.id)

    photos = query.offset(skip).limit(limit).all()

    response_photos = []
    for photo in photos:
        photo_url = get_presigned_url(photo.object_name)
        if photo_url:
            # PhotoResponse'ı manuel olarak doldur
            photo_response = PhotoResponse(
                id=photo.id,
                object_name=photo.object_name,
                url=photo_url,
                uploaded_at=photo.uploaded_at,
                owner_id=photo.owner_id,
                owner_username=photo.owner.username if photo.owner else None
            )
            response_photos.append(photo_response)
        else:
            logger.warning(f"Could not generate URL for photo ID {photo.id}. Skipping.")
    return response_photos

@router.get("/{photo_id}", response_model=PhotoResponse, summary="Get details of a specific photo")
async def get_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Oturum açmış her kullanıcı erişebilir
):
    """
    Belirli bir fotoğrafın detaylarını döndürür.
    Sadece fotoğrafın sahibi veya bir admin erişebilir.
    """
    photo = db.query(Photo).options(joinedload(Photo.owner)).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    # Fotoğrafın sahibinin kendisi veya admin mi olduğunu kontrol et
    if photo.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this photo."
        )

    photo_url = get_presigned_url(photo.object_name)
    if not photo_url:
        logger.error(f"Failed to generate presigned URL for photo ID {photo.id}.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate URL for photo."
        )

    # PhotoResponse'ı manuel olarak doldur
    response_data = PhotoResponse(
        id=photo.id,
        object_name=photo.object_name,
        url=photo_url,
        uploaded_at=photo.uploaded_at,
        owner_id=photo.owner_id,
        owner_username=photo.owner.username if photo.owner else None
    )

    return response_data

@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a photo by ID (Owner or Admin only)")
async def delete_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Oturum açmış kullanıcı
):
    """
    Belirtilen ID'ye sahip bir fotoğrafı siler.
    Sadece fotoğrafın sahibi veya bir admin silebilir.
    """
    photo_to_delete = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    # Fotoğrafın sahibi veya admin mi olduğunu kontrol et
    if photo_to_delete.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this photo."
        )

    # MinIO'dan dosyayı sil
    if not delete_file(photo_to_delete.object_name):
        logger.error(f"Failed to delete file {photo_to_delete.object_name} from MinIO.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete photo from storage."
        )

    # Veritabanından kaydı sil
    db.delete(photo_to_delete)
    db.commit()
    return # 204 No Content döndür