import os
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Product


class ProductPageImageTests(TestCase):
    def setUp(self):
        self.uploaded_images = []
        self.addCleanup(self.cleanup_uploaded_images)

    def cleanup_uploaded_images(self):
        for image_name in self.uploaded_images:
            Product._meta.get_field('image').storage.delete(image_name)

    def create_product(self, name, *, stock=10, price='10.00', image=None, category=Product.CATEGORY_GENERAL):
        product = Product.objects.create(
            name=name,
            description=f'{name} description',
            price=price,
            stock=stock,
            category=category,
            image=image,
            is_active=True,
        )
        if product.image:
            self.uploaded_images.append(product.image.name)
        return product

    def create_image(self, name):
        stem, extension = os.path.splitext(name)
        unique_name = f'{stem}-{uuid.uuid4().hex}{extension or ".jpg"}'
        return SimpleUploadedFile(unique_name, b'visible-image-content', content_type='image/jpeg')

    def test_has_visible_image_returns_false_when_file_is_missing(self):
        product = self.create_product('Visible Product', image=self.create_image('visible-product.jpg'))

        self.assertTrue(product.has_visible_image)

        product.image.storage.delete(product.image.name)

        self.assertFalse(product.has_visible_image)

    def test_product_list_hides_good_value_section_when_only_no_image_products_remain(self):
        for index, stock in enumerate((40, 35, 30, 25), start=1):
            self.create_product(
                f'Visible {index}',
                stock=stock,
                price='50.00',
                image=self.create_image(f'visible-{index}.jpg'),
            )

        for index, price in enumerate(('1.00', '2.00', '3.00', '4.00'), start=1):
            self.create_product(f'No Image {index}', stock=5, price=price)

        response = self.client.get(reverse('product_list'))

        self.assertEqual(len(response.context['best_products']), 4)
        self.assertEqual(response.context['good_products'], [])
        self.assertContains(response, 'Best Products')
        self.assertNotContains(response, 'Good Value Picks')

    def test_product_detail_related_products_only_include_visible_images(self):
        main_product = self.create_product(
            'Main Product',
            category=Product.CATEGORY_ELECTRONICS,
            image=self.create_image('main-product.jpg'),
        )
        visible_related = self.create_product(
            'Visible Related',
            category=Product.CATEGORY_ELECTRONICS,
            image=self.create_image('visible-related.jpg'),
        )
        self.create_product('Hidden Related', category=Product.CATEGORY_ELECTRONICS)

        response = self.client.get(reverse('product_detail', args=[main_product.id]))

        related_names = [product.name for product in response.context['related_products']]

        self.assertEqual(related_names, [visible_related.name])
        self.assertContains(response, visible_related.name)
        self.assertNotContains(response, 'Hidden Related')
