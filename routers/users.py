# routers/users.py
# Kullanıcı yönetimi endpoint'leri

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session # Veritabanı oturumu için

from database import get_db # Veritabanı oturumu bağımlılığı
from models.user import User, UserResponse # User modeli ve yanıt şeması
# Kimlik doğrulama bağımlılıklarını auth router'ından içe aktarın
from routers.auth import get_current_user, get_current_admin_user

router = APIRouter(
    prefix="/users", # Tüm endpoint'ler /users ile başlayacak
    tags=["Users"], # Swagger UI'da grup adı
)

@router.get("/me", response_model=UserResponse, summary="Get current authenticated user's details")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Kimliği doğrulanmış (oturum açmış) kullanıcının detaylarını döndürür.
    """
    return current_user # get_current_user zaten User objesini döndürüyor

@router.get("/{user_id}", response_model=UserResponse, summary="Get details of a specific user by ID (Admin only)")
async def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user) # Sadece adminler erişebilir
):
    """
    Belirli bir kullanıcı ID'sine sahip kullanıcının detaylarını döndürür.
    Sadece yönetici (admin) yetkisine sahip kullanıcılar erişebilir.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.get("/", response_model=List[UserResponse], summary="List all users (Admin only)")
async def read_users(
    skip: int = 0, # Sayfalama için kaç kullanıcıyı atlayacağımızı belirler
    limit: int = 100, # Sayfalama için maksimum kaç kullanıcı döndüreceğimizi belirler
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user) # Sadece adminler erişebilir
):
    """
    Sistemdeki tüm kullanıcıları listeler.
    Sadece yönetici (admin) yetkisine sahip kullanıcılar erişebilir.
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a user by ID (Admin only)")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user) # Sadece adminler silebilir
):
    """
    Belirtilen ID'ye sahip bir kullanıcıyı sistemden siler.
    Sadece yönetici (admin) yetkisine sahip kullanıcılar erişebilir.
    """
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if user_to_delete is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Kendi kendini silme engeli (isteğe bağlı ama iyi bir pratik)
    if user_to_delete.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own admin account directly through this endpoint."
        )

    db.delete(user_to_delete)
    db.commit()
    # 204 No Content döndürdüğümüz için herhangi bir yanıt modeli belirtmiyoruz.
    # FastAPI otomatik olarak uygun HTTP yanıtını oluşturur.
    return