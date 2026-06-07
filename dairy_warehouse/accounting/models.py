from django.db import models
from inventory.models import StockItem


class InventoryTransaction(models.Model):
    """تراکنش حسابداری انبار - هر تغییر در موجودی اینجا ثبت می‌شه"""
    TRANSACTION_TYPES = [
        ('debit', 'بدهکار (ورود)'),
        ('credit', 'بستانکار (خروج)'),
    ]
    
    stock_item = models.ForeignKey(StockItem, on_delete=models.CASCADE, verbose_name="قلم موجودی")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name="نوع تراکنش")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="تعداد")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="قیمت واحد")
    total_value = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="ارزش کل")
    related_voucher = models.CharField(max_length=100, verbose_name="شماره سند مرتبط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان")
    description = models.TextField(blank=True, verbose_name="توضیحات")

    def save(self, *args, **kwargs):
        self.total_value = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.stock_item.product.name} - {self.quantity}"

    class Meta:
        verbose_name = "Inventory Transaction"
        verbose_name_plural = "Inventory Transactions"
        ordering = ['-created_at']


class InventoryValuation(models.Model):
    """ارزش‌گذاری موجودی انبار در تاریخ‌های مختلف"""
    valuation_date = models.DateField(verbose_name="تاریخ ارزش‌گذاری")
    total_value = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="ارزش کل موجودی")
    total_quantity = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="کل تعداد")
    calculation_method = models.CharField(max_length=50, default='fifo', verbose_name="روش محاسبه")
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-valuation_date']
        verbose_name = "Inventory Valuation"
        verbose_name_plural = "Inventory Valuations"

    def __str__(self):
        return f"ارزش موجودی در {self.valuation_date}: {self.total_value:,.0f} ریال"