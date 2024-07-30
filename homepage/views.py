from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib import auth
from django.shortcuts import render, get_object_or_404, redirect
from .forms import TransactionForm  # Assuming you have a form for the Transaction model
from .models import Stock, Transaction
from django.utils import timezone
from django.db.models import Q,F,Sum
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import urllib, base64
from collections import defaultdict



@login_required
def purchase(request):
    if request.method == 'POST':
        source = request.POST.get('source')
        item_name = request.POST.get('item')
        quantity = int(request.POST.get('quantity'))
        price = float(request.POST.get('price'))
        date = request.POST.get('date') or timezone.now().date()  # Use today's date if not provided

        # Use atomic transaction to ensure data integrity
        with db_transaction.atomic():
            stock_item, created = Stock.objects.get_or_create(name=item_name, defaults={'quantity': 0},user=request.user)
            stock_item.quantity = F('quantity') + quantity
            stock_item.save()

            # Create a new transaction
            Transaction.objects.create(
                source=source,
                destination=request.user,
                item=item_name,
                quantity=quantity,
                price=price,
                type='purchase',  # Assuming this is a purchase transaction
                date=date
            )

        return redirect('home')  # Redirect to a success page after saving

    return render(request, 'purchase.html')


@login_required
def sell(request):
    if request.method == 'POST':
        destination = request.POST.get('destination')
        item_name = request.POST.get('item')
        quantity = int(request.POST.get('quantity'))
        price = float(request.POST.get('price'))
        date = request.POST.get('date') or timezone.now().date()  # Use today's date if not provided

        # Use atomic transaction to ensure data integrity
        with db_transaction.atomic():
            try:
                stock_item = Stock.objects.get(name=item_name , user=request.user)
                if stock_item.quantity < quantity:
                    messages.error(request, 'Insufficient stock to complete the sale.')
                    return redirect('sell')

                stock_item.quantity = F('quantity') - quantity
                stock_item.save()

                # Create a new transaction
                Transaction.objects.create(
                    source=request.user,
                    destination=destination,
                    item=item_name,
                    quantity=quantity,
                    price=price,
                    type='sell',  # Assuming this is a sell transaction
                    date=date
                )
            except Stock.DoesNotExist:
                messages.error(request, 'The item you want to sell is out of stock or not available.')
                return redirect('sell')

        return redirect('home')  # Redirect to a success page after saving

    return render(request, 'sell.html')


@login_required
def transaction(request):
    transaction_type = request.GET.get('type')
    user = request.user
    
    # Fetch all transactions based on the provided transaction type
    if transaction_type:
        if transaction_type == 'purchase':
            transactions_list = Transaction.objects.filter(type='purchase', destination=user)
        elif transaction_type == 'sell':
            transactions_list = Transaction.objects.filter(type='sell', source=user)
    else:
        transactions_list = Transaction.objects.filter(Q(source=user) | Q(destination=user))
    
    # Paginate the transactions
    paginator = Paginator(transactions_list, 7)  # Show 7 transactions per page
    page_number = request.GET.get('page')
    try:
        transactions = paginator.page(page_number)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)
    
    return render(request, 'transaction.html', {'object_list': transactions})

@login_required
def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    original_quantity = transaction.quantity
    original_type = transaction.type
    if request.method == "POST":
        edited_quantity = int(request.POST.get('quantity'))
        edited_type = request.POST.get('type')

        with db_transaction.atomic():
            stock = Stock.objects.get(name=transaction.item , user=request.user)
            difference = edited_quantity - original_quantity

            if original_type == 'purchase':
                if stock.quantity + difference < 0:
                    messages.error(request, 'Insufficient stock to complete the update.')
                    return redirect('edit_transaction', pk=pk)
                stock.quantity += difference
            elif original_type == 'sell':
                if stock.quantity - difference < 0:
                    messages.error(request, 'Insufficient stock to complete the update.')
                    return redirect('edit_transaction', pk=pk)
                stock.quantity -= difference

            stock.save()
            transaction.quantity = edited_quantity
            transaction.type = edited_type
            transaction.save()

        return redirect('transaction')
    else:
        return render(request, 'edit_transaction.html', {'transaction': transaction})
    
@login_required
def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    stock = Stock.objects.get(name=transaction.item , user=request.user)
    quantity_to_restore = transaction.quantity

    if request.method == "POST":
        with db_transaction.atomic():
            if transaction.type == 'purchase':
                stock.quantity = F('quantity') - quantity_to_restore
            elif transaction.type == 'sell':
                stock.quantity = F('quantity') + quantity_to_restore

            stock.save()
            transaction.delete()

        return redirect('transaction')
    return render(request, 'delete_transaction.html', {'transaction': transaction})

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']
        
        if password == password2:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already taken')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()
                messages.success(request, 'You are now registered and can log in')
                return redirect('login')
        else:
            messages.error(request, 'Passwords do not match')
    return render(request, 'register.html')


@login_required
def home(request):
    user = request.user

    # Fetch all stocks for the user
    stocks = Stock.objects.filter(user=user, is_deleted=False)
    name = request.user.username
    if not stocks:  # Check if stocks queryset is empty
        # Handle case when there is no data available
        return render(request, 'home.html', {'name': name})

    # Initialize a dictionary to store quantities for each item
    item_quantities = defaultdict(int)

    # Calculate quantities for each item
    for stock in stocks:
        item_quantities[stock.name] += stock.quantity

    # Create data for the stocks pie chart
    labels_stocks = list(item_quantities.keys())
    quantities_stocks = list(item_quantities.values())
    colors_stocks = ['red', 'blue', 'green', 'orange', 'purple', 'yellow', 'cyan', 'magenta', 'lime', 'pink']
    graphic_stocks = convert_to_base64(labels_stocks, quantities_stocks, colors_stocks)

    # Fetch total purchase and sell quantities
    total_purchase = Transaction.objects.filter(destination=user, type='purchase').aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_sell = Transaction.objects.filter(source=user, type='sell').aggregate(Sum('quantity'))['quantity__sum'] or 0

    # Create data for the sales pie chart
    labels_sales = ['Purchase', 'Sell']
    quantities_sales = [total_purchase, total_sell]
    colors_sales = ['orange', 'purple']
    graphic_sales = convert_to_base64(labels_sales, quantities_sales, colors_sales)

    # Calculate profit or loss for each item
    item_profit_loss = defaultdict(float)
    for item, quantity in item_quantities.items():
        total_purchase_price = Transaction.objects.filter(item=item, type='purchase').aggregate(Sum('price'))['price__sum'] or 0
        total_sell_price = Transaction.objects.filter(item=item, type='sell').aggregate(Sum('price'))['price__sum'] or 0
        profit_loss = total_sell_price - total_purchase_price
        item_profit_loss[item] = profit_loss

    # Create data for the profit or loss bar chart
    labels_profit_loss = list(item_profit_loss.keys())
    values_profit_loss = list(item_profit_loss.values())
    colors_profit_loss = ['green' if value >= 0 else 'red' for value in values_profit_loss]
    graphic_profit_loss = convert_to_base64_bar(labels_profit_loss, values_profit_loss, colors_profit_loss)

    return render(request, 'home.html', {
        'graphic_stocks': graphic_stocks,
        'graphic_sales': graphic_sales,
        'graphic_profit_loss': graphic_profit_loss,
        'name': name
    })

# Function to convert data to base64 for rendering in HTML
def convert_to_base64(labels, sizes, colors):
    plt.figure(figsize=(6, 6))
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, startangle=140)
    plt.axis('equal')
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()  # Close the figure
    graphic = base64.b64encode(image_png).decode('utf-8')
    return graphic

# Function to convert data to base64 for rendering bar chart in HTML
def convert_to_base64_bar(labels, values, colors):
    plt.figure(figsize=(10, 6))
    plt.bar(labels, values, color=colors)
    plt.xlabel('Item')
    plt.ylabel('Profit/Loss')
    plt.title('Profit/Loss by Item')
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()  # Close the figure
    graphic = base64.b64encode(image_png).decode('utf-8')
    return graphic
    
def logout(request):
    auth.logout(request)
    return redirect('/')
def about(request):
    return render(request, 'about.html')


@login_required
def inventory(request):
    user = request.user
    search_query = request.GET.get('name')

    if search_query:
        stocks = Stock.objects.filter(user=user, name__icontains=search_query, quantity__gt=0, is_deleted=False)
    else:
        stocks = Stock.objects.filter(user=user, quantity__gt=0, is_deleted=False)
    
    # Paginate the stocks
    paginator = Paginator(stocks, 7)  # Show 7 stocks per page
    page_number = request.GET.get('page')
    try:
        stocks = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        stocks = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        stocks = paginator.page(paginator.num_pages)

    return render(request, 'inventory.html', {'object_list': stocks, 'search_query': search_query})





