from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Sum

from .models import (
    User, WasteCategory, PickupRequest,
    Transaction, RecyclingImpact
)
from .forms import (
    CustomUserCreationForm, PickupRequestForm, CollectorUpdateForm
)


# ────────────────────────────────────────────────────────────
# PUBLIC VIEWS
# ────────────────────────────────────────────────────────────
def home(request):
    """Landing page with high-level statistics."""
    context = {
        'total_users': User.objects.count(),
        'total_pickups': PickupRequest.objects.count(),
        'completed_pickups': PickupRequest.objects.filter(status='completed').count(),
        'waste_categories': WasteCategory.objects.filter(is_active=True)[:4],
    }
    return render(request, 'core/home.html', context)


def register(request):
    """Sign-up page that lets a visitor create a Customer, Collector or Admin."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.role == 'customer':
                RecyclingImpact.objects.create(user=user)
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Your account is ready.')
            return redirect('dashboard')
        messages.error(request, 'Please correct the form errors.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/register.html', {'form': form})


def user_login(request):
    """Session-based authentication."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        if user:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'core/login.html')


def user_logout(request):
    """
    TERMINATE the session cleanly, add a toast message and
    always return the visitor to the home page.
    """
    if request.user.is_authenticated:
        username = request.user.username
        request.session.flush()          # purge every session key
        logout(request)
        messages.success(request, f'Good-bye {username}! You have been logged out.')
    return redirect('home')


# ────────────────────────────────────────────────────────────
# GENERIC DASHBOARD REDIRECT
# ────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    """Redirect an authenticated user to the role-specific dashboard."""
    role_redirects = {
        'customer':  'customer_dashboard',
        'collector': 'collector_dashboard',
        'admin':     'admin_dashboard',
    }
    target = role_redirects.get(request.user.role)
    if target:
        return redirect(target)
    messages.error(request, 'Invalid user role.')
    return redirect('home')


# ────────────────────────────────────────────────────────────
# CUSTOMER VIEWS
# ────────────────────────────────────────────────────────────
@login_required
def customer_dashboard(request):
    if request.user.role != 'customer':
        return HttpResponseForbidden('Access denied.')

    recent_pickups = (
        PickupRequest.objects
        .filter(customer=request.user)
        .order_by('-created_at')[:5]
    )
    pickup_stats = {
        'pending':   PickupRequest.objects.filter(customer=request.user, status='pending').count(),
        'completed': PickupRequest.objects.filter(customer=request.user, status='completed').count(),
        'total':     PickupRequest.objects.filter(customer=request.user).count(),
    }

    impact, created = RecyclingImpact.objects.get_or_create(user=request.user)
    if not created:
        impact.update_impact()

    completed = PickupRequest.objects.filter(
        customer=request.user,
        status='completed',
        actual_weight_kg__isnull=False
    )
    total_earnings = sum(p.actual_price() for p in completed)

    context = {
        'recent_pickups': recent_pickups,
        'pickup_stats':   pickup_stats,
        'impact':         impact,
        'total_earnings': total_earnings,
    }
    return render(request, 'core/dashboard_customer.html', context)


@login_required
def request_pickup(request):
    if request.user.role != 'customer':
        return HttpResponseForbidden('Only customers can request pickups.')

    if request.method == 'POST':
        form = PickupRequestForm(request.POST)
        if form.is_valid():
            pickup = form.save(commit=False)
            pickup.customer = request.user
            pickup.save()
            messages.success(request, 'Pickup request submitted. We will notify you once assigned.')
            return redirect('pickup_history')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = PickupRequestForm()

    context = {
        'form':            form,
        'waste_categories': WasteCategory.objects.filter(is_active=True),
    }
    return render(request, 'core/request_pickup.html', context)


@login_required
def pickup_history(request):
    if request.user.role != 'customer':
        return HttpResponseForbidden('Only customers can view history.')

    pickups_all = (
        PickupRequest.objects
        .filter(customer=request.user)
        .order_by('-created_at')
    )
    paginator = Paginator(pickups_all, 10)
    pickups_page = paginator.get_page(request.GET.get('page'))

    total_earnings = sum(
        p.actual_price() for p in pickups_all
        if p.status == 'completed' and p.actual_weight_kg
    )

    context = {
        'pickups':        pickups_page,
        'total_pickups':  pickups_all.count(),
        'total_earnings': total_earnings,
    }
    return render(request, 'core/pickup_history.html', context)


@login_required
def cancel_pickup(request, pickup_id):
    if request.user.role != 'customer':
        return HttpResponseForbidden('Only customers can cancel pickups.')

    pickup = get_object_or_404(PickupRequest, id=pickup_id, customer=request.user)
    if pickup.status in ('pending', 'assigned'):
        pickup.status = 'cancelled'
        pickup.save()
        messages.success(request, 'Pickup request cancelled.')
    else:
        messages.error(request, 'Cannot cancel a pickup in its current status.')
    return redirect('pickup_history')


# ────────────────────────────────────────────────────────────
# COLLECTOR VIEWS
# ────────────────────────────────────────────────────────────
@login_required
def collector_dashboard(request):
    if request.user.role != 'collector':
        return HttpResponseForbidden('Access denied.')

    assigned = PickupRequest.objects.filter(collector=request.user).order_by('pickup_date')
    available = (
        PickupRequest.objects
        .filter(status='pending', collector__isnull=True)
        .order_by('pickup_date')[:10]
    )
    today_pickups = assigned.filter(pickup_date=timezone.now().date())

    completed = assigned.filter(status='completed')
    total_earnings = sum(p.actual_price() * 0.10 for p in completed)  # 10 % commission

    context = {
        'assigned_pickups':  assigned,
        'available_pickups': available,
        'today_pickups':     today_pickups,
        'total_earnings':    total_earnings,
        'completion_rate':   completed.count(),
    }
    return render(request, 'core/dashboard_collector.html', context)


@login_required
def assign_pickup(request, pickup_id):
    if request.user.role != 'collector':
        return HttpResponseForbidden('Only collectors can assign pickups.')

    pickup = get_object_or_404(
        PickupRequest,
        id=pickup_id,
        status='pending',
        collector__isnull=True
    )
    pickup.collector = request.user
    pickup.status = 'assigned'
    pickup.save()
    messages.success(request, f'Pickup assigned. Contact customer at {pickup.customer.phone or pickup.customer.email}.')
    return redirect('collector_dashboard')


@login_required
def update_pickup(request, pickup_id):
    if request.user.role != 'collector':
        return HttpResponseForbidden('Only collectors can update pickups.')

    pickup = get_object_or_404(PickupRequest, id=pickup_id, collector=request.user)

    if request.method == 'POST':
        form = CollectorUpdateForm(request.POST, instance=pickup)
        if form.is_valid():
            updated = form.save()
            if updated.status == 'completed' and updated.actual_weight_kg:
                Transaction.objects.update_or_create(
                    pickup_request=updated,
                    defaults={
                        'amount':     updated.actual_price(),
                        'is_paid':    True,
                    }
                )
                impact, _ = RecyclingImpact.objects.get_or_create(user=updated.customer)
                impact.update_impact()

                updated.completed_at = timezone.now()
                updated.save()
                messages.success(request, f'Pickup completed! Customer payment: Rs.{updated.actual_price():.2f}')
            else:
                messages.success(request, 'Pickup updated.')
            return redirect('collector_dashboard')
        messages.error(request, 'Please fix the form errors.')
    else:
        form = CollectorUpdateForm(instance=pickup)

    return render(request, 'core/update_pickup.html', {'form': form, 'pickup': pickup})


# ────────────────────────────────────────────────────────────
# ADMIN DASHBOARD
# ────────────────────────────────────────────────────────────
@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        return HttpResponseForbidden('Access denied.')

    user_stats = {
        'total':     User.objects.count(),
        'customers': User.objects.filter(role='customer').count(),
        'collectors': User.objects.filter(role='collector').count(),
        'admins':    User.objects.filter(role='admin').count(),
    }

    pickup_stats = {
        'total':      PickupRequest.objects.count(),
        'pending':    PickupRequest.objects.filter(status='pending').count(),
        'completed':  PickupRequest.objects.filter(status='completed').count(),
        'this_month': PickupRequest.objects.filter(
            created_at__month=timezone.now().month
        ).count(),
    }

    completed_pickups = PickupRequest.objects.filter(
        status='completed',
        actual_weight_kg__isnull=False
    )
    total_transactions = completed_pickups.aggregate(
        total=Sum('actual_weight_kg')
    )['total'] or 0

    context = {
        'user_stats':         user_stats,
        'pickup_stats':       pickup_stats,
        'total_transactions': total_transactions,
        'recent_pickups':     PickupRequest.objects.order_by('-created_at')[:10],
        'recent_users':       User.objects.order_by('-date_joined')[:5],
        'waste_categories':   WasteCategory.objects.all(),
    }
    return render(request, 'core/dashboard_admin.html', context)


# ────────────────────────────────────────────────────────────
# API ENDPOINT
# ────────────────────────────────────────────────────────────
def waste_categories_api(request):
    data = WasteCategory.objects.filter(is_active=True).values(
        'id', 'name', 'rate_per_kg', 'description'
    )
    return JsonResponse(list(data), safe=False)

import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@login_required
def initiate_payment(request, pickup_id):
    """Initiate payment for completed pickup"""
    pickup = get_object_or_404(PickupRequest, id=pickup_id, customer=request.user)
    
    if pickup.status != 'completed':
        messages.error(request, 'Payment can only be made for completed pickups.')
        return redirect('pickup_history')
    
    # Create or get transaction
    transaction, created = Transaction.objects.get_or_create(
        pickup_request=pickup,
        defaults={
            'amount': pickup.actual_price(),
            'payment_method': 'digital',
            'payment_gateway': 'esewa'  # or user's choice
        }
    )
    
    context = {
        'transaction': transaction,
        'pickup': pickup,
        'esewa_merchant_id': settings.ESEWA_MERCHANT_ID,
        'success_url': settings.PAYMENT_SUCCESS_URL,
        'failure_url': settings.PAYMENT_FAILURE_URL,
    }
    
    return render(request, 'core/payment_form.html', context)

@csrf_exempt
def payment_success(request):
    """Handle successful payment callback"""
    if request.method == 'POST':
        # Get transaction details from POST data
        transaction_id = request.POST.get('oid')  # eSewa transaction ID
        ref_id = request.POST.get('refId')  # eSewa reference ID
        
        try:
            transaction = Transaction.objects.get(id=transaction_id)
            transaction.is_paid = True
            transaction.payment_status = 'success'
            transaction.gateway_transaction_id = ref_id
            transaction.gateway_response = request.POST.dict()
            transaction.save()
            
            messages.success(request, f'Payment successful! Amount: Rs.{transaction.amount}')
            return redirect('pickup_history')
            
        except Transaction.DoesNotExist:
            messages.error(request, 'Invalid transaction.')
            return redirect('pickup_history')
    
    return redirect('pickup_history')

@csrf_exempt
def payment_failure(request):
    """Handle failed payment callback"""
    messages.error(request, 'Payment failed. Please try again.')
    return redirect('pickup_history')
from django.conf import settings