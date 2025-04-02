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

    #https://dair12.pythonanywhere.com/transaction/buy/USD/100/74/Dair/
    path('transaction/<str:operation>/<str:currency>/<int:quantity>/<str:rate>/', views.save_transaction, name='save_transaction'),

    #https://dair12.pythonanywhere.com/transactions/
    path('transactions/', views.get_user_transactions, name='get_user_transactions'),

    #https://dair12.pythonanywhere.com/add_currency/?name=USD
    path('add_currency/', views.add_currency, name='add_currency'),

    #https://dair12.pythonanywhere.com/delete_currency/USD/
    path('delete_currency/<str:name>/', views.delete_currency, name='delete_currency'),

    #https://dair12.pythonanywhere.com/list_currencies/
    path('list_currencies/', views.list_currencies, name='list_currencies'),

    path('transaction/delete/', views.delete_transactions, name='delete_transactions'),

    path('transaction/edit/<int:transaction_id>/', views.edit_transaction, name='edit_transaction'),

    path('add_user/', views.add_user, name='add_user'),
    path('delete_user/', views.delete_user, name='delete_user'),
    #https://dair12.pythonanywhere.com/get_all_users/
    path('get_all_users/', views.get_all_users, name='get_all_users'),

    path('clear_transactions/', views.clear_user_transactions, name='clear_user_transactions'),

    path('add_balance/', views.add_balance, name='add_balance'),

    path('get_user_inventory/', views.get_user_inventory, name='get_user_inventory'),

    path('reset_user_data/', views.reset_user_data, name='reset_user_data'),

    path('login_user/', views.login_user, name='login_user'),

]
