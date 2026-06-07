/* ========================================
   سیستم انبارداری لبنیات - کدهای جاوااسکریپت
   ======================================== */

// منتظر می‌مونیم تا DOM کامل بارگذاری بشه
document.addEventListener('DOMContentLoaded', function() {
    
    // ---------- 1. هایلایت منوی فعال در سایدبار ----------
    highlightActiveMenu();
    
    // ---------- 2. فرم ورود کالا (افزودن/حذف ردیف) ----------
    initDynamicForm();
    
    // ---------- 3. فرم خروج کالا ----------
    initDynamicForm();
    
    // ---------- 4. فعال کردن خودکار tooltip های Bootstrap (اگه استفاده بشه) ----------
    initBootstrapTooltips();
    
    // ---------- 5. بستن خودکار alert ها بعد از 5 ثانیه ----------
    autoCloseAlerts();
});


/**
 * هایلایت کردن گزینه فعال در منوی سایدبار
 */
function highlightActiveMenu() {
    const currentUrl = window.location.pathname;
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    
    // لیست آدرس‌های نسبی
    const urlMappings = getUrlMappings();
    
    navLinks.forEach(link => {
        const linkUrl = link.getAttribute('href');
        
        // مقایسه دقیق
        if (currentUrl === linkUrl) {
            link.classList.add('active');
        }
        // برای صفحه اصلی (داشبورد)
        else if (currentUrl === '/' && linkUrl === urlMappings['/']) {
            link.classList.add('active');
        }
        // برای صفحات دیگه با تطابق کامل
        else if (linkUrl !== '/' && currentUrl === linkUrl) {
            link.classList.add('active');
        }
    });
}


/**
 * دریافت نگاشت آدرس‌ها (این مقادیر از Django به JS منتقل می‌شن)
 * در صورت نیاز می‌تونی این تابع رو توسعه بدی
 */
function getUrlMappings() {
    return {
        '/': '/',
        '/reports/': '/reports/',
        '/stock-in/': '/stock-in/',
        '/stock-out/': '/stock-out/',
        '/stock-list/': '/stock-list/',
        '/stock-in/list/': '/stock-in/list/',
        '/stock-out/list/': '/stock-out/list/',
    };
}


/**
 * مدیریت فرم‌های پویا (افزودن و حذف ردیف)
 */
function initDynamicForm() {
    const addButton = document.getElementById('add-row');
    if (!addButton) return;
    
    // افزودن ردیف جدید
    addButton.addEventListener('click', function() {
        const container = document.getElementById('items-container');
        if (!container) return;
        
        const firstRow = container.querySelector('.item-row');
        if (!firstRow) return;
        
        const newRow = firstRow.cloneNode(true);
        
        // پاک کردن مقادیر ورودی‌های ردیف جدید
        newRow.querySelectorAll('input, select').forEach(input => {
            input.value = '';
            // حذف کلاس‌های خطا (اگه باشه)
            input.classList.remove('is-invalid');
        });
        
        container.appendChild(newRow);
    });
    
    // حذف ردیف
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-row')) {
            const rows = document.querySelectorAll('.item-row');
            if (rows.length > 1) {
                e.target.closest('.item-row').remove();
            } else {
                alert('حداقل یک قلم باید وجود داشته باشد');
            }
        }
    });
}


/**
 * فعال کردن Bootstrap Tooltips (اگه ازش استفاده بشه)
 */
function initBootstrapTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}


/**
 * بستن خودکار پیغام‌های alert بعد از 5 ثانیه
 */
function autoCloseAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}


/**
 * اعتبارسنجی فرم ورود کالا (اختیاری)
 */
function validateStockInForm() {
    let isValid = true;
    const requiredFields = document.querySelectorAll('#items-container input[required], #items-container select[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}


/**
 * اعتبارسنجی فرم خروج کالا با بررسی موجودی
 * (این تابع باید با AJAX به سرور متصل بشه برای چک کردن موجودی)
 */
async function validateStockOutForm(productId, warehouseId, quantity) {
    try {
        const response = await fetch(`/api/check-stock/?product=${productId}&warehouse=${warehouseId}&quantity=${quantity}`);
        const data = await response.json();
        return data.available;
    } catch (error) {
        console.error('خطا در بررسی موجودی:', error);
        return false;
    }
}


/**
 * نمایش/مخفی کردن بارگذاری (Loading spinner)
 */
function showLoading(show) {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.style.display = show ? 'block' : 'none';
    }
}


/**
 * فرمت کردن اعداد با کاما (برای نمایش بهتر قیمت‌ها)
 */
function formatNumber(number) {
    return new Intl.NumberFormat('fa-IR').format(number);
}


/**
 * محاسبه خودکار قیمت کل در فرم‌ها (اگه فیلد قیمت واحد و تعداد داشته باشیم)
 */
function initAutoTotalCalculation() {
    const quantityInputs = document.querySelectorAll('.quantity-input');
    const priceInputs = document.querySelectorAll('.price-input');
    const totalDisplay = document.getElementById('total-amount');
    
    if (!totalDisplay) return;
    
    function calculateTotal() {
        let total = 0;
        for (let i = 0; i < quantityInputs.length; i++) {
            const qty = parseFloat(quantityInputs[i].value) || 0;
            const price = parseFloat(priceInputs[i].value) || 0;
            total += qty * price;
        }
        totalDisplay.textContent = formatNumber(total);
    }
    
    quantityInputs.forEach(input => input.addEventListener('input', calculateTotal));
    priceInputs.forEach(input => input.addEventListener('input', calculateTotal));
}