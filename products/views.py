from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, F, Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Product


def _with_visible_images(products):
    return [product for product in products if product.has_visible_image]


def product_list(request):
    """Display all products with search functionality"""
    catalog = Product.objects.filter(is_active=True).only(
        'id',
        'name',
        'sku',
        'category',
        'description',
        'price',
        'stock',
        'inventory_locked',
        'low_stock_threshold',
        'image',
        'created_at',
    )
    products = catalog
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'featured').strip()
    
    # Search functionality
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(sku__icontains=query)
        )
    
    if category and category in dict(Product.CATEGORY_CHOICES):
        products = products.filter(category=category)

    if sort == 'price_low':
        products = products.order_by('price', 'name')
    elif sort == 'price_high':
        products = products.order_by('-price', 'name')
    elif sort == 'latest':
        products = products.order_by('-created_at', 'name')
    else:
        products = products.order_by('-stock', 'price', '-created_at', 'name')

    category_totals = {
        item['category']: item['total']
        for item in catalog.values('category').annotate(total=Count('id'))
    }
    category_filters = [
        {
            'value': value,
            'label': label,
            'count': category_totals.get(value, 0),
        }
        for value, label in Product.CATEGORY_CHOICES
        if category_totals.get(value, 0)
    ]

    best_products = _with_visible_images(
        catalog.filter(stock__gt=0).order_by('-stock', 'price', '-created_at', 'name')
    )[:4]
    best_ids = {product.id for product in best_products}
    good_products = _with_visible_images(
        catalog.filter(stock__gt=0)
        .exclude(id__in=best_ids)
        .order_by('price', '-stock', '-created_at', 'name')
    )
    good_products = good_products[:4]

    search_suggestions = list(
        catalog.order_by('-stock', 'name').values_list('name', flat=True)[:8]
    )
    catalog_metrics = catalog.aggregate(
        catalog_total=Count('id'),
        in_stock_total=Count('id', filter=Q(stock__gt=0)),
        low_stock_total=Count('id', filter=Q(stock__gt=0, stock__lte=F('low_stock_threshold'))),
    )
    
    context = {
        'products': products,
        'query': query,
        'category': category if category else None,
        'selected_category_label': dict(Product.CATEGORY_CHOICES).get(category),
        'sort': sort,
        'total_products': products.count(),
        'catalog_total': catalog_metrics['catalog_total'],
        'in_stock_total': catalog_metrics['in_stock_total'],
        'low_stock_total': catalog_metrics['low_stock_total'],
        'category_filters': category_filters,
        'search_suggestions': search_suggestions,
        'best_products': best_products,
        'good_products': good_products,
    }
    return render(request, 'product_list.html', context)


def product_detail(request, id):
    """Display detailed information about a specific product"""
    # Get the product or return 404 if not found
    product = get_object_or_404(
        Product.objects.only(
            'id',
            'name',
            'sku',
            'category',
            'description',
            'price',
            'stock',
            'inventory_locked',
            'low_stock_threshold',
            'image',
            'created_at',
        ),
        id=id,
        is_active=True,
    )
    
    # Get related products (exclude current product)
    related_products = Product.objects.filter(is_active=True).exclude(id=id).only(
        'id',
        'name',
        'sku',
        'category',
        'description',
        'price',
        'stock',
        'inventory_locked',
        'low_stock_threshold',
        'image',
        'created_at',
    )
    
    if product.category:
        category_related = related_products.filter(category=product.category)
        if category_related.exists():
            related_products = category_related

    # Limit to 4 related products
    related_products = _with_visible_images(
        related_products.order_by('-stock', 'price', '-created_at', 'name')
    )[:4]
    
    # Stock status
    stock_status = 'In Stock' if product.stock > 0 else 'Out of Stock'
    stock_class = 'success' if product.stock > 0 else 'danger'
    
    # Get next URL for login redirect
    next_url = request.GET.get('next', '')
    
    context = {
        'product': product,
        'related_products': related_products,
        'stock_status': stock_status,
        'stock_class': stock_class,
        # Add delivery info to context
        'delivery_fee': 2000,
        'delivery_time': 'Within 24 hours',
        'districts': ['Gasabo', 'Kicukiro', 'Nyarugenge'],
        'payment_methods': ['Cash on Delivery', 'MTN Mobile Money', 'Airtel Money'],
        'category_label': product.get_category_display(),
        'next': next_url
    }
    return render(request, 'product_detail.html', context)


def about_page(request):
    """About Us page"""
    context = {
        'title': 'About EMG Shipping Rwanda',
        'company_name': 'EMG Shipping Rwanda',
        'year': '2024',
        'mission': 'To provide fast, reliable, and affordable delivery services across Kigali districts.',
        'vision': 'To become the leading e-commerce delivery service in Rwanda.',
        'values': [
            {'icon': 'bi-clock-history', 'title': 'Fast Delivery', 'desc': 'Within 24 hours'},
            {'icon': 'bi-shield-check', 'title': 'Reliable Service', 'desc': '100% guaranteed'},
            {'icon': 'bi-currency-dollar', 'title': 'Affordable', 'desc': 'Competitive prices'},
        ]
    }
    return render(request, 'about.html', context)


def contact_page(request):
    """Contact Us page"""
    # Handle contact form submission
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Here you would typically send an email or save to database
        # For now, just show a success message
        messages.success(request, f"Thank you {name}! We'll get back to you soon.")
        return redirect('contact')
        
        # Optional: You can add email sending logic here
        # from django.core.mail import send_mail
        # send_mail(
        #     f"Contact Form: {subject}",
        #     f"From: {name}\nEmail: {email}\nPhone: {phone}\n\nMessage:\n{message}",
        #     email,
        #     ['info@emgshipping.rw'],
        #     fail_silently=True,
        # )
    
    context = {
        'title': 'Contact EMG Shipping Rwanda',
        'company_name': 'EMG Shipping Rwanda',
        'address': 'Kigali, Rwanda',
        'phone': '0789 670 931',
        'email': 'info@emgshipping.rw',
        'hours': 'Monday - Saturday: 8:00 AM - 8:00 PM',
        'sunday_hours': 'Sunday: 9:00 AM - 5:00 PM'
    }
    return render(request, 'contact.html', context)
