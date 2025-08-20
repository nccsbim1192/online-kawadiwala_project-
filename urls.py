from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),  # Add this line for the home page
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Dashboard redirect
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Role-specific dashboards
    path('customer/', views.customer_dashboard, name='customer_dashboard'),
    path('collector/', views.collector_dashboard, name='collector_dashboard'),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # Customer functionality
    path('request-pickup/', views.request_pickup, name='request_pickup'),
    path('pickup-history/', views.pickup_history, name='pickup_history'),
    path('cancel-pickup/<int:pickup_id>/', views.cancel_pickup, name='cancel_pickup'),
    
    # Collector functionality
    path('assign-pickup/<int:pickup_id>/', views.assign_pickup, name='assign_pickup'),
    path('update-pickup/<int:pickup_id>/', views.update_pickup, name='update_pickup'),
    
    # Payment URLs (from your previous implementation)
    path('payment/<int:pickup_id>/', views.initiate_payment, name='initiate_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failure/', views.payment_failure, name='payment_failure'),
    
    # Public API
    path('api/waste-categories/', views.waste_categories_api, name='waste_categories_api'),
]
