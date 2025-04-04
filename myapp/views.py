from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Transaction
from .models import Currency
from .models import Users
from .models import Inventory
from django.shortcuts import get_object_or_404
from django.db import models
import json
import smtplib
import dns.resolver
import socket
import uuid
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

#Not reqest
pending_users = {}
reset_tokens = {}

def reset_user_data_by_id(user_id):
    try:
        user = get_object_or_404(Users, id=user_id)

        # Сброс баланса и add
        user.balance = 0.0
        user.add = 0.0
        user.save()

        # Сброс quantity и add в инвентаре
        Inventory.objects.filter(user=user).update(quantity=0.0, add=0.0)

        return "Баланс и инвентарь успешно сброшены"

    except Exception as e:
        return f"Ошибка при сбросе: {str(e)}"

def calculate_user_balance_and_inventory(user_id):
    from .models import Users, Inventory, Transaction

    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return "Пользователь не найден"

    # Словарь для временного хранения количества по каждой валюте
    inventory_quantities = {}

    # Обрабатываем все транзакции пользователя
    transactions = Transaction.objects.filter(user=user)

    balance = 0

    for tx in transactions:
        amount = tx.quantity * tx.rate
        currency_id = tx.currency.id

        if currency_id not in inventory_quantities:
            inventory_quantities[currency_id] = 0

        if tx.operation == 'buy':
            balance -= amount
            inventory_quantities[currency_id] += tx.quantity
        elif tx.operation == 'sell':
            balance += amount
            inventory_quantities[currency_id] -= tx.quantity

    # Добавляем user.add
    final_balance = balance + user.add

    # Обновляем или создаем записи инвентаря
    for currency_id, calculated_quantity in inventory_quantities.items():
        try:
            inventory = Inventory.objects.get(user=user, currency_id=currency_id)
        except Inventory.DoesNotExist:
            inventory = Inventory.objects.create(user=user, currency_id=currency_id, quantity=0, add=0)

        # Применяем add
        final_quantity = calculated_quantity + inventory.add

        # Обновляем количество
        inventory.quantity = final_quantity
        inventory.save()

    # Обновляем баланс пользователя
    user.balance = final_balance
    user.save()

    return "Баланс и инвентарь обновлены"

def add_amount_to_currency(user_id, currency_id, amount):
    user = get_object_or_404(Users, id=user_id)
    currency = get_object_or_404(Currency, id=currency_id)

    inventory, _ = Inventory.objects.get_or_create(user=user, currency=currency)
    inventory.quantity += amount
    inventory.add += amount
    inventory.save()

def is_email_real(email):
    try:
        domain = email.split('@')[1]
        records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(records[0].exchange)

        # Устанавливаем SMTP соединение
        server = smtplib.SMTP(timeout=10)
        server.set_debuglevel(0)
        server.connect(mx_record)
        server.helo(socket.gethostname())
        server.mail('test@example.com')
        code, _ = server.rcpt(email)
        server.quit()

        return code == 250
    except Exception as e:
        return False

def verify_email(request):
    token = request.GET.get('token')
    if not token or token not in pending_users:
        return JsonResponse({'error': 'Invalid or expired token'}, status=400)

    data = pending_users.pop(token)
    new_user = Users(user=data['user'], password=data['password'], email=data['email'])
    new_user.save()

    return JsonResponse({'message': 'Registration successful. Welcome, ' + new_user.user})

# def send_email(user,password,email):
#     token = str(uuid.uuid4())
#     pending_users[token] = {'user': user, 'password': password, 'email': email}

#     verify_url = f"https://dair12.pythonanywhere.com/verify_email?token={token}"
#     send_mail(
#         'Confirm your registration',
#         f'Hi {user},\n\nClick the link to finish registration:\n{verify_url}',
#         settings.DEFAULT_FROM_EMAIL,
#         [email],
#         fail_silently=False,
#     )

def send_email(user, password, email):
    token = str(uuid.uuid4())
    pending_users[token] = {'user': user, 'password': password, 'email': email}

    verify_url = f"https://dair12.pythonanywhere.com/verify_email?token={token}"

    subject = "Confirm your registration"
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [email]

    # Текстовая версия (на случай если HTML не поддерживается)
    text_content = f"""Hi {user},

Thank you for registering at My App!

Please click the link below to verify your email address:
{verify_url}

If you did not request this, just ignore this message.

Best regards,
The My App Team
"""

    # HTML-версия письма
    html_content = f"""
    <html>
        <body>
            <p>Hi {user},</p>
            <p>Thank you for registering at <strong>My App</strong>!</p>
            <p>Please click the link below to verify your email address:</p>
            <p><a href="{verify_url}">Verify your email</a></p>
            <p>If you did not request this, just ignore this message.</p>
            <br>
            <p>Best regards,<br><strong>The My App Team</strong></p>
        </body>
    </html>
    """

    # Отправка письма
    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()


#Transactions___________________________________________________________________

from datetime import datetime

@csrf_exempt
def save_transaction(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            operation = data.get('operation')
            currency = data.get('currency')
            quantity = data.get('quantity')
            rate = data.get('rate')
            user_id = data.get('user_id')
            description = data.get('description', '')
            created_at_str = data.get('created_at')  # формат "YYYY-MM-DD HH:MM"

            # Проверки
            if not all([operation, currency, quantity, rate, user_id, created_at_str]):
                return JsonResponse({"error": "Missing required fields."}, status=400)

            user = Users.objects.filter(id=user_id).first()
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            currency_obj, _ = Currency.objects.get_or_create(name=currency)

            rate = float(rate)
            quantity = int(quantity)
            transaction_cost = quantity * rate

            try:
                created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M")
            except ValueError:
                return JsonResponse({"error": "Incorrect date format. Use 'YYYY-MM-DD HH:MM'"}, status=400)

            # inventory, _ = Inventory.objects.get_or_create(user=user, currency=currency_obj)

            # if operation == 'buy':
            #     user.balance -= transaction_cost
            #     inventory.quantity += quantity
            # elif operation == 'sell':
            #     user.balance += transaction_cost
            #     inventory.quantity -= quantity
            # else:
            #     return JsonResponse({"error": "Invalid operation"}, status=400)

            # user.save()
            # inventory.save()

            # Создаём транзакцию с датой
            transaction = Transaction.objects.create(
                operation=operation,
                currency=currency_obj,
                quantity=quantity,
                rate=rate,
                user=user,
                description=description,
                created_at=created_at
            )

            calculate_user_balance_and_inventory(user_id)

            return JsonResponse({
                "message": "Transaction saved",
                "transaction": {
                    "operation": transaction.operation,
                    "currency": transaction.currency.name,
                    "quantity": transaction.quantity,
                    "rate": transaction.rate,
                    "description": transaction.description,
                    "created_at": transaction.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
            })

        except ValueError:
            return JsonResponse({"error": "Invalid data format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def get_user_transactions(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')

            if not user_id:
                return JsonResponse({"error": "user_id field is required."}, status=400)

            user = Users.objects.filter(id=user_id).first()
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            transactions = Transaction.objects.filter(user=user)
            data = [
                {
                    "id": transaction.id,
                    "operation": transaction.operation,
                    "currency": transaction.currency.name,
                    "quantity": transaction.quantity,
                    "rate": transaction.rate,
                    "description": transaction.description,
                    "created_at": transaction.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for transaction in transactions
            ]
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method."}, status=405)

@csrf_exempt
def delete_transactions(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            ids = body.get('ids', [])
            Transaction.objects.filter(id__in=ids).delete()
            calculate_user_balance_and_inventory(user_id)
            return JsonResponse({"message": "Transactions deleted successfully."}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def edit_transaction(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            transaction_id = body.get('transaction_id')
            if not transaction_id:
                return JsonResponse({"error": "transaction_id is required."}, status=400)

            transaction = Transaction.objects.get(id=transaction_id)

            # Сохраняем user_id до изменений
            user_id = transaction.user.id

            # Обновляем поля, если они переданы
            if 'operation' in body:
                transaction.operation = body['operation']
            if 'currency' in body:
                currency_name = body['currency']
                currency_obj, _ = Currency.objects.get_or_create(name=currency_name)
                transaction.currency = currency_obj
            if 'quantity' in body:
                transaction.quantity = int(body['quantity'])
            if 'rate' in body:
                transaction.rate = float(body['rate'])
            if 'description' in body:
                transaction.description = body['description']
            if 'created_at' in body:
                try:
                    transaction.created_at = datetime.strptime(body['created_at'], "%Y-%m-%d %H:%M")
                except ValueError:
                    return JsonResponse({"error": "Incorrect date format. Use 'YYYY-MM-DD HH:MM'"}, status=400)

            transaction.save()

            # Пересчёт баланса
            calculate_user_balance_and_inventory(user_id)

            return JsonResponse({"message": "Transaction updated and balance recalculated."}, status=200)

        except Transaction.DoesNotExist:
            return JsonResponse({"error": "Transaction not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def clear_user_transactions(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')

            if not user_id:
                return JsonResponse({"error": "user_id field is required."}, status=400)

            user = Users.objects.filter(id=user_id).first()
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            # Удаляем все транзакции пользователя
            Transaction.objects.filter(user=user).delete()
            reset_user_data_by_id(user_id)
            return JsonResponse({"message": f"All transactions for user ID {user_id} have been deleted."}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)

#currency_______________________________________________________________________

@csrf_exempt
def add_currency(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            name = data.get('name')
            code = data.get('code')
            amount = data.get('amount')

            if not user_id or not name or not code or amount is None:
                return JsonResponse({'error': 'user_id, name, and code are required.'}, status=400)

            user = Users.objects.filter(id=user_id).first()
            if not user:
                return JsonResponse({'error': 'User not found.'}, status=404)

            currency, created = Currency.objects.get_or_create(code=code, defaults={'name': name})
            user.currencies.add(currency)

            add_amount_to_currency(user_id, currency.id, amount)

            return JsonResponse({'message': f'Currency "{currency.name}" ({currency.code}) added to user ID {user_id}.'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method.'}, status=405)

@csrf_exempt
def add_inventory_amount(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            currency_id = data.get('currency_id')
            amount = data.get('amount')

            if not user_id or not currency_id or amount is None:
                return JsonResponse({'error': 'user_id, currency_id, and amount are required.'}, status=400)

            if amount <= 0:
                return JsonResponse({'error': 'Amount must be greater than 0.'}, status=400)

            add_amount_to_currency(user_id, currency_id, amount)

            return JsonResponse({'message': 'Amount successfully added to inventory.',}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON input.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

@csrf_exempt
def delete_currency(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            currency_id = data.get('currency_id')

            if not user_id or not currency_id:
                return JsonResponse({'error': 'Both user_id and currency_id are required.'}, status=400)

            user = Users.objects.filter(id=user_id).first()
            if not user:
                return JsonResponse({'error': 'User not found'}, status=404)

            currency = Currency.objects.filter(id=currency_id).first()
            if not currency:
                return JsonResponse({'error': 'Currency not found'}, status=404)

            # Удаляем все транзакции пользователя с этой валютой
            Transaction.objects.filter(user=user, currency=currency).delete()

            # Удаляем валюту из связей ManyToMany
            user.currencies.remove(currency)

            # Удаляем запись из Inventory (если есть)
            Inventory.objects.filter(user=user, currency=currency).delete()

            # Пересчитываем баланс и инвентарь
            calculate_user_balance_and_inventory(user_id)

            return JsonResponse({
                'message': f'Currency "{currency.name}" (ID {currency.id}) and all related transactions for user ID {user_id} have been removed.'
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Only POST method is allowed.'}, status=405)

@csrf_exempt
def list_currencies(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')

            if not user_id:
                return JsonResponse({'error': 'user_id field is required.'}, status=400)

            user = Users.objects.filter(id=user_id).first()
            if not user:
                return JsonResponse({'error': 'User not found'}, status=404)

            currencies = user.currencies.all()
            currency_list = [[c.id, c.name, c.code] for c in currencies]

            return JsonResponse(currency_list, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method.'}, status=405)

#users__________________________________________________________________________
from django.template.loader import render_to_string
from django.shortcuts import redirect

def reset_password_form(request):
    token = request.GET.get('token')
    if not token:
        return HttpResponse("Invalid token", status=400)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reset Password</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h2>Enter new password</h2>
        <form method="POST" action="/confirm_password_reset/">
            <input type="hidden" name="token" value="{token}" />
            <label>New password:</label><br>
            <input type="password" name="password1" required><br><br>
            <label>Repeat password:</label><br>
            <input type="password" name="password2" required><br><br>
            <button type="submit">Reset</button>
        </form>
    </body>
    </html>
    """
    return HttpResponse(html)

@csrf_exempt
def request_password_reset(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')

            if not email:
                return JsonResponse({'error': 'Email is required.'}, status=400)

            user = Users.objects.filter(email=email).first()
            if not user:
                return JsonResponse({'error': 'User with this email not found.'}, status=404)

            token = str(uuid.uuid4())
            reset_tokens[token] = user.id

            reset_url = f"https://dair12.pythonanywhere.com/reset_password_form/?token={token}"

            subject = "Reset your password"
            from_email = settings.DEFAULT_FROM_EMAIL
            to = [email]

            text = f"Click the link to reset your password:\n{reset_url}"
            html = f"""
            <html>
                <body>
                    <p>Click the link to reset your password:</p>
                    <a href="{reset_url}">{reset_url}</a>
                </body>
            </html>
            """

            msg = EmailMultiAlternatives(subject, text, from_email, to)
            msg.attach_alternative(html, "text/html")
            msg.send()

            return JsonResponse({'message': 'Password reset link has been sent to your email.'}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def confirm_password_reset(request):
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            token = data.get('token')
            password1 = data.get('password1')
            password2 = data.get('password2')

            if not token or not password1 or not password2:
                return JsonResponse({'error': 'All fields are required.'}, status=400)

            if password1 != password2:
                return JsonResponse({'error': 'Passwords do not match.'}, status=400)

            user_id = reset_tokens.pop(token, None)
            if not user_id:
                return JsonResponse({'error': 'Invalid or expired token.'}, status=400)

            user = Users.objects.filter(id=user_id).first()
            if not user:
                return JsonResponse({'error': 'User not found.'}, status=404)

            user.password = password1
            user.save()

            return HttpResponse("Password has been successfully reset.")
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def add_balance(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            amount = data.get('amount')

            if not user_id or amount is None:
                return JsonResponse({'error': 'Both user_id and amount fields are required.'}, status=400)

            if amount <= 0:
                return JsonResponse({'error': 'Amount must be greater than 0.'}, status=400)

            user = get_object_or_404(Users, id=user_id)
            user.balance += amount
            user.add += amount
            user.save()

            return JsonResponse({'message': 'Balance updated successfully.', 'balance': user.balance}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON input.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)

@csrf_exempt
def add_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = data.get('user')
            password = data.get('password')
            email = data.get('email')

            if not user or not password or not email:
                return JsonResponse({'error': 'User, password, and email fields are required.'}, status=400)

            if Users.objects.filter(user=user).exists():
                return JsonResponse({'error': 'User already exists.'}, status=400)

            if Users.objects.filter(email=email).exists():
                return JsonResponse({'error': 'Email already registered.'}, status=400)

            if not is_email_real(email):
                return JsonResponse({'error': 'Provided email address does not appear to be real.'}, status=400)

            send_email(user,password,email)

            return JsonResponse({'message': 'Confirmation email sent. Please verify to complete registration.'})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)

@csrf_exempt
def delete_user(request):
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')

            if not user_id:
                return JsonResponse({'error': 'user_id field is required.'}, status=400)

            user_instance = get_object_or_404(Users, id=user_id)
            user_instance.delete()

            return JsonResponse({'message': 'User deleted successfully.'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON input.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)

@csrf_exempt
def login_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            identifier = data.get('identifier')  # username или email
            password = data.get('password')

            if not identifier or not password:
                return JsonResponse({'error': 'Identifier and password are required.'}, status=400)

            # Поиск по нику или email
            user = Users.objects.filter(models.Q(user=identifier) | models.Q(email=identifier)).first()

            if not user:
                return JsonResponse({'error': 'User not found.'}, status=404)

            if user.password != password:
                return JsonResponse({'error': 'Invalid password.'}, status=401)

            return JsonResponse({'message': f'Welcome back, {user.user}!', 'id': user.id, 'user': user.user, 'email': user.email, 'balance': user.balance}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON input.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method.'}, status=405)

@csrf_exempt
def get_user_inventory(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')

            if not user_id:
                return JsonResponse({'error': 'user_id field is required.'}, status=400)

            user = get_object_or_404(Users, id=user_id)
            inventory = Inventory.objects.filter(user=user)

            inventory_data = [
                {
                    'currency': item.currency.name,
                    'quantity': item.quantity
                }
                for item in inventory
            ]
            return JsonResponse({'inventory': inventory_data}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON input.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)

@csrf_exempt
def reset_user_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')

            if not user_id:
                return JsonResponse({'error': 'user_id field is required.'}, status=400)

            reset_user_data_by_id(user_id)

            return JsonResponse({'message': 'User balance and inventory reset successfully.'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON input.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)