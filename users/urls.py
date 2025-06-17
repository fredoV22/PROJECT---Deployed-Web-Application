from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('cashier/', views.cashier_dashboard, name='cashier_dashboard'),
    path('register/', views.register, name='register'),
] 