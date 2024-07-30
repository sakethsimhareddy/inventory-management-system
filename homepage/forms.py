from django import forms
from .models import Transaction

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['source', 'destination', 'item', 'quantity', 'price', 'type', 'date']
