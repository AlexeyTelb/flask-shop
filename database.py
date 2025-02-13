import psycopg
import os
from dotenv import load_dotenv
from flask_login import UserMixin

# Загружаем переменные окружения
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


class User(UserMixin):
    def __init__(self, user_id, username, password):
        self.id = user_id
        self.username = username
        self.password = password

    @staticmethod
    def get(user_id):
        user_data = fetch_one("SELECT id, username, password FROM \"user\" WHERE id = %s", (user_id,))
        return User(*user_data) if user_data else None

def get_connection():
    """Создает подключение к базе данных."""
    return psycopg.connect(DATABASE_URL)

def fetch_one(query, params=None):
    """Выполняет SELECT и возвращает одну запись."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchone()

def fetch_all(query, params=None):
    """Выполняет SELECT и возвращает список записей."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchall()

def execute_query(query, params=None, commit=True):
    """Выполняет INSERT, UPDATE, DELETE."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
        if commit:
            conn.commit()
