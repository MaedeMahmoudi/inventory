from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from datetime import date
from django.http import JsonResponse
from .models import Warehouse, StorageZone

from .models import (
    StockIn, StockInItem, StockOut, StockOutItem, 
    StockOutItemDetail, StockItem, Warehouse, Product,
    UnitOfMeasure, AutoDiscountRule
)
from .utils import get_fefo_items, calculate_discount


@login_required
def dashboard(request):
    total_products = Product.objects.count()
    total_warehouses = Warehouse.objects.count()
    
    stock_items = StockItem.objects.filter(quantity__gt=0)
    total_inventory_value = sum(float(item.quantity) * float(item.unit_price) for item in stock_items)
    
    expiring_soon = []
    for item in stock_items:
        if item.is_expiring_soon():
            expiring_soon.append(item)
    
    context = {
        'total_products': total_products,
        'total_warehouses': total_warehouses,
        'total_inventory_value': total_inventory_value,
        'expiring_soon': expiring_soon[:10],
    }
    return render(request, 'inventory/dashboard.html', context)

@login_required
def stock_in_create(request):
    """ثبت رسید جدید (ورود کالا) - با مدیریت کامل خطاها"""
    
    # درخواست GET - نمایش فرم
    if request.method == 'GET':
        warehouses = Warehouse.objects.all()
        products = Product.objects.all()
        uoms = UnitOfMeasure.objects.all()
        context = {
            'warehouses': warehouses,
            'products': products,
            'uoms': uoms,
        }
        return render(request, 'inventory/stock_in_form.html', context)
    
    # ========== درخواست POST - ثبت رسید ==========
    
    # 1. دریافت داده‌های اصلی
    reference_number = request.POST.get('reference_number', '').strip()
    warehouse_id = request.POST.get('warehouse', '').strip()
    voucher_type = request.POST.get('voucher_type', '').strip()
    
    # 2. اعتبارسنجی داده‌های اصلی
    errors = []
    
    if not reference_number:
        errors.append('شماره رسید الزامی است.')
    elif StockIn.objects.filter(reference_number=reference_number).exists():
        errors.append(f'شماره رسید "{reference_number}" قبلاً ثبت شده است.')
    
    if not warehouse_id:
        errors.append('انتخاب انبار الزامی است.')
    else:
        try:
            warehouse = Warehouse.objects.get(id=warehouse_id)
        except Warehouse.DoesNotExist:
            errors.append('انبار انتخاب شده معتبر نیست.')
    
    if not voucher_type:
        errors.append('نوع ورود الزامی است.')
    
    # 3. دریافت جزئیات کالاها
    product_ids = request.POST.getlist('product_id')
    quantities = request.POST.getlist('quantity')
    unit_prices = request.POST.getlist('unit_price')
    uom_ids = request.POST.getlist('uom_id')
    batch_numbers = request.POST.getlist('batch_number')
    production_dates = request.POST.getlist('production_date')
    expiry_dates = request.POST.getlist('expiry_date')
    
    # 4. اعتبارسنجی جزئیات کالاها
    items_data = []
    for i in range(len(product_ids)):
        product_id = product_ids[i] if i < len(product_ids) else ''
        quantity = quantities[i] if i < len(quantities) else ''
        unit_price = unit_prices[i] if i < len(unit_prices) else ''
        
        # فقط ردیف‌هایی که پر شده‌اند پردازش شوند
        if product_id or quantity or unit_price:
            # بررسی کامل بودن ردیف
            if not product_id:
                errors.append(f'ردیف {i+1}: انتخاب محصول الزامی است.')
            elif not quantity:
                errors.append(f'ردیف {i+1}: وارد کردن تعداد الزامی است.')
            elif not unit_price:
                errors.append(f'ردیف {i+1}: وارد کردن قیمت الزامی است.')
            else:
                try:
                    items_data.append({
                        'product_id': int(product_id),
                        'quantity': float(quantity),
                        'unit_price': float(unit_price),
                        'uom_id': int(uom_ids[i]) if i < len(uom_ids) and uom_ids[i] else None,
                        'batch_number': batch_numbers[i] if i < len(batch_numbers) else '',
                        'production_date': production_dates[i] if i < len(production_dates) and production_dates[i] else None,
                        'expiry_date': expiry_dates[i] if i < len(expiry_dates) and expiry_dates[i] else None,
                    })
                except ValueError:
                    errors.append(f'ردیف {i+1}: تعداد و قیمت باید عدد باشند.')
    
    # 5. بررسی وجود حداقل یک قلم کالا
    if len(items_data) == 0:
        errors.append('حداقل یک قلم کالا باید وارد شود.')
    
    # 6. اگر خطایی وجود دارد، نمایش خطاها
    if errors:
        for error in errors:
            messages.error(request, error)
        
        # برگرداندن فرم با داده‌های قبلی
        # درخواست GET - نمایش فرم
        warehouses = Warehouse.objects.all()
        products = Product.objects.all()
        uoms = UnitOfMeasure.objects.all()
        context = {
            'warehouses': warehouses,
            'products': products,
            'uoms': uoms,
        }

        # پاک کردن پیام‌های قبلی قبل از نمایش فرم
        storage = messages.get_messages(request)
        storage.used = True
        return render(request, 'inventory/stock_in_form.html', context)


    # 7. فیلدهای اضافی بر اساس نوع ورود
    supplier = ''
    if voucher_type == 'purchase':
        supplier = request.POST.get('supplier', '').strip()
    elif voucher_type == 'production':
        supplier = request.POST.get('manufacturer', '').strip()
    elif voucher_type == 'transfer_in':
        source_warehouse = request.POST.get('source_warehouse', '').strip()
        supplier = f"انتقال از انبار {source_warehouse}" if source_warehouse else ''
    elif voucher_type == 'return_from_customer':
        supplier = request.POST.get('customer_name', '').strip()
    elif voucher_type == 'inventory_addition':
        supplier = f"اضافات - تأیید: {request.POST.get('approved_by', '')}"
    
    # 8. ثبت رسید
    try:
        with transaction.atomic():
            stock_in = StockIn.objects.create(
                reference_number=reference_number,
                warehouse_id=warehouse_id,
                voucher_type=voucher_type,
                supplier=supplier,
                notes=request.POST.get('notes', '')
            )
            
            for item in items_data:
                StockInItem.objects.create(
                    stock_in=stock_in,
                    product_id=item['product_id'],
                    uom_id=item['uom_id'],
                    batch_number=item['batch_number'],
                    production_date=item['production_date'],
                    expiry_date=item['expiry_date'],
                    quantity=item['quantity'],
                    unit_price=item['unit_price']
                )
        
        messages.success(request, f'✅ رسید {reference_number} با موفقیت ثبت شد.')
        return redirect('inventory:stock_in_list')
    
    except Exception as e:
        messages.error(request, f'خطا در ثبت رسید: {str(e)}')
        
        warehouses = Warehouse.objects.all()
        products = Product.objects.all()
        uoms = UnitOfMeasure.objects.all()
        context = {
            'warehouses': warehouses,
            'products': products,
            'uoms': uoms,
            'form_data': request.POST,
        }
        return render(request, 'inventory/stock_in_form.html', context)
    

@login_required
def stock_out_create(request):
    if request.method == 'POST':
        reference_number = request.POST.get('reference_number')
        warehouse_id = request.POST.get('warehouse')
        voucher_type = request.POST.get('voucher_type')
        customer = request.POST.get('customer')
        
        with transaction.atomic():
            stock_out = StockOut.objects.create(
                reference_number=reference_number,
                warehouse_id=warehouse_id,
                voucher_type=voucher_type,
                customer=customer
            )
            
            product_ids = request.POST.getlist('product_id')
            uom_ids = request.POST.getlist('uom_id')
            quantities = request.POST.getlist('quantity')
            
            for i in range(len(product_ids)):
                product_id = product_ids[i]
                quantity = float(quantities[i])
                
                warehouse = get_object_or_404(Warehouse, id=warehouse_id)
                product = get_object_or_404(Product, id=product_id)
                
                fefo_items = get_fefo_items(product, warehouse, quantity)
                
                stock_out_item = StockOutItem.objects.create(
                    stock_out=stock_out,
                    product=product,
                    uom_id=uom_ids[i],
                    quantity=quantity,
                )
                
                total_discount = 0
                for item in fefo_items:
                    discount = calculate_discount(item['stock_item'])
                    total_discount += discount
                
                if total_discount > 0 and len(fefo_items) > 0:
                    stock_out_item.discount_percent = total_discount / len(fefo_items)
                    stock_out_item.discount_reason = 'تخفیف خودکار - نزدیک به انقضا'
                    stock_out_item.save()
                
                for item in fefo_items:
                    StockOutItemDetail.objects.create(
                        stock_out_item=stock_out_item,
                        stock_item=item['stock_item'],
                        quantity=item['quantity']
                    )
        
        messages.success(request, f'فاکتور {reference_number} با موفقیت ثبت شد.')
        return redirect('inventory:stock_out_list')
    
    warehouses = Warehouse.objects.all()
    products = Product.objects.all()
    uoms = UnitOfMeasure.objects.all()
    return render(request, 'inventory/stock_out_form.html', {
        'warehouses': warehouses,
        'products': products,
        'uoms': uoms,
    })


@login_required
def stock_list(request):
    """لیست موجودی انبار با قابلیت جستجو و فیلتر"""
    from django.db.models import Q
    from datetime import date
    
    stock_items = StockItem.objects.filter(quantity__gt=0).select_related('product', 'warehouse', 'zone', 'uom')
    
    # جستجو
    search = request.GET.get('search', '')
    if search:
        stock_items = stock_items.filter(
            Q(product__name__icontains=search) |
            Q(product__code__icontains=search) |
            Q(batch_number__icontains=search)
        )
    
    # فیلتر بر اساس انبار
    warehouse_id = request.GET.get('warehouse', '')
    if warehouse_id:
        stock_items = stock_items.filter(warehouse_id=warehouse_id)
    
    # فیلتر بر اساس دسته‌بندی
    category = request.GET.get('category', '')
    if category:
        stock_items = stock_items.filter(product__category=category)
    
    # ========== محاسبه days_left برای هر آیتم ==========
    for item in stock_items:
        item.days_left = (item.expiry_date - date.today()).days if item.expiry_date else 0
    
    # ========== فیلتر بر اساس وضعیت انقضا ==========
    expiry_filter = request.GET.get('expiry', '')
    
    if expiry_filter == 'expiring':
        stock_items = [item for item in stock_items if 0 < item.days_left <= 7]
    elif expiry_filter == 'expired':
        stock_items = [item for item in stock_items if item.days_left < 0]
    
    # ========== آمار ==========
    total_value = sum(item.quantity * item.unit_price for item in stock_items)
    expiring_count = sum(1 for item in stock_items if 0 < item.days_left <= 7)
    expired_count = sum(1 for item in stock_items if item.days_left < 0)
    
    # ========== آماده‌سازی context ==========
    warehouses = Warehouse.objects.all()
    
    context = {
        'stock_items': stock_items,
        'warehouses': warehouses,
        'total_value': total_value,
        'expiring_count': expiring_count,
        'expired_count': expired_count,
        'search': search,
        'selected_warehouse': warehouse_id,
        'selected_expiry': expiry_filter,
        'selected_category': category,
    }
    return render(request, 'inventory/stock_list.html', context)

@login_required
def stock_in_list(request):
    stock_ins = StockIn.objects.all().order_by('-date')
    return render(request, 'inventory/stock_in_list.html', {'stock_ins': stock_ins})


@login_required
def stock_out_list(request):
    stock_outs = StockOut.objects.all().order_by('-date')
    return render(request, 'inventory/stock_out_list.html', {'stock_outs': stock_outs})

from django.http import JsonResponse
from .models import Warehouse, StorageZone

def get_warehouses_by_type(request):
    """API: دریافت انبارها بر اساس نوع"""
    warehouse_type = request.GET.get('type')
    if warehouse_type:
        warehouses = Warehouse.objects.filter(warehouse_type=warehouse_type).values('id', 'name')
    else:
        warehouses = Warehouse.objects.all().values('id', 'name')
    return JsonResponse({'warehouses': list(warehouses), 'success': True})


def get_zones_by_warehouse(request, warehouse_id):
    """API: دریافت سوله‌های یک انبار خاص"""
    try:
        zones = StorageZone.objects.filter(warehouse_id=warehouse_id).values('id', 'name', 'code')
        return JsonResponse({'zones': list(zones), 'success': True})
    except Exception as e:
        return JsonResponse({'zones': [], 'success': False, 'error': str(e)})


def get_zones_by_warehouse(request, warehouse_id):
    """API: دریافت سوله‌های یک انبار خاص"""
    try:
        zones = StorageZone.objects.filter(warehouse_id=warehouse_id).values('id', 'name', 'code')
        return JsonResponse({'zones': list(zones), 'success': True})
    except Exception as e:
        return JsonResponse({'zones': [], 'success': False, 'error': str(e)})


@login_required
def reports_dashboard(request):
    """داشبورد گزارشات و آنالیز"""
    from django.db.models import Sum, Count
    from datetime import date, timedelta
    from .models import StockIn, StockOut, StockItem, Product, Warehouse
    from accounting.models import InventoryValuation
    
    today = date.today()
    last_month = today - timedelta(days=30)
    
    # آمار کلی
    total_products = Product.objects.count()
    total_warehouses = Warehouse.objects.count()
    
    stock_items = StockItem.objects.filter(quantity__gt=0).select_related('product', 'warehouse', 'zone', 'uom')
    total_inventory_value = sum(float(item.quantity) * float(item.unit_price) for item in stock_items)
    
    # میانگین ارزش هر قلم
    if stock_items:
        avg_value_per_item = total_inventory_value / stock_items.count()
    else:
        avg_value_per_item = 0
    
    # محصولات نزدیک به انقضا
    expiring_soon = []
    for item in stock_items:
        days_left = (item.expiry_date - today).days
        if 0 < days_left <= 7:
            expiring_soon.append({
                'product': item.product,
                'warehouse': item.warehouse,
                'zone': item.zone,
                'batch_number': item.batch_number,
                'quantity': item.quantity,
                'uom': item.uom,
                'expiry_date': item.expiry_date,
                'days_left': days_left,
            })
    
    # ورود و خروج ماه اخیر
    stock_in_last_month = StockIn.objects.filter(date__gte=last_month).count()
    stock_out_last_month = StockOut.objects.filter(date__gte=last_month).count()
    
    # ارزش‌گذاری روزانه (برای نمودار)
    valuations = InventoryValuation.objects.order_by('-valuation_date')[:30]
    valuation_labels = [v.valuation_date.strftime('%Y-%m-%d') for v in reversed(valuations)]
    valuation_values = [float(v.total_value / 1000000) for v in reversed(valuations)]
    
    # آمار دسته‌بندی محصولات
    category_stats = Product.objects.values('category').annotate(
        count=Count('id'),
        total_value=Sum('stockitem__quantity', default=0)
    )
    category_map = dict(Product.CATEGORY_CHOICES)
    category_labels = [category_map.get(c['category'], c['category']) for c in category_stats]
    category_counts = [c['count'] for c in category_stats]
    category_values = [float(c['total_value'] or 0) for c in category_stats]
    
    # آمار انبارها
    warehouse_stats = Warehouse.objects.annotate(
        total_stock=Sum('stockitem__quantity', default=0)
    )
    warehouse_names = [w.name for w in warehouse_stats]
    warehouse_stock = [float(w.total_stock or 0) for w in warehouse_stats]
    
    context = {
        'total_products': total_products,
        'total_warehouses': total_warehouses,
        'total_inventory_value': total_inventory_value,
        'avg_value_per_item': avg_value_per_item,
        'expiring_soon': expiring_soon[:10],
        'expiring_count': len(expiring_soon),
        'stock_in_last_month': stock_in_last_month,
        'stock_out_last_month': stock_out_last_month,
        'valuation_labels': valuation_labels,
        'valuation_values': valuation_values,
        'category_labels': category_labels,
        'category_counts': category_counts,
        'category_values': category_values,
        'warehouse_names': warehouse_names,
        'warehouse_stock': warehouse_stock,
    }
    return render(request, 'inventory/reports.html', context)

def export_stock_excel(request):
    """خروجی Excel از لیست موجودی"""
    import csv
    from django.http import HttpResponse
    from datetime import date
    
    stock_items = StockItem.objects.filter(quantity__gt=0).select_related('product', 'warehouse', 'zone', 'uom')
    
    # فیلترها
    search = request.GET.get('search', '')
    if search:
        stock_items = stock_items.filter(product__name__icontains=search)
    
    warehouse_id = request.GET.get('warehouse', '')
    if warehouse_id:
        stock_items = stock_items.filter(warehouse_id=warehouse_id)
    
    # ایجاد پاسخ CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="stock_list.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ردیف', 'نام محصول', 'کد محصول', 'دسته بندی', 'انبار', 'سوله', 
                     'شماره دسته', 'موجودی', 'واحد', 'تاریخ تولید', 'تاریخ انقضا', 
                     'روز باقی‌مانده', 'قیمت تمام شده', 'ارزش کل'])
    
    for idx, item in enumerate(stock_items, 1):
        days_left = (item.expiry_date - date.today()).days if item.expiry_date else 0
        total_value = float(item.quantity) * float(item.unit_price)
        
        writer.writerow([
            idx, item.product.name, item.product.code, item.product.get_category_display(),
            item.warehouse.name, item.zone.name if item.zone else '-', item.batch_number,
            float(item.quantity), item.uom.code, item.production_date, item.expiry_date,
            days_left, float(item.unit_price), float(total_value)
        ])
    
    return response