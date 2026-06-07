from datetime import date
from .models import StockItem, AutoDiscountRule


def get_fefo_items(product, warehouse, requested_quantity):
    """
    دریافت بهترین دسته‌های کالا بر اساس FEFO
    اولویت: تاریخ انقضای نزدیک‌تر → زودتر خارج شود
    Returns: لیستی از آیتم‌ها با مقادیر دقیق برای خروج
    """
    available_items = StockItem.objects.filter(
        product=product,
        warehouse=warehouse,
        quantity__gt=0,
        expiry_date__gte=date.today(),
        status='available'
    ).order_by('expiry_date')
    
    selected_items = []
    remaining = requested_quantity
    
    for item in available_items:
        if remaining <= 0:
            break
            
        take_quantity = min(float(item.quantity), float(remaining))
        selected_items.append({
            'stock_item': item,
            'quantity': take_quantity,
            'expiry_date': item.expiry_date,
            'days_left': (item.expiry_date - date.today()).days,
            'unit_price': float(item.unit_price),
        })
        remaining -= take_quantity
    
    if remaining > 0:
        raise ValueError(
            f"موجودی کافی نیست! {remaining} واحد دیگر نیاز است."
        )
    
    return selected_items


def calculate_discount(stock_item):
    """محاسبه تخفیف خودکار بر اساس قوانین تعریف شده"""
    today = date.today()
    total_life = (stock_item.expiry_date - stock_item.production_date).days
    days_left = (stock_item.expiry_date - today).days
    
    if total_life <= 0 or days_left <= 0:
        return 0
    
    percent_left = (days_left / total_life) * 100
    
    rules = AutoDiscountRule.objects.filter(
        product=stock_item.product,
        is_active=True,
        threshold_percent__gte=percent_left
    ).order_by('priority')
    
    if rules.exists():
        return float(rules.first().discount_percent)
    
    return 0