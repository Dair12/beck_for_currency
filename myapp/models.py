from django.db import models

# Create your models here.

class Transaction(models.Model):
    OPERATION_CHOICES = [
        ('buy', 'Покупка'),
        ('sell', 'Продажа'),
    ]

    operation = models.CharField(max_length=10, choices=OPERATION_CHOICES)
    currency = models.ForeignKey('Currency', on_delete=models.CASCADE, related_name='transactions')
    quantity = models.IntegerField()
    rate = models.FloatField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    user = models.ForeignKey('Users', on_delete=models.CASCADE, related_name='transactions')

    def __str__(self):
        return f"{self.operation} {self.quantity} {self.currency.name} {self.rate}"


class Currency(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Users(models.Model):
    user = models.CharField(max_length=10)
    password=models.CharField(max_length=10)
    email = models.EmailField(unique=True)
    balance = models.FloatField(default=0.0)
    add = models.FloatField(default=0.0)
    currencies = models.ManyToManyField('Currency', related_name='users')
    def __str__(self):
        return f"{self.user} {self.password}"


class Inventory(models.Model):
    user = models.ForeignKey('Users', on_delete=models.CASCADE, related_name='inventory')
    currency = models.ForeignKey('Currency', on_delete=models.CASCADE, related_name='inventory')
    quantity = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.user.user} - {self.currency.name}: {self.quantity}"
