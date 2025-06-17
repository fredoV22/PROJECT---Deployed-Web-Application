from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView
from django.db.models import Sum, Q, Max, Min, F, Case, When, Value, IntegerField, ExpressionWrapper, DecimalField
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.utils import timezone
from datetime import date, timedelta # Import date and timedelta
from django.http import JsonResponse # Import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from xhtml2pdf import pisa # Import pisa for PDF generation
from io import BytesIO # Import BytesIO for handling PDF in memory
from django.template.loader import get_template # Import get_template
from django.http import HttpResponse # Import HttpResponse
import uuid # Import uuid for generating unique IDs
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Category, Product, Stock, SerialNumber, Supplier
from .forms import CategoryForm, ProductForm, StockForm, SupplierForm

def home_redirect(request):
    return redirect('dashboard')

def is_admin(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'admin'

def dashboard_overview(request):
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_suppliers = Supplier.objects.count() # Get total suppliers

    # Calculate income for today and this month
    today = timezone.now().date()
    start_of_month = today.replace(day=1)

    # Daily Income
    daily_income = 0
    # Filter 'out' transactions for today
    daily_sales = Stock.objects.filter(
        transaction_type='out',
        transaction_date__date=today # Filter by date part
    )
    # Calculate income by multiplying quantity by product price for each sale
    for sale in daily_sales:
        if sale.product and sale.product.price is not None:
            daily_income += sale.quantity * sale.product.price

    # Monthly Income
    monthly_income = 0
    # Filter 'out' transactions for this month
    monthly_sales = Stock.objects.filter(
        transaction_type='out',
        transaction_date__gte=start_of_month, # Greater than or equal to the start of the month
        transaction_date__lt=today + timedelta(days=1) # Less than the start of tomorrow
    )
    # Calculate income
    for sale in monthly_sales:
         if sale.product and sale.product.price is not None:
            monthly_income += sale.quantity * sale.product.price


    # Fetch recent activities from different models
    recent_stocks = Stock.objects.order_by('-transaction_date')[:20]
    recent_categories = Category.objects.order_by('-created_at')[:5]
    recent_suppliers = Supplier.objects.order_by('-created_at')[:5]
    recent_products = Product.objects.order_by('-created_at')[:5]

    # Combine and sort all recent activities by date
    # We need a way to consistently get the date from each object type
    # Assuming 'created_at' for Category, Supplier, Product and 'transaction_date' for Stock
    # If these fields don't exist or have different names, this will need adjustment
    all_recent_activities = list(recent_stocks) + list(recent_categories) + list(recent_suppliers) + list(recent_products)

    # Sort by date in descending order (most recent first)
    # This assumes each object has a date attribute like 'transaction_date' or 'created_at'
    def get_activity_date(activity):
        if isinstance(activity, Stock):
            return activity.transaction_date
        # Assuming 'created_at' for other models. Adjust if necessary.
        return activity.created_at if hasattr(activity, 'created_at') else timezone.now()

    all_recent_activities.sort(key=get_activity_date, reverse=True)

    # Limit the total number of items in the history
    TRANSACTION_HISTORY_LIMIT = 15
    transaction_history = all_recent_activities[:TRANSACTION_HISTORY_LIMIT]

    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_suppliers': total_suppliers, # Add total suppliers to context
        'daily_income': daily_income, # Add daily income to context
        'monthly_income': monthly_income, # Add monthly income to context
        'transaction_history': transaction_history, # Pass the combined and sorted list
    }
    return render(request, 'core/dashboard.html', context)

def landing_page_view(request):
    return render(request, 'core/landing_page.html')

def product_list(request):
    products = Product.objects.all()
    categories = Category.objects.all()

    # Filtering by category
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category__id=category_id)

    # Searching
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Annotate with current_stock_value for sorting
    products = products.annotate(
        stock_in_sum=Sum('stock_movements__quantity', filter=Q(stock_movements__transaction_type__in=['in', 'adjustment'])),
        stock_out_sum=Sum('stock_movements__quantity', filter=Q(stock_movements__transaction_type='out'))
    ).annotate(
        current_stock_value=Case(
            When(stock_in_sum__isnull=True, then=Value(0)),
            default=F('stock_in_sum') - F('stock_out_sum'),
            output_field=IntegerField()
        )
    )
    
    # Annotate with earliest_expiry_date for sorting
    products = products.annotate(
        earliest_expiry_date=Min('stock_movements__expiry_date', filter=Q(stock_movements__expiry_date__gte=timezone.now().date()))
    )

    # Sorting
    sort_by = request.GET.get('sort_by', 'name') # Default sort by name
    allowed_sort_fields = ['name', 'sku', 'category', 'price', 'restock_level', 'low_stock', 'near_expiration']

    if sort_by == 'low_stock':
        # Sort by current stock value ascending, then by name
        products = products.order_by('current_stock_value', 'name')
    elif sort_by == 'near_expiration':
        # Sort by earliest expiry date ascending, then by name (nulls last for expiry)
        products = products.order_by(F('earliest_expiry_date').asc(nulls_last=True), 'name')
    elif sort_by in allowed_sort_fields:
        products = products.order_by(sort_by)

    context = {
        'products': products,
        'categories': categories,
        'selected_category': category_id,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'core/product_list.html', context)

def low_stock_report(request):
    # Define a simple low stock threshold (e.g., 10 units)
    LOW_STOCK_THRESHOLD = 10 # Consider making this configurable later

    low_stock_products = []
    for product in Product.objects.filter(is_active=True):
        if product.current_stock() <= product.restock_level:
             low_stock_products.append({
                'product': product,
                'current_stock': product.current_stock(),
                'restock_level': product.restock_level
            })

    context = {
        'low_stock_products': low_stock_products,
        'low_stock_threshold': LOW_STOCK_THRESHOLD, # Still show threshold in template
    }
    return render(request, 'core/low_stock_report.html', context)

def stock_value_report(request):
    total_stock_value = 0
    for product in Product.objects.filter(is_active=True):
        current_stock = product.current_stock()
        product_value = current_stock * (product.price or 0)
        total_stock_value += product_value

    context = {
        'total_stock_value': total_stock_value
    }
    return render(request, 'core/stock_value_report.html', context)

def sales_report(request):
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday()) # Monday as start of week
    start_of_month = today.replace(day=1)

    # Daily Sales
    daily_sales_data = Stock.objects.filter(
        transaction_type='out',
        transaction_date__date=today
    ).aggregate(total_daily_sales=Sum(F('quantity') * F('product__price')))
    daily_total = daily_sales_data['total_daily_sales'] or 0

    # Weekly Sales
    weekly_sales_data = Stock.objects.filter(
        transaction_type='out',
        transaction_date__date__gte=start_of_week,
        transaction_date__date__lte=today
    ).aggregate(total_weekly_sales=Sum(F('quantity') * F('product__price')))
    weekly_total = weekly_sales_data['total_weekly_sales'] or 0

    # Monthly Sales
    monthly_sales_data = Stock.objects.filter(
        transaction_type='out',
        transaction_date__date__gte=start_of_month,
        transaction_date__date__lte=today
    ).aggregate(total_monthly_sales=Sum(F('quantity') * F('product__price')))
    monthly_total = monthly_sales_data['total_monthly_sales'] or 0

    context = {
        'daily_total': daily_total,
        'weekly_total': weekly_total,
        'monthly_total': monthly_total,
        'today': today,
        'start_of_week': start_of_week,
        'start_of_month': start_of_month,
    }
    return render(request, 'core/sales_report.html', context)

def transaction_report(request):
    transactions_list = Stock.objects.all().order_by('-transaction_date')

    # Add current_stock to each transaction for display
    for transaction in transactions_list:
        if transaction.product:
            transaction.remaining_stock = transaction.product.current_stock()
        else:
            transaction.remaining_stock = "N/A"

    paginator = Paginator(transactions_list, 10)  # Show 10 transactions per page

    page = request.GET.get('page')
    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        transactions = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        transactions = paginator.page(paginator.num_pages)

    context = {
        'transactions': transactions
    }
    return render(request, 'core/transaction_report.html', context)

def print_transaction_report(request):
    time_range = request.GET.get('range', 'all')
    transactions = Stock.objects.all().order_by('-transaction_date')

    today = timezone.localdate()

    if time_range == 'daily':
        transactions = transactions.filter(transaction_date__date=today)
    elif time_range == 'weekly':
        start_of_week = today - timedelta(days=today.weekday())
        transactions = transactions.filter(transaction_date__date__gte=start_of_week, transaction_date__date__lte=today)
    elif time_range == 'monthly':
        start_of_month = today.replace(day=1)
        transactions = transactions.filter(transaction_date__date__gte=start_of_month, transaction_date__date__lte=today)
    # 'all' is default, no additional filtering needed

    # Add current_stock to each transaction for display in the printout
    for transaction in transactions:
        if transaction.product:
            transaction.remaining_stock = transaction.product.current_stock()
        else:
            transaction.remaining_stock = "N/A"

    context = {
        'transactions': transactions,
        'report_range': time_range.replace('_', ' ').title() # For displaying in the report title
    }
    return render(request, 'core/transaction_report_print.html', context)

def record_stock_transaction(request):
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            stock_transaction = form.save(commit=False)
            stock_transaction.transaction_date = timezone.now()
            stock_transaction.save()
            # Redirect to the product detail page for the newly created transaction
            return redirect('product_detail', pk=stock_transaction.product.pk)
    else:
        form = StockForm(initial={'transaction_date': timezone.now()})
    return render(request, 'core/record_stock_transaction.html', {'form': form})

# View to get current stock for a product (for AJAX call)
def get_product_current_stock(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    current_stock = product.current_stock()
    return JsonResponse({'current_stock': current_stock})

# View to get product details by SKU (for scanner input and potential pre-filling)
def get_product_by_sku(request):
    sku = request.GET.get('sku')
    if sku:
        try:
            product = Product.objects.get(sku=sku)
            # Return more product details
            data = {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'description': product.description,
                'unit': product.unit,
                'price': str(product.price), # Convert Decimal to string for JSON
                'category_id': product.category.id if product.category else None,
                'supplier_id': product.supplier.id if product.supplier else None,
                'restock_level': product.restock_level,
            }
            return JsonResponse(data)
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
    return JsonResponse({'error': 'SKU not provided'}, status=400)

def category_list(request):
    categories = Category.objects.all()
    return render(request, 'core/category_list.html', {'categories': categories})

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'core/product_detail.html', {'product': product})

class SupplierListView(ListView):
    model = Supplier
    template_name = 'core/supplier_list.html'
    context_object_name = 'suppliers'
    ordering = ['name']

class SupplierCreateView(CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'core/supplier_form.html'
    success_url = reverse_lazy('supplier_list')

class SupplierUpdateView(UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'core/supplier_form.html'
    success_url = reverse_lazy('supplier_list')

class SupplierDeleteView(DeleteView):
    model = Supplier
    template_name = 'core/supplier_confirm_delete.html'
    success_url = reverse_lazy('supplier_list')

class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'core/category_form.html'
    success_url = reverse_lazy('category_list')

class CategoryUpdateView(UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'core/category_form.html'
    success_url = reverse_lazy('category_list')

class CategoryDeleteView(DeleteView):
    model = Category
    template_name = 'core/category_confirm_delete.html'
    success_url = reverse_lazy('category_list')

class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'core/product_form.html'
    success_url = reverse_lazy('product_list')

    def form_valid(self, form):
        # Save the product first
        response = super().form_valid(form)

        # Get the initial stock quantity from the form
        initial_stock_quantity = form.cleaned_data.get('initial_stock')

        # If initial stock is provided and greater than 0, create a Stock transaction
        if initial_stock_quantity is not None and initial_stock_quantity > 0:
            Stock.objects.create(
                product=self.object, # The newly created product
                transaction_type='in',
                quantity=initial_stock_quantity,
                transaction_date=timezone.now(),
                notes='Initial stock on product creation'
            )

        return response

class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'core/product_form.html'
    success_url = reverse_lazy('product_list')

class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'core/product_confirm_delete.html'
    success_url = reverse_lazy('product_list')

@method_decorator(login_required, name='dispatch')
class StockCreateView(CreateView):
    model = Stock
    form_class = StockForm
    template_name = 'core/stock_form.html'
    success_url = reverse_lazy('product_list') # Or redirect to product detail page? Let's start with product list.

class StockUpdateView(UpdateView):
    model = Stock
    form_class = StockForm
    template_name = 'core/stock_form.html'
    success_url = reverse_lazy('product_list') # Or redirect to product detail page?

class StockDeleteView(DeleteView):
    model = Stock
    form_class = StockForm
    template_name = 'core/stock_confirm_delete.html'
    success_url = reverse_lazy('product_list') # Or redirect to product detail page?

def receipt_print_view(request, transaction_id):
    stock_transaction = get_object_or_404(Stock, pk=transaction_id)
    context = {
        'stock_transaction': stock_transaction
    }
    return render(request, 'core/receipt_print.html', context)

def receipt_lookup_view(request):
    receipt_data = None
    if request.method == 'POST':
        try:
            # Assuming data is sent as JSON from the frontend
            data = json.loads(request.body)
            customer_name = data.get('customer_name', '')
            items_from_request = data.get('items', [])

            processed_items = []
            grand_total = 0
            errors = []

            for item_data in items_from_request:
                item_name = item_data.get('item_name', '')
                requested_quantity = float(item_data.get('quantity', 0))
                price = float(item_data.get('price', 0))
                unit = item_data.get('unit', '')
                product_id = item_data.get('product_id')

                actual_quantity_for_receipt = requested_quantity
                # Perform stock check if product_id is available
                if product_id:
                    try:
                        product = Product.objects.get(id=product_id)
                        current_stock = product.current_stock()

                        if requested_quantity > current_stock:
                            actual_quantity_for_receipt = max(0, current_stock) # Ensure it's not negative
                            if current_stock <= 0:
                                errors.append(f"'{item_name}' is out of stock. Quantity set to 0.")
                            else:
                                errors.append(f"Only {current_stock} unit(s) of '{item_name}' available. Quantity adjusted to {current_stock}.")

                    except Product.DoesNotExist:
                        errors.append(f"Product with ID {product_id} ('{item_name}') not found in inventory.")

                item_total = actual_quantity_for_receipt * price
                grand_total += item_total

                processed_items.append({
                    'item_name': item_name,
                    'quantity': actual_quantity_for_receipt,
                    'price': price,
                    'unit': unit,
                    'item_total': item_total,
                })
            
            receipt_data = {
                'customer_name': customer_name,
                'items': processed_items,
                'grand_total': grand_total,
                'errors': errors # Pass errors to the template
            }
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            receipt_data = {'error': f'Invalid data submitted: {e}'}

    context = {
        'receipt_data': receipt_data,
        'products': Product.objects.all() # Pass all products to the template
    }
    return render(request, 'core/receipt_lookup.html', context)

@csrf_exempt # For simplicity in this example, consider more secure CSRF handling for production
def save_receipt_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_name = data.get('customer_name', '')
            items_to_save = data.get('items', [])

            if not items_to_save:
                return JsonResponse({'status': 'error', 'message': 'No items to save in the receipt.'}, status=400)

            # Generate a unique receipt reference for this entire sale
            receipt_reference = f"SALE-{timezone.now().strftime("%Y%m%d%H%M%S")}-{uuid.uuid4().hex[:6].upper()}"

            transactions_created = []
            errors = []

            for item_data in items_to_save:
                product_id = item_data.get('product_id')
                quantity = item_data.get('quantity')
                item_name = item_data.get('item_name')
                # unit = item_data.get('unit') # Not directly used in Stock model but can be kept for notes if desired
                # price = item_data.get('price') # Not directly used in Stock model but relevant for SaleItem if created

                if not all([product_id, quantity]):
                    errors.append(f"Missing data for item: {item_data.get('item_name', 'Unknown Item')}")
                    continue

                try:
                    product = Product.objects.get(id=product_id)
                    # Check if enough stock is available before creating an 'out' transaction
                    if product.current_stock() >= quantity:
                        stock_transaction = Stock.objects.create(
                            product=product,
                            transaction_type='out',
                            quantity=quantity,
                            reference_number=receipt_reference, # Assign the common receipt reference
                            notes=f'Sale to {customer_name or "Customer"} (Receipt: {receipt_reference})',
                            transaction_date=timezone.now(),
                            client_name=customer_name, # Assign the customer name here
                        )
                        transactions_created.append({
                            'product_name': product.name,
                            'quantity': quantity,
                            'transaction_id': stock_transaction.pk,
                            'receipt_reference': receipt_reference # Add to response for debugging/info
                        })
                    else:
                        errors.append(f"Insufficient stock for {item_name}. Available: {product.current_stock()}, Requested: {quantity}.")
                except Product.DoesNotExist:
                    errors.append(f"Product ' {item_name}' (ID: {product_id}) not found.")
                except Exception as e:
                    errors.append(f"Error processing item {item_name}: {str(e)}")
            
            if errors:
                return JsonResponse({'status': 'warning', 'message': 'Receipt saved with some issues.', 'details': errors, 'transactions': transactions_created, 'receipt_reference': receipt_reference}, status=200)
            else:
                return JsonResponse({'status': 'success', 'message': 'Receipt saved successfully!', 'transactions': transactions_created, 'receipt_reference': receipt_reference}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

@csrf_exempt # For simplicity, consider more secure CSRF handling for production
def generate_receipt_pdf(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_name = data.get('customer_name', '')
            items_data = data.get('items', [])

            # Calculate total and prepare items for template
            grand_total = 0
            items_for_template = []
            for item in items_data:
                item_total = float(item.get('quantity', 0)) * float(item.get('price', 0))
                grand_total += item_total
                items_for_template.append({
                    'quantity': item.get('quantity'),
                    'unit': item.get('unit'),
                    'item_name': item.get('item_name'),
                    'price': float(item.get('price', 0)),
                    'item_total': item_total,
                })

            context = {
                'customer_name': customer_name,
                'items': items_for_template,
                'grand_total': grand_total,
                'receipt_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            template = get_template('core/receipt_pdf_template.html')
            html = template.render(context)
            result = BytesIO()

            pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

            if not pdf.err:
                response = HttpResponse(result.getvalue(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="receipt_{timezone.now().strftime("%Y%m%d%H%M%S")}.pdf"'
                return response
            return HttpResponse('We had some errors <pre>' + html + '</pre>', status=500)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

def get_product_suggestions(request):
    query = request.GET.get('query', '')
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(sku__icontains=query)
        ).values('id', 'name', 'price', 'unit').annotate(current_stock=F('stock_movements__quantity')).distinct() # Efficiently get current stock, though might need refinement if product has multiple stock entries for different batches. This is a simplification.
        
        # Manually calculate current_stock for each product to ensure accuracy
        products_data = []
        for product_dict in products:
            product_obj = Product.objects.get(id=product_dict['id'])
            products_data.append({
                'id': product_obj.id,
                'name': product_obj.name,
                'price': str(product_obj.price),
                'unit': product_obj.unit,
                'current_stock': product_obj.current_stock(),
            })
        
        return JsonResponse({'products': products_data})
    return JsonResponse({'products': []}) # Return empty list if no query
