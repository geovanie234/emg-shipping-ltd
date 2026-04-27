from django.urls import path
from . import views

urlpatterns = [
    # Product listing URLs
    path('', views.product_list, name='product_list'),
    path('products/', views.product_list, name='products_list'),
    
    # Product detail - This is the key URL for product details
    path('product/<int:id>/', views.product_detail, name='product_detail'),
    
    # Page URLs
    path('about/', views.about_page, name='about'),
    path('contact/', views.contact_page, name='contact'),
]