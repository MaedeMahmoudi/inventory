from django.db import models
from django.utils import timezone
from datetime import date


class UnitOfMeasure(models.Model):
    """واحدهای اندازه‌گیری (کیلوگرم، عدد، جعبه، لیتر)"""
    CATEGORY_CHOICES = [
        ('weight', 'وزن'),
        ('quantity', 'تعداد'),
        ('volume', 'حجم'),
    ]
    name = models.CharField(max_length=50, verbose_name="نام واحد")
    code = models.CharField(max_length=10, unique=True, verbose_name="کد واحد")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="دسته واحد")
    description = models.TextField(blank=True, verbose_name="توضیحات")

    def __str__(self):
        return f"{self.name} ({self.code})"


class UnitConversion(models.Model):
    """تبدیل بین واحدهای مختلف"""
    from_unit = models.ForeignKey(UnitOfMeasure, on_delete=models.CASCADE, related_name='from_conversions')
    to_unit = models.ForeignKey(UnitOfMeasure, on_delete=models.CASCADE, related_name='to_conversions')
    factor = models.DecimalField(max_digits=20, decimal_places=6, verbose_name="ضریب تبدیل")
    description = models.TextField(blank=True, verbose_name="توضیح تبدیل")

    def __str__(self):
        return f"1 {self.from_unit.code} = {self.factor} {self.to_unit.code}"


class Product(models.Model):
    CATEGORY_CHOICES = [
        ('yogurt', 'ماست'),
        ('milk', 'شیر'),
        ('cheese', 'پنیر'),
        ('butter', 'کره'),
        ('dough', 'دوغ'),
        ('icecream', 'بستنی'),
        ('cream', 'خامه'),
    ]

    name = models.CharField(max_length=200, verbose_name="نام محصول")
    code = models.CharField(max_length=50, unique=True, verbose_name="کد محصول")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="دسته بندی")
    base_uom = models.ForeignKey(UnitOfMeasure, on_delete=models.CASCADE, verbose_name="واحد پایه")
    default_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="قیمت پیش فرض")
    shelf_life_days = models.IntegerField(verbose_name="عمر مفید (روز)")
    storage_temp_min = models.IntegerField(verbose_name="حداقل دمای نگهداری")
    storage_temp_max = models.IntegerField(verbose_name="حداکثر دمای نگهداری")
    description = models.TextField(blank=True, verbose_name="توضیحات")

    def __str__(self):
        return f"{self.name} ({self.code})"


class AutoDiscountRule(models.Model):
    """قانون تخفیف خودکار برای کالاهای نزدیک به انقضا"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='discount_rules')
    threshold_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name="آستانه درصد باقی مانده از عمر",
        help_text="مثلاً 20 یعنی وقتی 20% از عمر محصول باقی مونده، این تخفیف اعمال شود"
    )
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="درصد تخفیف")
    priority = models.IntegerField(default=1, verbose_name="اولویت")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    reason = models.CharField(max_length=200, blank=True, verbose_name="دلیل تخفیف")
    description = models.TextField(blank=True, verbose_name="توضیحات")

    def __str__(self):
        return f"{self.product.name}: کمتر از {self.threshold_percent}% = {self.discount_percent}% تخفیف"

    class Meta:
        ordering = ['product', 'priority', 'threshold_percent']


# ==================== انبارها و سوله‌ها ====================

class Warehouse(models.Model):
    """انبار اصلی - می‌تواند شامل چندین سوله/بخش باشد"""
    TYPE_CHOICES = [
        ('cold', 'سردخانه'),
        ('dry', 'انبار خشک'),
        ('raw', 'انبار مواد اولیه'),
        ('packaging', 'انبار بسته‌بندی'),
        ('distribution', 'انبار توزیع'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='نام انبار')
    location = models.CharField(max_length=300, blank=True, verbose_name="آدرس")
    warehouse_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='dry', verbose_name="نوع انبار")
    is_cold_storage = models.BooleanField(default=False, verbose_name="سردخانه؟")
    description = models.TextField(blank=True, verbose_name="توضیحات")

    def __str__(self):
        type_display = dict(self.TYPE_CHOICES).get(self.warehouse_type, '')
        return f"{self.name} ({type_display})"


class StorageZone(models.Model):
    """سوله/بخش/قفسه داخل انبار"""
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='zones', verbose_name="انبار")
    name = models.CharField(max_length=100, verbose_name="نام سوله/بخش")
    code = models.CharField(max_length=20, verbose_name="کد سوله")
    temperature_min = models.IntegerField(null=True, blank=True, verbose_name="دمای حداقل (درجه سانتی‌گراد)")
    temperature_max = models.IntegerField(null=True, blank=True, verbose_name="دمای حداکثر (درجه سانتی‌گراد)")
    capacity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="ظرفیت (کیلوگرم)")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    
    def __str__(self):
        return f"{self.warehouse.name} - {self.name} ({self.code})"
    
    class Meta:
        ordering = ['warehouse', 'code']


# ==================== موجودی و عملیات انبار ====================

class StockItem(models.Model):
    STATUS_CHOICES = [
        ('available', 'موجود - قابل فروش'),
        ('quarantined', 'قرنطینه - در انتظار تایید کیفیت'),
        ('blocked', 'بلوکه - غیرقابل فروش'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name="انبار")
    zone = models.ForeignKey(StorageZone, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="سوله/بخش")
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.CASCADE, verbose_name="واحد موجودی")
    batch_number = models.CharField(max_length=100, unique=True, verbose_name="شماره دسته")
    production_date = models.DateField(verbose_name="تاریخ تولید")
    expiry_date = models.DateField(verbose_name="تاریخ انقضا")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="موجودی")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="قیمت تمام شده")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', verbose_name="وضعیت")
    description = models.TextField(blank=True, verbose_name="توضیحات")

    def days_left(self):
        """روزهای باقی مانده تا انقضا"""
        return (self.expiry_date - date.today()).days

    def is_expiring_soon(self):
        """آیا در حال انقضاست؟ (کمتر از 7 روز مونده)"""
        days = (self.expiry_date - date.today()).days
        return 0 < days <= 7

    def is_expired(self):
        """آیا تاریخ گذشته؟"""
        return self.expiry_date < date.today()

    @property
    def total_value(self):
        return self.quantity * self.unit_price

    def __str__(self):
        zone_info = f" - {self.zone.name}" if self.zone else ""
        return f"{self.product.name} - {self.batch_number} - {self.quantity} {self.uom.code}{zone_info}"


class StockIn(models.Model):
    VOUCHER_TYPES = [
        ('purchase', 'خرید'),
        ('production', 'تولید داخلی'),
        ('transfer_in', 'انتقال از انبار دیگر'),
        ('return_from_customer', 'برگشت از مشتری'),
        ('inventory_addition', 'اضافات انبار'),
    ]

    reference_number = models.CharField(max_length=100, unique=True, verbose_name="شماره رسید")
    date = models.DateField(auto_now_add=True, verbose_name="تاریخ")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name="انبار")
    zone = models.ForeignKey(StorageZone, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="سوله/بخش")
    voucher_type = models.CharField(max_length=25, choices=VOUCHER_TYPES, default='purchase', verbose_name="نوع ورود")
    supplier = models.CharField(max_length=200, blank=True, verbose_name="تامین کننده")
    notes = models.TextField(blank=True, verbose_name="توضیحات")

    def __str__(self):
        return f"رسید {self.reference_number}"


class StockInItem(models.Model):
    stock_in = models.ForeignKey(StockIn, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.CASCADE, verbose_name="واحد ورودی")
    batch_number = models.CharField(max_length=100)
    production_date = models.DateField()
    expiry_date = models.DateField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="قیمت تمام شده")
    zone = models.ForeignKey(StorageZone, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="سوله مقصد")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        stock_item, created = StockItem.objects.get_or_create(
            batch_number=self.batch_number,
            defaults={
                'product': self.product,
                'warehouse': self.stock_in.warehouse,
                'zone': self.zone or self.stock_in.zone,
                'uom': self.uom,
                'production_date': self.production_date,
                'expiry_date': self.expiry_date,
                'quantity': self.quantity,
                'unit_price': self.unit_price,
                'status': 'available',
            }
        )
        if not created:
            stock_item.quantity += self.quantity
            stock_item.save()


class StockOut(models.Model):
    VOUCHER_TYPES = [
        ('sale', 'فروش'),
        ('transfer_out', 'انتقال به انبار دیگر'),
        ('return_to_supplier', 'برگشت به تامین کننده'),
        ('waste', 'ضایعات'),
        ('gift', 'هدیه/نمونه'),
        ('inventory_deficit', 'کسری انبار'),
    ]

    reference_number = models.CharField(max_length=100, unique=True, verbose_name="شماره فاکتور")
    date = models.DateField(auto_now_add=True, verbose_name="تاریخ")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name="انبار")
    voucher_type = models.CharField(max_length=25, choices=VOUCHER_TYPES, default='sale', verbose_name="نوع خروج")
    customer = models.CharField(max_length=200, verbose_name="مشتری")
    notes = models.TextField(blank=True, verbose_name="توضیحات")

    def __str__(self):
        return f"خروج {self.reference_number}"


class StockOutItem(models.Model):
    stock_out = models.ForeignKey(StockOut, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    uom = models.ForeignKey(UnitOfMeasure, on_delete=models.CASCADE, verbose_name="واحد خروجی")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_reason = models.CharField(max_length=100, blank=True)
    stock_items = models.ManyToManyField(StockItem, through='StockOutItemDetail')


class StockOutItemDetail(models.Model):
    stock_out_item = models.ForeignKey(StockOutItem, on_delete=models.CASCADE)
    stock_item = models.ForeignKey(StockItem, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.stock_item.quantity -= self.quantity
        self.stock_item.save()