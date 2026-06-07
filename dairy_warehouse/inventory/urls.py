from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('stock-in/', views.stock_in_create, name='stock_in_create'),
    path('stock-in/list/', views.stock_in_list, name='stock_in_list'),
    path('stock-out/', views.stock_out_create, name='stock_out_create'),
    path('stock-out/list/', views.stock_out_list, name='stock_out_list'),
    path('stock-list/', views.stock_list, name='stock_list'),
    path('reports/', views.reports_dashboard, name='reports'),
    path('stock-list/export/', views.export_stock_excel, name='stock_list_export'),
    
    # APIها
    path('api/warehouses/by-type/', views.get_warehouses_by_type, name='api_warehouses_by_type'),
    path('api/zones/by-warehouse/<int:warehouse_id>/', views.get_zones_by_warehouse, name='api_zones_by_warehouse'),
]