from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField
from wtforms.validators import DataRequired, Length, EqualTo, Email, Optional

# Форма регистрации
class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=4, max=100)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6, max=100)])
    confirm_password = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password', message='Пароли должны совпадать')])
    submit = SubmitField('Зарегистрироваться')

# Форма редактирования профиля
class EditProfileForm(FlaskForm):
    surname = StringField('Фамилия', validators=[Optional(), Length(max=100)])
    name = StringField('Имя', validators=[DataRequired(), Length(max=100)])
    patronymic = StringField('Отчество', validators=[Optional(), Length(max=100)])
    address = StringField('Адрес', validators=[Optional(), Length(max=255)])
    phone = StringField('Телефон', validators=[Optional(), Length(max=20)])
    email = EmailField('Email', validators=[Optional(), Email()])
    password = PasswordField('Новый пароль', validators=[Optional(), Length(min=6, max=100)])
    submit = SubmitField('Сохранить изменения')
