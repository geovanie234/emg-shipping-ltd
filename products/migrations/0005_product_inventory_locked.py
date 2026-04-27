from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_product_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='inventory_locked',
            field=models.BooleanField(default=False),
        ),
    ]
