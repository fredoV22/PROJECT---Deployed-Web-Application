from django.contrib import admin
from .models import Category, Product, Stock, SerialNumber, Supplier

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at', 'updated_at')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'created_at')
    search_fields = ('name', 'contact_person', 'email', 'phone', 'address')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'supplier', 'unit', 'price', 'current_stock', 'restock_level', 'is_active', 'created_at')
    list_filter = ('category', 'supplier', 'unit', 'is_active', 'created_at')
    search_fields = ('name', 'sku', 'description')
    readonly_fields = ('created_at', 'updated_at', 'current_stock')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'sku', 'category', 'supplier', 'description')
        }),
        ('Details', {
            'fields': ('unit', 'price', 'image', 'is_active', 'restock_level')
        }),
        ('Stock Information', {
             'fields': ('current_stock',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'product', 'transaction_type', 'quantity', 'transaction_date')
    list_filter = ('transaction_type', 'transaction_date', 'product')
    search_fields = ('product__name', 'notes', 'reference_number')
    readonly_fields = ('created_at', 'reference_number')
    fieldsets = (
        ('Transaction Details', {
            'fields': ('product', 'transaction_type', 'quantity', 'reference_number')
        }),
        ('Additional Information', {
            'fields': ('notes', 'transaction_date', 'created_at')
        }),
    )

@admin.register(SerialNumber)
class SerialNumberAdmin(admin.ModelAdmin):
    list_display = ('product', 'serial_number', 'is_allocated', 'stock_in_transaction', 'stock_out_transaction', 'created_at')
    list_filter = ('product', 'is_allocated', 'created_at')
    search_fields = ('product__name', 'serial_number')
    readonly_fields = ('created_at', 'updated_at')
