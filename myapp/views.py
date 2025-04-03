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

#Not reqest
pending_users = {}

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

def send_email(user,password,email):
    token = str(uuid.uuid4())
    pending_users[token] = {'user': user, 'password': password, 'email': email}

    verify_url = f"https://dair12.pythonanywhere.com/verify_email?token={token}"
    send_mail(
        'Confirm your registration',
        f'Hi {user},\n\nClick the link to finish registration:\n{verify_url}',
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

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

            inventory, _ = Inventory.objects.get_or_create(user=user, currency=currency_obj)

            if operation == 'buy':
                user.balance -= transaction_cost
                inventory.quantity += quantity
            elif operation == 'sell':
                user.balance += transaction_cost
                inventory.quantity -= quantity
            else:
                return JsonResponse({"error": "Invalid operation"}, status=400)

            user.save()
            inventory.save()

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
            transaction.quantity = body.get('quantity', transaction.quantity)
            transaction.rate = body.get('rate', transaction.rate)
            transaction.save()
            return JsonResponse({"message": "Transaction updated successfully."}, status=200)
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

            if not user_id or not name or not code:
                return JsonResponse({'error': 'user_id, name, and code are required.'}, status=400)

            user = Users.objects.filter(id=user_id).first()
            if not user:
                return JsonResponse({'error': 'User not found.'}, status=404)

            currency, created = Currency.objects.get_or_create(code=code, defaults={'name': name})
            user.currencies.add(currency)

            return JsonResponse({'message': f'Currency "{currency.name}" ({currency.code}) added to user ID {user_id}.'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
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

            user.currencies.remove(currency)

            return JsonResponse({
                'message': f'Currency "{currency.name}" (ID {currency.id}) removed from user ID {user_id}.'
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

            user = get_object_or_404(Users, id=user_id)

            # Обнуление баланса
            user.balance = 0.0
            user.save()

            # Обнуление инвентаря
            Inventory.objects.filter(user=user).update(quantity=0.0)

            return JsonResponse({'message': 'User balance and inventory reset successfully.'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON input.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)