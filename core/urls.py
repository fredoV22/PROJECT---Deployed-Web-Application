from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page_view, name='landing_page'),
    path('dashboard/', views.dashboard_overview, name='dashboard'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.ProductCreateView.as_view(), name='product_add'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),

    path('stock/record/', views.record_stock_transaction, name='record_stock_transaction'),
    path('stock/add/', views.StockCreateView.as_view(), name='stock_add'),
    path('stock/<int:pk>/edit/', views.StockUpdateView.as_view(), name='stock_edit'),
    path('stock/<int:pk>/delete/', views.StockDeleteView.as_view(), name='stock_delete'),
    path('stock/get-stock/<int:product_id>/', views.get_product_current_stock, name='get_product_stock'),
    path('stock/get-product-by-sku/', views.get_product_by_sku, name='get_product_by_sku'),
    path('products/suggestions/', views.get_product_suggestions, name='get_product_suggestions'),

    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/add/', views.SupplierCreateView.as_view(), name='supplier_add'),
    path('suppliers/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier_delete'),

    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/transactions/', views.transaction_report, name='transaction_report'),
    path('reports/transactions/print/', views.print_transaction_report, name='print_transaction_report'),
    path('receipt/<int:transaction_id>/print/', views.receipt_print_view, name='receipt_print'),
    path('receipt/lookup/', views.receipt_lookup_view, name='receipt_lookup'),
    path('receipt/save/', views.save_receipt_view, name='save_receipt'),
    path('receipt/generate-pdf/', views.generate_receipt_pdf, name='generate_receipt_pdf'),
] 