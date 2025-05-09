from .models import Product

def product_categories(request):
    return {
        'product_categories': Product.PRODUCT_CATEGORIES
    }