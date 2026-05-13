import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings


def get_database_engine():
    try:
        server = settings.MYSQL_HOST
        port =  settings.MYSQL_PORT
        database = settings.MYSQL_DB
        username = settings.MYSQL_USER
        password = settings.MYSQL_PASSWORD

        connection_url = (
            f"mysql+pymysql://{username}:{password}@{server}:{port}/{database}"
        )

        engine = create_engine(
            connection_url,
            pool_pre_ping=True,
            echo=False  # Set to False to reduce noise, or keep if you need SQL logs
        )

        return engine

    except Exception as e:
        print(f"Lỗi kết nối MySQL Sync: {e}")
        return None

def get_async_database_engine():
    try:
        server = settings.MYSQL_HOST
        port = settings.MYSQL_PORT
        database = settings.MYSQL_DB
        username = settings.MYSQL_USER
        password = settings.MYSQL_PASSWORD

        # Sử dụng mysql+aiomysql cho async
        connection_url = (
            f"mysql+aiomysql://{username}:{password}@{server}:{port}/{database}"
        )

        engine = create_async_engine(
            connection_url,
            pool_pre_ping=True,
            echo=False
        )

        return engine

    except Exception as e:
        print(f"Lỗi kết nối MySQL Async: {e}")
        return None
