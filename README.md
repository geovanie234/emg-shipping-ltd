# EMG Shipping Ltd

EMG Shipping Ltd is a Django web application for browsing products, managing a cart, placing orders, and tracking deliveries.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Set the required environment variables in PowerShell:

```powershell
$env:DJANGO_SECRET_KEY = "replace-with-a-long-random-secret"
$env:DJANGO_DEBUG = "True"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,testserver"
```

4. Apply migrations and run the server:

```powershell
python manage.py migrate
python manage.py runserver
```

`db.sqlite3` is intentionally ignored so local data does not get committed to the public repository.
