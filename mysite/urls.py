"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from myapp import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Transactions
    path('transaction/', views.save_transaction, name='save_transaction'),
    path('transactions/', views.get_user_transactions, name='get_user_transactions'),
    path('transaction/delete/', views.delete_transactions, name='delete_transactions'),
    path('transaction/edit/', views.edit_transaction, name='edit_transaction'),
    path('clear_transactions/', views.clear_user_transactions, name='clear_user_transactions'),

    # Currency
    path('add_currency/', views.add_currency, name='add_currency'),
    path('delete_currency/', views.delete_currency, name='delete_currency'),
    path('list_currencies/', views.list_currencies, name='list_currencies'),
    path('add_inventory_amount/', views.add_inventory_amount, name='add_inventory_amount'),

    # Users
    path('add_user/', views.add_user, name='add_user'),
    path('delete_user/', views.delete_user, name='delete_user'),
    path('add_balance/', views.add_balance, name='add_balance'),
    path('get_user_inventory/', views.get_user_inventory, name='get_user_inventory'),
    path('reset_user_data/', views.reset_user_data, name='reset_user_data'),

    # Auth
    path('send_pin/', views.send_pin, name='send_pin'),
    path('verify_email/', views.verify_email, name='verify_email'),
    path('request_password_reset/', views.request_password_reset, name='request_password_reset'),
    path('confirm_password_reset/', views.confirm_password_reset, name='confirm_password_reset'),
    path('reset_password_form/', views.reset_password_form, name='reset_password_form'),
    path('login_user/', views.login_user, name='login_user'),
]