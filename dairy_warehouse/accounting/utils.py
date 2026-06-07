from datetime import date, timedelta
from django.db.models import Sum
from inventory.models import StockItem
from .models import InventoryTransaction, InventoryValuation


def create_transaction(stock_item, transaction_type, quantity, unit_price, related_voucher, description=''):
    """ثبت یک تراکنش حسابداری جدید"""
    return InventoryTransaction.objects.create(
        stock_item=stock_item,
        transaction_type=transaction_type,
        quantity=quantity,
        unit_price=unit_price,
        total_value=quantity * unit_price,
        related_voucher=related_voucher,
        description=description
    )


def calculate_total_inventory_value():
    """محاسبه ارزش کل موجودی انبار در لحظه"""
    stock_items = StockItem.objects.filter(quantity__gt=0)
    total_value = sum(float(item.quantity) * float(item.unit_price) for item in stock_items)
    total_quantity = sum(float(item.quantity) for item in stock_items)
    return total_value, total_quantity


def create_daily_valuation():
    """ایجاد ارزش‌گذاری روزانه موجودی انبار"""
    total_value, total_quantity = calculate_total_inventory_value()
    today = date.today()
    
    valuation, created = InventoryValuation.objects.get_or_create(
        valuation_date=today,
        defaults={
            'total_value': total_value,
            'total_quantity': total_quantity,
            'calculation_method': 'fifo'
        }
    )
    
    if not created:
        valuation.total_value = total_value
        valuation.total_quantity = total_quantity
        valuation.save()
    
    return valuation


def get_profit_loss(from_date=None, to_date=None):
    """محاسبه سود و زیان در بازه زمانی مشخص"""
    if not from_date:
        from_date = date.today() - timedelta(days=30)
    if not to_date:
        to_date = date.today()
    
    # تراکنش‌های خروج (فروش)
    credit_transactions = InventoryTransaction.objects.filter(
        transaction_type='credit',
        created_at__date__gte=from_date,
        created_at__date__lte=to_date
    )
    
    total_revenue = sum(float(t.total_value) for t in credit_transactions)
    
    # ارزش تمام شده کالای فروش رفته
    total_cost = sum(float(t.quantity) * float(t.unit_price) for t in credit_transactions)
    
    profit = total_revenue - total_cost
    profit_margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return {
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'profit': profit,
        'profit_margin': profit_margin,
        'from_date': from_date,
        'to_date': to_date,
        'transaction_count': credit_transactions.count()
    }