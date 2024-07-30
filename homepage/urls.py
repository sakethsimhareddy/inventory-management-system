from django.urls import path
from . import views


urlpatterns = [
    path('',views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('register/',views.register,name='register'),                                                                       
    path('home/', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('inventory/',views.inventory,name='inventory'),
    path('transactions/', views.transaction, name='transaction'),
    path('transactions/edit/<int:pk>/', views.edit_transaction, name='edit_transaction'),
    path('transactions/delete/<int:pk>/', views.delete_transaction, name='delete_transaction'),
    path('purchase/',views.purchase,name='purchase'),
    path('sell/',views.sell,name='sell'),

]