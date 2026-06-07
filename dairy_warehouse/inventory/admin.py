from django.contrib import admin
from .models import (
    Warehouse, 
    Product, 
    UnitOfMeasure, 
    UnitConversion, 
    AutoDiscountRule, 
    StockItem, 
    StockIn, 
    StockInItem, 
    StockOut, 
    StockOutItem
)

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'is_cold_storage']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'base_uom', 'default_price']
    search_fields = ['name', 'code']
    list_filter = ['category']

@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category']
    search_fields = ['name', 'code']

@admin.register(UnitConversion)
class UnitConversionAdmin(admin.ModelAdmin):
    list_display = ['from_unit', 'to_unit', 'factor']

@admin.register(AutoDiscountRule)
class AutoDiscountRuleAdmin(admin.ModelAdmin):
    list_display = ['product', 'threshold_percent', 'discount_percent', 'is_active']
    list_filter = ['is_active', 'product']

@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'batch_number', 'quantity', 'expiry_date', 'status']
    list_filter = ['status', 'warehouse', 'product']
    search_fields = ['batch_number']

@admin.register(StockIn)
class StockInAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'date', 'warehouse', 'voucher_type', 'supplier']
    list_filter = ['voucher_type', 'warehouse', 'date']

@admin.register(StockInItem)
class StockInItemAdmin(admin.ModelAdmin):
    list_display = ['stock_in', 'product', 'batch_number', 'quantity', 'unit_price']

@admin.register(StockOut)
class StockOutAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'date', 'warehouse', 'voucher_type', 'customer']
    list_filter = ['voucher_type', 'warehouse', 'date']

@admin.register(StockOutItem)
class StockOutItemAdmin(admin.ModelAdmin):
    list_display = ['stock_out', 'product', 'quantity', 'discount_percent']