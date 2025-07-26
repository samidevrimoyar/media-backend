# Dockerfile
# FastAPI uygulamasını içeren Docker imajını oluşturmak için

# Python'ın belirli bir sürümünü temel imaj olarak kullanın
# python:3.9-slim-buster veya python:3.10-slim-buster gibi slim versiyonlar daha küçüktür.
FROM python:3.9-slim-buster

# Çalışma dizinini /app olarak ayarlayın
WORKDIR /app

# Bağımlılıklar dosyasını kopyalayın ve Python paketlerini kurun
# pip cache'ini kullanmayarak imaj boyutunu küçültün
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Uygulamanın geri kalan kodunu çalışma dizinine kopyalayın
# Bu, models/, routers/, database.py, storage.py, main.py ve .env dosyalarını içerir.
COPY . .

# FastAPI uygulamasının çalıştığı portu dışarıya açın
EXPOSE 8000

# Uygulamayı Uvicorn ile başlatma komutu
# --host 0.0.0.0: Uygulamanın tüm ağ arayüzlerinde dinlemesini sağlar (Docker içinde gerekli)
# --port 8000: Uygulamanın 8000 portunda çalışmasını sağlar
# --workers 1: Uvicorn için çalışan işlemci sayısı. Daha fazla performans için artırılabilir.
# main:app: main.py dosyasındaki 'app' FastAPI objesini belirtir
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]