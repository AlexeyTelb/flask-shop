from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from database import fetch_one, fetch_all, execute_query
from werkzeug.utils import secure_filename
import os

from forms import RegistrationForm, EditProfileForm

login_manager = LoginManager()
login_manager.login_view = 'login'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Проверяет, является ли файл допустимым изображением."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_routes(app):
    """Инициализирует маршруты в приложении Flask."""
    login_manager.init_app(app)

    from database import User

    @app.route('/client', methods=['GET', 'POST'])
    @login_required
    def client_page():
        client = fetch_one("SELECT * FROM client WHERE userid = %s", (current_user.id,))
        if not client:
            flash("Ошибка! Клиент не найден.", "danger")
            return redirect(url_for('products'))

        form = EditProfileForm()

        if form.validate_on_submit():
            new_surname = form.surname.data or client[1]
            new_name = form.name.data or client[2]
            new_patronymic = form.patronymic.data or client[3]
            new_address = form.address.data or client[4]
            new_phone = form.phone.data or client[5]
            new_email = form.email.data or client[6]

            # Обновляем данные клиента
            execute_query("""
                UPDATE client SET surname = %s, name = %s, patronymic = %s, address = %s, phone = %s, email = %s
                WHERE userid = %s
            """, (new_surname, new_name, new_patronymic, new_address, new_phone, new_email, current_user.id))

            # Если ввели новый пароль, хешируем его и обновляем
            if form.password.data:
                new_password = generate_password_hash(form.password.data)
                execute_query("UPDATE \"user\" SET password = %s WHERE id = %s", (new_password, current_user.id))

            flash("Данные обновлены!", "success")
            return redirect(url_for('client_page'))

        # Передаём текущие данные в форму
        form.surname.data = client[1]
        form.name.data = client[2]
        form.patronymic.data = client[3]
        form.address.data = client[4]
        form.phone.data = client[5]
        form.email.data = client[6]

        return render_template('client.html', form=form)

    # Добавляем обработчик маршрутов
    @app.route('/add_product', methods=['GET', 'POST'])
    @login_required
    def add_product():
        user = fetch_one("SELECT username FROM \"user\" WHERE id = %s", (current_user.id,))
        if not user or user[0].lower() != "admin":
            flash("У вас нет прав для добавления товаров!", "danger")
            return redirect(url_for('products'))

        if request.method == 'POST':
            productname = request.form['productname']
            description = request.form['description']
            quantity = request.form['quantity']
            price = request.form['price']
            photo = request.files['photo']

            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo = str (f"{app.config['UPLOAD_FOLDER']}/{filename}")
            else:
                photo = None  # Фото не обязательно

            execute_query(
                "INSERT INTO product (productname, description, quantity, price, photo) VALUES (%s, %s, %s, %s, %s)",
                (productname, description, quantity, price, photo))

            flash("Товар добавлен!", "success")
            return redirect(url_for('products'))

        return render_template('add_product.html')

    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)

    @app.route('/')
    def home():
        return render_template('home.html', username=current_user.username if current_user.is_authenticated else None)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegistrationForm()
        if form.validate_on_submit():
            username = form.username.data.lower()  # Приводим к нижнему регистру

            # Запрещаем логин "admin"
            if username == "admin":
                flash("Этот логин запрещён!", "danger")
                return redirect(url_for('register'))

            password = generate_password_hash(form.password.data)

            existing_user = fetch_one("SELECT id FROM \"user\" WHERE username = %s", (username,))
            if existing_user:
                flash("Этот логин уже используется!", "danger")
                return redirect(url_for('register'))

            # Создаём пользователя и получаем его ID
            user_id = fetch_one("""
                INSERT INTO "user" (username, password) VALUES (%s, %s) RETURNING id
            """, (username, password))

            if not user_id:
                flash("Ошибка при создании пользователя!", "danger")
                return redirect(url_for('register'))

            user_id = user_id[0]  # Берём ID пользователя из запроса

            # Создаём запись в таблице client
            execute_query("""
                INSERT INTO client (name, userid) VALUES (%s, %s)
            """, (username, user_id))

            flash("Вы успешно зарегистрировались!", "success")
            return redirect(url_for('login'))

        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user_data = fetch_one("SELECT id, username, password FROM \"user\" WHERE username = %s", (username,))
            if user_data and check_password_hash(user_data[2], password):
                user = User(*user_data)  # Преобразуем в объект
                login_user(user)
                return redirect(url_for('products'))
            else:
                flash("Неверное имя пользователя или пароль", "danger")

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        logout_user()
        flash('Вы вышли из системы.', 'info')
        return redirect(url_for('home'))

    @app.route('/products')
    @login_required
    def products():
        search = request.args.get('search', '')
        sort = request.args.get('sort', 'default')

        query = "SELECT productid, productname, description, quantity, price, photo FROM product"
        params = []

        if search:
            query += " WHERE productname ILIKE %s OR description ILIKE %s"
            params.extend([f"%{search}%", f"%{search}%"])

        if sort == 'price_asc':
            query += " ORDER BY price ASC"
        elif sort == 'price_desc':
            query += " ORDER BY price DESC"
        elif sort == 'name_asc':
            query += " ORDER BY productname ASC"
        elif sort == 'name_desc':
            query += " ORDER BY productname DESC"

        products = fetch_all(query, params)

        # Преобразуем кортежи в словари
        product_list = [
            {
                "productid": p[0],
                "productname": p[1],
                "description": p[2],
                "quantity": p[3],
                "price": p[4],
                "photo": p[5]
            } for p in products
        ]

        return render_template('products.html', products=product_list, search=search, sort=sort)

    @app.route('/product/<int:product_id>')
    def product_detail(product_id):
        product = fetch_one("""
            SELECT productid, productname, description, quantity, price, photo 
            FROM product WHERE productid = %s
        """, (product_id,))

        if not product:
            flash("Товар не найден!", "danger")
            return redirect(url_for('products'))

        # Преобразуем кортеж в словарь
        product_data = {
            "productid": product[0],
            "productname": product[1],
            "description": product[2],
            "quantity": product[3],
            "price": product[4],
            "photo": product[5]
        }

        return render_template('product_detail.html', product=product_data)

    @app.route('/basket')
    @login_required
    def basket():
        client = fetch_one("SELECT clientid FROM client WHERE userid = %s", (current_user.id,))
        if not client:
            flash('Ошибка: у пользователя нет связанного клиента!', 'danger')
            return redirect(url_for('products'))

        client_id = client[0]

        basket_items = fetch_all("""
            SELECT 
                b.basketid, 
                p.productid, 
                p.productname, 
                p.photo, 
                b.quantity AS basket_quantity, 
                p.price, 
                p.quantity AS stock_quantity
            FROM basket b
            JOIN product p ON b.productid = p.productid
            WHERE b.clientid = %s
        """, (client_id,))

        # Преобразуем кортежи в список словарей
        basket_list = [
            {
                "basketid": item[0],
                "product": {
                    "productid": item[1],
                    "productname": item[2],
                    "photo": item[3],
                },
                "quantity": item[4],  # Количество в корзине
                "price": item[5],  # Цена
                "stock_quantity": item[6]  # Доступное количество на складе
            }
            for item in basket_items
        ]

        return render_template('basket.html', basket_items=basket_list)

    @app.route('/add_to_basket/<int:product_id>', methods=['POST'])
    @login_required
    def add_to_basket(product_id):
        client_id = fetch_one("SELECT clientid FROM client WHERE userid = %s", (current_user.id,))
        if not client_id:
            flash('Ошибка: у пользователя нет связанного клиента!', 'danger')
            return redirect(url_for('products'))

        basket_item = fetch_one("SELECT quantity FROM basket WHERE clientid = %s AND productid = %s", (client_id[0], product_id))

        if basket_item:
            execute_query("UPDATE basket SET quantity = quantity + 1 WHERE clientid = %s AND productid = %s", (client_id[0], product_id))
        else:
            execute_query("INSERT INTO basket (clientid, productid, quantity) VALUES (%s, %s, 1)", (client_id[0], product_id))

        flash('Товар добавлен в корзину!', 'success')
        return redirect(url_for('basket'))

    @app.route('/remove_from_basket/<int:basket_id>', methods=['POST'])
    @login_required
    def remove_from_basket(basket_id):
        execute_query("DELETE FROM basket WHERE basketid = %s", (basket_id,))
        flash('Товар удален из корзины!', 'success')
        return redirect(url_for('basket'))

    @app.route('/update_basket/<int:basket_id>', methods=['POST'])
    @login_required
    def update_basket(basket_id):
        basket_item = fetch_one("SELECT quantity, productid FROM basket WHERE basketid = %s", (basket_id,))

        if not basket_item:
            flash('Товар не найден в корзине!', 'danger')
            return redirect(url_for('basket'))

        new_quantity = request.form.get('quantity', 1)

        try:
            new_quantity = int(new_quantity)
        except ValueError:
            flash('Некорректное количество!', 'danger')
            return redirect(url_for('basket'))

        # Проверяем наличие товара на складе
        product_quantity = fetch_one("SELECT quantity FROM product WHERE productid = %s", (basket_item[1],))[0]

        if new_quantity < 1:
            flash('Количество товара не может быть меньше 1!', 'danger')
        elif new_quantity > product_quantity:
            flash(f'На складе доступно только {product_quantity} шт.', 'warning')
        else:
            execute_query("UPDATE basket SET quantity = %s WHERE basketid = %s", (new_quantity, basket_id))
            flash('Количество товара обновлено!', 'success')

        return redirect(url_for('basket'))

    @app.route('/place_order', methods=['POST'])
    @login_required
    def place_order():
        user_id = current_user.id
        client = fetch_one("SELECT clientid, address, phone, email FROM client WHERE userid = %s", (user_id,))

        if not client:
            flash("Ошибка! Клиент не найден.", "danger")
            return redirect(url_for('basket'))

        client_id, address, phone, email = client

        # Получаем все товары из корзины клиента
        basket_items = fetch_all("""
            SELECT b.basketid, b.productid, b.quantity, p.price 
            FROM basket b
            JOIN product p ON b.productid = p.productid
            WHERE b.clientid = %s
        """, (client_id,))

        if not basket_items:
            flash("Ваша корзина пуста!", "warning")
            return redirect(url_for('basket'))

        # Считаем общую стоимость заказа
        total_cost = sum(item[2] * item[3] for item in basket_items)

        # Создаем заказ и получаем orderid
        order_id = fetch_one("""
            INSERT INTO "order" (address, phone, email, cost, clientid, status) 
            VALUES (%s, %s, %s, %s, %s, 'В обработке') RETURNING orderid
        """, (address, phone, email, total_cost, client_id))

        if not order_id:
            flash("Ошибка при создании заказа!", "danger")
            return redirect(url_for('basket'))

        order_id = order_id[0]  # Забираем ID заказа из результата

        # Добавляем товары в таблицу productorder и обновляем склад
        for item in basket_items:
            execute_query("""
                INSERT INTO productorder (orderid, productid, quantity) 
                VALUES (%s, %s, %s)
            """, (order_id, item[1], item[2]))

            execute_query("""
                UPDATE product SET quantity = quantity - %s WHERE productid = %s
            """, (item[2], item[1]))

        # Очищаем корзину клиента
        execute_query("DELETE FROM basket WHERE clientid = %s", (client_id,))

        flash("Заказ успешно оформлен!", "success")
        return redirect(url_for('basket'))

    @app.route('/orders')
    @login_required
    def orders():
        client = fetch_one("SELECT clientid FROM client WHERE userid = %s", (current_user.id,))
        if not client:
            flash("Ошибка! Клиент не найден.", "danger")
            return redirect(url_for('products'))

        client_id = client[0]

        # Запрашиваем заказы клиента
        orders_data = fetch_all("""
            SELECT o.orderid, o.address, o.phone, o.email, o.cost, o.status, 
                   po.productid, p.productname, p.photo, po.quantity, p.price
            FROM "order" o
            JOIN productorder po ON o.orderid = po.orderid
            JOIN product p ON po.productid = p.productid
            WHERE o.clientid = %s
            ORDER BY o.orderid DESC
        """, (client_id,))

        # Группируем заказы по orderid
        orders_dict = {}
        for row in orders_data:
            order_id = row[0]
            if order_id not in orders_dict:
                orders_dict[order_id] = {
                    "orderid": row[0],
                    "address": row[1],
                    "phone": row[2],
                    "email": row[3],
                    "cost": row[4],
                    "status": row[5],
                    "products": []
                }

            orders_dict[order_id]["products"].append({
                "productid": row[6],
                "productname": row[7],
                "photo": row[8],
                "quantity": row[9],
                "price": row[10]
            })

        orders_list = list(orders_dict.values())

        return render_template('orders.html', orders=orders_list)
