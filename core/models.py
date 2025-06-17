from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import Sum, Max

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    UNIT_CHOICES = [
        ('piece', 'Piece'),
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('l', 'Liter'),
        ('ml', 'Milliliter'),
        ('box', 'Box'),
        ('pack', 'Pack'),
    ]

    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='piece')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    restock_level = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Minimum stock quantity to trigger a reorder.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def current_stock(self):
        """Calculate current stock level for the product based on transactions"""
        stock_in = self.stock_movements.filter(
            transaction_type__in=['in', 'adjustment']
        ).aggregate(total=Sum('quantity'))['total'] or 0

        stock_out = self.stock_movements.filter(
            transaction_type='out'
        ).aggregate(total=Sum('quantity'))['total'] or 0

        return max(0, stock_in - stock_out)

class Stock(models.Model):
    TRANSACTION_TYPES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Adjustment'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    reference_number = models.CharField(max_length=50, blank=True, null=True, help_text="Optional reference for the transaction, e.g., receipt number.")
    notes = models.TextField(blank=True)
    transaction_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateField(blank=True, null=True, help_text="Expiry date of the batch")
    client_name = models.CharField(max_length=200, blank=True, null=True, help_text="Name of the client for this transaction.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['reference_number']
        verbose_name_plural = "Stock Transactions"

    def __str__(self):
        if self.reference_number:
            return f"#{self.reference_number} - {self.product.name} - {self.get_transaction_type_display()} ({self.quantity})"
        return f"{self.product.name} - {self.get_transaction_type_display()} ({self.quantity}) - No Reference #"

class Sale(models.Model):
    client_name = models.CharField(max_length=200, blank=True, null=True)
    sale_date = models.DateTimeField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Add other fields like user who made the sale, payment method, etc., if needed

    class Meta:
        ordering = ['-sale_date']

    def __str__(self):
        return f"Sale on {self.sale_date.strftime('%Y-%m-%d %H:%M')}" + (f" for {self.client_name}" if self.client_name else "")

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sale_items')
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2) # Store price at the time of sale

    class Meta:
        # Ensure a product is not added twice to the same sale (optional, can be handled in logic)
        # unique_together = ('sale', 'product')
        pass

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Sale #{self.sale.id}"

    def get_total(self):
        return self.quantity * self.price_at_sale

# We may need to adjust the Stock model or create Stock entries when a SaleItem is created/saved
# This is a crucial part of linking sales to inventory management.
# We can implement this logic in the SaleItem save method or in the view that processes the sale.

class SerialNumber(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='serial_numbers')
    serial_number = models.CharField(max_length=255, unique=True)
    is_allocated = models.BooleanField(default=False, help_text="Indicates if the serial number is allocated to an order or stock out transaction.")
    stock_in_transaction = models.ForeignKey(Stock, on_delete=models.SET_NULL, null=True, blank=True, related_name='serial_numbers_in', help_text="Stock transaction that brought this serial number into inventory.")
    stock_out_transaction = models.ForeignKey(Stock, on_delete=models.SET_NULL, null=True, blank=True, related_name='serial_numbers_out', help_text="Stock transaction that took this serial number out of inventory.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['serial_number']
        verbose_name_plural = "Serial Numbers"

    def __str__(self):
        return f"{self.product.name} - {self.serial_number}"
