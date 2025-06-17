from django import forms
from .models import Category, Product, Stock, SerialNumber, Supplier
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class ProductForm(forms.ModelForm):
    initial_stock = forms.IntegerField(label="Initial Stock Quantity", required=False, initial=0, validators=[MinValueValidator(0)])
    
    class Meta:
        model = Product
        fields = ['name', 'category', 'supplier', 'description', 'unit', 'price', 'image', 'is_active', 'restock_level']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['product', 'transaction_type', 'quantity', 'notes', 'transaction_date', 'expiry_date']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'transaction_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        quantity = cleaned_data.get('quantity')
        product = cleaned_data.get('product')

        if transaction_type == 'out' and quantity is not None and product is not None:
            current_stock = product.current_stock()

            if quantity > current_stock:
                raise ValidationError(
                    f"Cannot stock out {quantity} units. Only {current_stock} units are currently in stock for {product.name}."
                )

        return cleaned_data 