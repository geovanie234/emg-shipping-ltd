from django.db import models
import uuid


class Product(models.Model):
    CATEGORY_GENERAL = 'general'
    CATEGORY_ELECTRONICS = 'electronics'
    CATEGORY_FASHION = 'fashion'
    CATEGORY_HOME = 'home'
    CATEGORY_BEAUTY = 'beauty'
    CATEGORY_OFFICE = 'office'
    CATEGORY_GROCERIES = 'groceries'
    CATEGORY_HEALTH = 'health'
    CATEGORY_SPORTS = 'sports'
    CATEGORY_ACCESSORIES = 'accessories'

    CATEGORY_CHOICES = [
        (CATEGORY_GENERAL, 'General'),
        (CATEGORY_ELECTRONICS, 'Electronics'),
        (CATEGORY_FASHION, 'Fashion'),
        (CATEGORY_HOME, 'Home & Living'),
        (CATEGORY_BEAUTY, 'Beauty & Care'),
        (CATEGORY_OFFICE, 'Office & School'),
        (CATEGORY_GROCERIES, 'Groceries'),
        (CATEGORY_HEALTH, 'Health & Wellness'),
        (CATEGORY_SPORTS, 'Sports & Outdoors'),
        (CATEGORY_ACCESSORIES, 'Accessories'),
    ]

    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=40, unique=True, blank=True, null=True, db_index=True)
    category = models.CharField(
        max_length=40,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_GENERAL,
        db_index=True,
    )
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    inventory_locked = models.BooleanField(default=False)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['category', 'name']

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"SKU-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.stock <= self.low_stock_threshold and self.stock > 0

    @property
    def inventory_status(self):
        if self.inventory_locked:
            return 'Locked'
        if self.stock == 0:
            return 'Out of Stock'
        if self.is_low_stock:
            return 'Low Stock'
        return 'In Stock'

    @property
    def inventory_status_color(self):
        if self.inventory_locked:
            return 'secondary'
        if self.stock == 0:
            return 'danger'
        if self.is_low_stock:
            return 'warning'
        return 'success'

    @property
    def has_visible_image(self):
        if not self.image or not self.image.name:
            return False

        try:
            return self.image.storage.exists(self.image.name)
        except (OSError, ValueError):
            return False

    @classmethod
    def infer_category(cls, name, description=''):
        haystack = f"{name} {description}".lower()
        keyword_map = (
            (cls.CATEGORY_ELECTRONICS, ('phone', 'laptop', 'headphone', 'speaker', 'watch', 'tablet', 'tv', 'camera', 'charger', 'computer')),
            (cls.CATEGORY_FASHION, ('shoe', 'shirt', 'dress', 'jean', 'jacket', 'fashion', 'clothing', 'bag', 'sandal')),
            (cls.CATEGORY_HOME, ('chair', 'table', 'bed', 'home', 'kitchen', 'pot', 'plate', 'lamp', 'sofa', 'curtain')),
            (cls.CATEGORY_BEAUTY, ('soap', 'lotion', 'cream', 'makeup', 'perfume', 'beauty', 'shampoo', 'conditioner')),
            (cls.CATEGORY_OFFICE, ('book', 'pen', 'printer', 'office', 'notebook', 'paper', 'school', 'desk')),
            (cls.CATEGORY_GROCERIES, ('rice', 'sugar', 'tea', 'coffee', 'milk', 'bread', 'grocer', 'food', 'drink')),
            (cls.CATEGORY_HEALTH, ('vitamin', 'health', 'mask', 'sanitizer', 'medicine', 'supplement', 'wellness')),
            (cls.CATEGORY_SPORTS, ('ball', 'fitness', 'sport', 'bike', 'helmet', 'gym', 'training')),
            (cls.CATEGORY_ACCESSORIES, ('case', 'cover', 'cable', 'accessory', 'wallet', 'belt')),
        )

        for category, keywords in keyword_map:
            if any(keyword in haystack for keyword in keywords):
                return category

        return cls.CATEGORY_GENERAL
