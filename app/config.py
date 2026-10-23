import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://app_user:app_password@127.0.0.1:3307/app_db",
)
