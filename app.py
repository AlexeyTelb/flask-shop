from flask import Flask
from dotenv import load_dotenv
import os

from database import fetch_one, execute_query
from routes import init_routes
from werkzeug.security import generate_password_hash
# Загружаем переменные окружения из .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['UPLOAD_FOLDER'] = os.getenv("UPLOAD_FOLDER")

# Инициализация маршрутов
init_routes(app)
def create_admin():
    admin = fetch_one("SELECT id FROM \"user\" WHERE username = 'admin'")
    if not admin:
        hashed_password = generate_password_hash("admin123")  # Можно изменить пароль
        execute_query("INSERT INTO \"user\" (username, password) VALUES (%s, %s)",
                      ("admin", hashed_password))
        print("✅ Администратор создан: admin / admin123")

create_admin()  # Запуск при старте приложения
if __name__ == '__main__':
    app.run(debug=True)
