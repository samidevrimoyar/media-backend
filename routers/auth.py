# routers/auth.py
# Kullanıcı kimlik doğrulama (kayıt, giriş, JWT oluşturma) ve yetkilendirme bağımlılıkları

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext # Şifre hashleme için
from jose import JWTError, jwt # JWT (JSON Web Token) işlemleri için

from database import get_db # Veritabanı oturumu almak için
from models.user import User, UserCreate, UserLogin, Token, TokenData, UserResponse # Kullanıcı modelleri ve Pydantic şemaları

router = APIRouter(
    prefix="/auth", # Tüm endpoint'ler /auth ile başlayacak
    tags=["Authentication"], # Swagger UI'da grup adı
)

# Şifre hashleme için CryptContext
# schemes parametresi hashleme algoritmasını belirtir (bcrypt kullanıyoruz)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Ortam değişkeninden gizli anahtarı al
# Bu anahtar, JWT tokenlarını imzalamak ve doğrulamak için kullanılır.
SECRET_KEY = os.getenv("SECRET_KEY")
if SECRET_KEY is None:
    raise Exception("SECRET_KEY environment variable not set. Please add it to your .env file.")

ALGORITHM = "HS256" # JWT imzalama algoritması
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Erişim tokenının geçerlilik süresi (dakika)

# OAuth2 şifre taşıyıcısı (Bearer token)
# tokenUrl: Swagger UI'ın "Authorize" penceresinde kullanıcı adı/şifre alanlarını göstermesi için gerekli.
# Bu URL, token almak için POST isteği gönderilecek endpoint'i belirtir.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Yardımcı Fonksiyonlar

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Düz metin şifreyi, hashlenmiş şifre ile doğrular.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Verilen şifrenin hash'ini oluşturur.
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Belirtilen verilerle bir JWT erişim tokenı oluşturur.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire}) # Token'ın son kullanma tarihini ekle
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM) # Token'ı imzala
    return encoded_jwt

# Kimlik Doğrulama Endpoint'leri

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user")
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Yeni bir kullanıcı kaydı oluşturur.
    """
    # Kullanıcı adının zaten var olup olmadığını kontrol et
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered."
        )

    # Şifreyi hash'le
    hashed_password = get_password_hash(user.password)

    # Yeni User objesini oluştur
    new_user = User(
        username=user.username,
        hashed_password=hashed_password,
        is_admin=user.is_admin # is_admin alanı UserCreate şemasından geliyor
    )
    db.add(new_user) # Veritabanına ekle
    db.commit() # Değişiklikleri kaydet
    db.refresh(new_user) # Oluşturulan objeyi yenile (ID gibi bilgileri almak için)

    return new_user

@router.post("/login", response_model=Token, summary="Login and get an access token")
async def login_for_access_token(
    username: str = Form(), # Kullanıcı adı form verisinden
    password: str = Form(),  # Şifre form verisinden
    db: Session = Depends(get_db)
):
    """
    Kullanıcı adı ve şifre ile giriş yapar ve bir JWT erişim tokenı döndürür.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # JWT erişim tokenı oluştur
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "is_admin": user.is_admin}, # is_admin bilgisini token'a ekle
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Kimlik Doğrulama Bağımlılıkları (API Yollarını Korumak İçin)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    JWT tokenını doğrular ve mevcut aktif kullanıcı objesini döndürür.
    Token geçerli olmazsa HTTP 401 hatası fırlatır.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Token'ı çöz ve kullanıcı adını (sub) ile admin durumunu al
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        is_admin: bool = payload.get("is_admin", False) # is_admin yoksa varsayılan false
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username) # TokenData'yı sadece username ile kullanabiliriz
    except JWTError:
        raise credentials_exception # JWT çözme hatası varsa hata fırlat

    # Kullanıcıyı veritabanından bul
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception # Kullanıcı veritabanında yoksa hata fırlat
    return user # Doğrulanmış User objesini döndür (FastAPI'nin daha sonra kullanabilmesi için)

async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Mevcut kullanıcının admin olup olmadığını kontrol eder.
    Admin değilse HTTP 403 hatası fırlatır.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    return current_user # Admin kullanıcı ise objeyi döndür