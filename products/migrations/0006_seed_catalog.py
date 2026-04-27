from django.db import migrations


CATALOG_PRODUCTS = [
    {
        'sku': 'SKU-554EA046',
        'name': 'phones',
        'category': 'electronics',
        'description': 'we bring you phones of your choice',
        'price': '90000.00',
        'stock': 93,
        'inventory_locked': False,
        'low_stock_threshold': 5,
        'is_active': True,
        'image': 'products/pexels-zeleboba-28902920.jpg',
    },
    {
        'sku': 'SKU-A90513D0',
        'name': 'nokia',
        'category': 'electronics',
        'description': 'available at low prices',
        'price': '15000.00',
        'stock': 65,
        'inventory_locked': False,
        'low_stock_threshold': 5,
        'is_active': True,
        'image': 'products/pexels-masoodaslami-19335258.jpg',
    },
    {
        'sku': 'SKU-E9BE84BB',
        'name': 'computer',
        'category': 'electronics',
        'description': 'available in many categories',
        'price': '400000.00',
        'stock': 25,
        'inventory_locked': False,
        'low_stock_threshold': 5,
        'is_active': True,
        'image': 'products/pexels-mikhail-nilov-9300738.jpg',
    },
    {
        'sku': 'SKU-8A273228',
        'name': 'shoes',
        'category': 'sports',
        'description': 'shoes that you were missing',
        'price': '25000.00',
        'stock': 30,
        'inventory_locked': False,
        'low_stock_threshold': 5,
        'is_active': True,
        'image': 'products/ii.jpg',
    },
    {
        'sku': 'SKU-F6E498CC',
        'name': 'shoes',
        'category': 'fashion',
        'description': 'that one fashion shoes which is on fire,  is here!',
        'price': '30000.00',
        'stock': 23,
        'inventory_locked': False,
        'low_stock_threshold': 5,
        'is_active': True,
        'image': 'products/dg.jpg',
    },
    {
        'sku': 'SKU-29F2A6F5',
        'name': 'headsets',
        'category': 'electronics',
        'description': 'part yourself from noise and disturbance with quality headsets',
        'price': '15000.00',
        'stock': 40,
        'inventory_locked': False,
        'low_stock_threshold': 5,
        'is_active': True,
        'image': 'products/pexels-anchukk-30428606.jpg',
    },
    {
        'sku': 'SKU-ED7AE780',
        'name': 'radio',
        'category': 'electronics',
        'description': 'anywhere you at find one for you.',
        'price': '20000.00',
        'stock': 20,
        'inventory_locked': False,
        'low_stock_threshold': 5,
        'is_active': True,
        'image': 'products/pexels-tkirkgoz-19924600.jpg',
    },
]


def seed_catalog(apps, schema_editor):
    Product = apps.get_model('products', 'Product')

    for product in CATALOG_PRODUCTS:
        defaults = product.copy()
        sku = defaults.pop('sku')
        Product.objects.update_or_create(sku=sku, defaults=defaults)


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_product_inventory_locked'),
    ]

    operations = [
        migrations.RunPython(seed_catalog, migrations.RunPython.noop),
    ]
