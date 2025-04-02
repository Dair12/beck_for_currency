from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Transaction
from .models import Currency
from .models import Users
from .models import Inventory
from django.shortcuts import get_object_or_404
import json
import smtplib
import dns.resolver
import socket

#Dair12

#Not reqest
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

#Transactions___________________________________________________________________

@csrf_exempt
def save_transaction(request, operation, currency, quantity, rate):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get('user')
            user = Users.objects.filter(user=username).first()
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)
            currencyadd, created = Currency.objects.get_or_create(name=currency)
            currency_obj = Currency.objects.filter(name=currency).first()
            if not currency_obj:
                return JsonResponse({"error": "Currency not found"}, status=404)

            rate = float(rate)
            quantity = int(quantity)

            # Обновление баланса пользователя
            transaction_cost = quantity * rate
            inventory, created = Inventory.objects.get_or_create(user=user, currency=currency_obj)
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

            rate = float(rate)
            quantity = int(quantity)
            transaction = Transaction.objects.create(
                operation=operation,
                currency=currency_obj,
                quantity=quantity,
                rate=rate,
                user=user
            )
            transaction.save()
            return JsonResponse({"message": "Transaction saved", "transaction": {
                "operation": transaction.operation,
                "currency": transaction.currency.name,
                "quantity": transaction.quantity,
                "rate": transaction.rate,
                "created_at": transaction.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }})
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
            username = data.get('user')

            if not username:
                return JsonResponse({"error": "User field is required."}, status=400)

            user = Users.objects.filter(user=username).first()
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
def edit_transaction(request, transaction_id):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
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
            username = data.get('user')

            if not username:
                return JsonResponse({"error": "User field is required."}, status=400)

            user = Users.objects.filter(user=username).first()
            if not user:
                return JsonResponse({"error": "User not found"}, status=404)

            # Удаляем все транзакции пользователя
            Transaction.objects.filter(user=user).delete()
            return JsonResponse({"message": f"All transactions for user {username} have been deleted."}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)

#currency_______________________________________________________________________

@csrf_exempt
def add_currency(request):
    if request.method == 'GET':
        name = request.GET.get('name')  # Получаем название валюты из параметра запроса
        if name:
            currency, created = Currency.objects.get_or_create(name=name)
            if created:
                return JsonResponse({'message': f'Currency "{name}" added successfully.'}, status=200)
            return JsonResponse({'message': f'Currency "{name}" already exists.'}, status=400)
        else:
            return JsonResponse({'error': 'Name parameter is required.'}, status=400)
    else:
        return JsonResponse({'error': 'Only GET method is allowed.'}, status=405)


def delete_currency(request, name):
    if request.method == 'GET':  # Используем GET вместо DELETE для простоты URL
        try:
            currency = Currency.objects.get(name=name)
            currency.delete()
            return JsonResponse({'message': f'Currency "{name}" deleted successfully.'}, status=200)
        except Currency.DoesNotExist:
            return JsonResponse({'error': f'Currency "{name}" not found.'}, status=404)
    else:
        return JsonResponse({'error': 'Only GET method is allowed.'}, status=405)

def list_currencies(request):
    currencies = Currency.objects.values_list('name', flat=True)
    return JsonResponse(list(currencies), safe=False)

#users__________________________________________________________________________

@csrf_exempt
def add_balance(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('user')
            amount = data.get('amount')

            if not username or amount is None:
                return JsonResponse({'error': 'Both user and amount fields are required.'}, status=400)

            if amount <= 0:
                return JsonResponse({'error': 'Amount must be greater than 0.'}, status=400)

            user = get_object_or_404(Users, user=username)
            user.balance += amount  # Увеличиваем баланс
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

            new_user = Users(user=user, password=password, email=email)
            new_user.save()
            return JsonResponse({'message': 'User added successfully.', 'user': new_user.user, 'email': new_user.email})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON input.'}, status=400)
    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)


@csrf_exempt
def delete_user(request):
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            user = data.get('user')

            if not user:
                return JsonResponse({'error': 'User field is required.'}, status=400)

            user_instance = get_object_or_404(Users, user=user)
            user_instance.delete()
            return JsonResponse({'message': 'User deleted successfully.'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON input.'}, status=400)
    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)

# def get_all_users(request):
#     currencies = Users.objects.values_list('user', flat=True)
#     return JsonResponse(list(currencies), safe=False)

@csrf_exempt
def login_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        try:
            user = get_object_or_404(Users, user=username)
            #user = Users.objects.get(user=username)
            user.is_online = True
            user.save()
            return JsonResponse({'message': f'User {username} is now online.'}, status=200)
        except Users.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)


@csrf_exempt
def logout_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        try:
            user = get_object_or_404(Users, user=username)
            #user = Users.objects.get(user=username)
            user.is_online = False
            user.save()
            return JsonResponse({'message': f'User {username} is now offline.'}, status=200)
        except Users.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)

# @csrf_exempt
# def get_all_users(request):
#     if request.method == 'GET':
#         users = Users.objects.all()
#         user_list = [{'username': user.username, 'is_online': user.is_online} for user in users]
#         return JsonResponse(user_list, safe=False)
@csrf_exempt
def get_all_users(request):
    if request.method == 'GET':
        users = Users.objects.all()
        user_list = [{'user': user.user, 'is_online': user.is_online} for user in users]
        return JsonResponse(user_list, safe=False)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def get_password_by_username(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = data.get('user')

            if not user:
                return JsonResponse({'error': 'User field is required.'}, status=400)

            user_instance = get_object_or_404(Users, user=user)
            return JsonResponse({'user': user_instance.user, 'password': user_instance.password,'balance': user_instance.balance})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON input.'}, status=400)
    return JsonResponse({'error': 'Invalid HTTP method.'}, status=405)

@csrf_exempt
def get_user_inventory(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('user')

            if not username:
                return JsonResponse({'error': 'User field is required.'}, status=400)

            user = get_object_or_404(Users, user=username)
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
            username = data.get('user')

            if not username:
                return JsonResponse({'error': 'User field is required.'}, status=400)

            user = get_object_or_404(Users, user=username)

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

