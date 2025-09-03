from django.db import models
from django.contrib.auth.models import User

class MonthlyData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    month = models.CharField(max_length=7) 
    income = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    goal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.username} - {self.month}"


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('hrana', 'Hrana'),
        ('smjestaj', 'Smještaj'),
        ('prijevoz', 'Prijevoz'),
        ('zabava', 'Zabava'),
        ('ostalo', 'Ostalo'),
    ]

    monthly_data = models.ForeignKey(MonthlyData, on_delete=models.CASCADE, related_name="expenses")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.category} - {self.amount} EUR"
