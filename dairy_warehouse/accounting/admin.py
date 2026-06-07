from django.contrib import admin
from .models import InventoryTransaction, InventoryValuation


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ['stock_item', 'transaction_type', 'quantity', 'unit_price', 'total_value', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['stock_item__product__name', 'related_voucher']
    readonly_fields = ['total_value']
    date_hierarchy = 'created_at'


@admin.register(InventoryValuation)
class InventoryValuationAdmin(admin.ModelAdmin):
    list_display = ['valuation_date', 'total_value', 'total_quantity', 'calculation_method']
    list_filter = ['calculation_method', 'valuation_date']
    readonly_fields = ['created_at']