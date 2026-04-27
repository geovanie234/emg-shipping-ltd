from django.urls import path

from . import views


urlpatterns = [
    path('checkout/', views.create_order, name='checkout'),
    path('invoice/<int:order_id>/', views.invoice, name='invoice'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('track/<int:order_id>/', views.order_tracking, name='order_tracking'),
    path('tracking/', views.public_tracking_search, name='public_tracking_search'),
    path('tracking/<str:tracking_number>/', views.public_tracking, name='public_tracking'),
    path('cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('reorder/<int:order_id>/', views.reorder, name='reorder'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/inventory/', views.inventory_management, name='inventory_management'),
    path('admin/orders/<int:order_id>/status/', views.admin_order_status_update, name='admin_order_status_update'),
    path('api/orders/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    path('api/stats/', views.get_order_stats, name='get_order_stats'),
    path('api/tracking/<int:order_id>/', views.get_tracking_data, name='get_tracking_data'),
]
