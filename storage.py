# storage.py
# MinIO (S3 uyumlu) depolama bağlantısı ve fotoğraf yönetimi işlevleri

import os
from io import BytesIO # Dosya verilerini bellekte tutmak için
from typing import Optional # Tip ipuçları için
from dotenv import load_dotenv # .env dosyasını yüklemek için
import boto3 # AWS SDK, S3 uyumlu MinIO ile etkileşim için
from botocore.exceptions import ClientError # Boto3 istemci hatalarını yakalamak için
import logging # Loglama için

# .env dosyasını yükle
load_dotenv()

# Ortam değişkenlerinden MinIO ayarlarını al
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT") # örn: minio:9000
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")

# Loglama ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MinIO istemcisini global olarak tanımlıyoruz, başlatma fonksiyonunda değeri atanacak
s3_client = None

def get_s3_client():
    """
    Başlatılmış MinIO S3 istemcisini döndürür.
    İstemci henüz başlatılmadıysa None döndürür.
    """
    return s3_client

def initialize_minio_client():
    """
    MinIO istemcisini ortam değişkenlerinden gelen bilgilerle başlatır.
    Başarılı olursa global s3_client değişkenini ayarlar.
    """
    global s3_client # global s3_client değişkenini değiştiriyoruz
    logger.info("Attempting to initialize MinIO client...")
    logger.info(f"MINIO_ENDPOINT: {MINIO_ENDPOINT}")
    logger.info(f"MINIO_ROOT_USER: {MINIO_ROOT_USER}")
    # logger.info(f"MINIO_ROOT_PASSWORD: {MINIO_ROOT_PASSWORD}") # Güvenlik nedeniyle şifreyi loglamayın
    logger.info(f"MINIO_BUCKET_NAME: {MINIO_BUCKET_NAME}")

    if not all([MINIO_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, MINIO_BUCKET_NAME]):
        logger.critical("MinIO environment variables are NOT fully set. Cannot initialize client.")
        s3_client = None # Hata durumunda s3_client'ı None olarak bırak
        return

    try:
        # boto3 istemcisini oluştur
        temp_s3_client = boto3.client(
            's3',
            endpoint_url=f"http://{MINIO_ENDPOINT}", # Docker içinden erişim için http://minio:9000 gibi
            aws_access_key_id=MINIO_ROOT_USER,
            aws_secret_access_key=MINIO_ROOT_PASSWORD,
            region_name='us-east-1' # MinIO için bölge adı önemli değil, bir placeholder
        )
        # İstemci başarılı bir şekilde oluşturulduktan sonra bir test işlemi yapalım
        temp_s3_client.list_buckets() # Bu, bağlantının çalışıp çalışmadığını test eder
        s3_client = temp_s3_client # Test başarılıysa global s3_client'a ata
        logger.info("MinIO client initialized successfully and connected to MinIO server.")
    except Exception as e:
        logger.critical(f"FATAL ERROR: MinIO client initialization failed: {e}")
        s3_client = None

def create_bucket_if_not_exists():
    """
    Belirtilen bucket'ın (kova) MinIO'da varlığını kontrol eder, yoksa oluşturur.
    """
    current_s3_client = get_s3_client() # Güncel istemciyi get_s3_client() üzerinden al
    logger.info(f"Attempting to check/create bucket: {MINIO_BUCKET_NAME}") # Yeni debug log
    if current_s3_client is None:
        logger.error("MinIO client is not initialized within storage.py for bucket operation.")
        return False
    try:
        current_s3_client.head_bucket(Bucket=MINIO_BUCKET_NAME) # Bucket'ın varlığını kontrol et
        logger.info(f"Bucket '{MINIO_BUCKET_NAME}' already exists.")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        logger.warning(f"Bucket '{MINIO_BUCKET_NAME}' does not exist or access error: {error_code}. Attempting to create.") # Yeni debug log
        if error_code == '404' or error_code == 'NoSuchBucket': # Bucket bulunamadı hatası
            try:
                current_s3_client.create_bucket(Bucket=MINIO_BUCKET_NAME)
                logger.info(f"Bucket '{MINIO_BUCKET_NAME}' created successfully.")
            except ClientError as ce:
                logger.critical(f"FATAL ERROR: Error creating bucket '{MINIO_BUCKET_NAME}': {ce}") # Daha kritik log seviyesi
                return False
        else: # Diğer hatalar
            logger.critical(f"FATAL ERROR: Error checking bucket '{MINIO_BUCKET_NAME}': {e}") # Daha kritik log seviyesi
            return False
    return True

def upload_file(file_data: BytesIO, object_name: str, content_type: str) -> Optional[str]:
    """
    MinIO'ya dosya yükler. Başarılı olursa dosyanın MinIO'daki adını (object_name) döndürür.
    """
    current_s3_client = get_s3_client() # Güncel istemciyi get_s3_client() üzerinden al
    if current_s3_client is None:
        logger.error("MinIO client is not initialized. Cannot upload file.")
        return None
    try:
        current_s3_client.put_object(
            Bucket=MINIO_BUCKET_NAME,
            Key=object_name, # MinIO'daki dosya yolu/adı (örn: 'fotoğraflar/resim.jpg')
            Body=file_data, # Yüklenecek dosya verisi (BytesIO objesi)
            ContentType=content_type # Dosyanın MIME tipi (örn: 'image/jpeg')
        )
        logger.info(f"File '{object_name}' uploaded successfully to bucket '{MINIO_BUCKET_NAME}'.")
        return object_name
    except ClientError as e:
        logger.error(f"Error uploading file '{object_name}': {e}")
        return None

def get_presigned_url(object_name: str, expiration: int = 3600) -> Optional[str]:
    """
    MinIO'daki bir obje için geçici olarak geçerli, ön-imzalı (presigned) bir URL oluşturur.
    Varsayılan olarak 1 saat (3600 saniye) geçerlidir.
    """
    current_s3_client = get_s3_client() # Güncel istemciyi get_s3_client() üzerinden al
    if current_s3_client is None:
        logger.error("MinIO client is not initialized. Cannot get presigned URL.")
        return None
    try:
        url = current_s3_client.generate_presigned_url(
            'get_object', # Alınacak objeler için URL
            Params={'Bucket': MINIO_BUCKET_NAME, 'Key': object_name},
            ExpiresIn=expiration # URL'nin geçerlilik süresi (saniye)
        )
        logger.info(f"Presigned URL generated for '{object_name}'.")
        return url
    except ClientError as e:
        logger.error(f"Error generating presigned URL for '{object_name}': {e}")
        return None

def delete_file(object_name: str) -> bool:
    """
    MinIO'dan belirtilen objeyi siler.
    """
    current_s3_client = get_s3_client() # Güncel istemciyi get_s3_client() üzerinden al
    if current_s3_client is None:
        logger.error("MinIO client is not initialized. Cannot delete file.")
        return False
    try:
        current_s3_client.delete_object(Bucket=MINIO_BUCKET_NAME, Key=object_name)
        logger.info(f"File '{object_name}' deleted successfully from bucket '{MINIO_BUCKET_NAME}'.")
        return True
    except ClientError as e:
        logger.error(f"Error deleting file '{object_name}': {e}")
        return False

# NOT: MinIO istemcisinin başlatılması ve bucket'ın oluşturulması gibi işlemler,
# FastAPI uygulaması başladığında (main.py'de) çağrılmalıdır.
# Burada doğrudan çağırmıyoruz ki import edildiğinde hemen çalışmasın.