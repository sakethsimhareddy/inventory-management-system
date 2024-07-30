from django.db import models
from django.contrib.auth.models import User

# Create your models here
class Stock(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)
    quantity = models.IntegerField(default=1)
    is_deleted = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)

    class Meta:
        # Define unique constraint on name and user
        unique_together = ('name', 'user')

    def __str__(self):
        return self.name
    
class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('purchase', 'Purchase'),
        ('sell', 'Sell'),
    )

    source = models.CharField(max_length=100)  # Change from 'from' to 'source'
    destination = models.CharField(max_length=100)  # Change from 'to' to 'destination'
    item = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    date = models.DateField()

    def __str__(self):
        return f"{self.id}: {self.item} - {self.type}"
