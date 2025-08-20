from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, WasteCategory, PickupRequest, Transaction, RecyclingImpact

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'phone', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'phone')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone', 'address')}),
    )

@admin.register(WasteCategory)
class WasteCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'rate_per_kg', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    list_editable = ('rate_per_kg', 'is_active')

@admin.register(PickupRequest)
class PickupRequestAdmin(admin.ModelAdmin):
    list_display = ('customer', 'waste_category', 'status', 'pickup_date', 'estimated_price', 'actual_price')
    list_filter = ('status', 'pickup_date', 'waste_category', 'created_at')
    search_fields = ('customer__username', 'address', 'collector__username')
    date_hierarchy = 'pickup_date'
    readonly_fields = ('estimated_price', 'actual_price', 'created_at')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('pickup_request', 'amount', 'payment_method', 'is_paid', 'transaction_date')
    list_filter = ('is_paid', 'payment_method', 'transaction_date')
    search_fields = ('pickup_request__customer__username',)

@admin.register(RecyclingImpact)
class RecyclingImpactAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_weight_recycled', 'trees_saved', 'co2_reduced', 'water_saved', 'last_updated')
    search_fields = ('user__username',)
    readonly_fields = ('last_updated',)
