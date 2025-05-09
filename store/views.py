
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404, JsonResponse
from .models import Product, Cart, CartItem
from django.contrib.auth.decorators import login_required
from .models import *
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from .forms import *
import stripe
import uuid
import json
from django.db import transaction
from cryptography.fernet import Fernet
import logging
from django_countries import countries
logger = logging.getLogger(__name__)
from django.views.generic import ListView, DetailView
from django.utils import timezone
from .recommendations import RecommendationEngine

# Create a global instance of the recommendation engine
recommendation_engine = RecommendationEngine()

def home(request):
    # Get site configuration
    site_config = SiteConfiguration.objects.first()
    if not site_config:
        site_config = SiteConfiguration.objects.create(
            site_name="Betegna",
            hero_title="Discover Ethiopian Heritage",
            hero_description="Authentic handcrafted products and specialty coffee",
            hero_button_text="Shop Collections",
            hero_button_link="/products",
            secondary_button_text="Learn More",
            secondary_button_link="/about"
        )

    # Get featured collections
    featured_collections = Collection.objects.filter(is_featured=True, is_active=True)[:5]
    all_collections = Collection.objects.filter(is_active=True)

    # Initialize recommendation engine
    from .recommendations import RecommendationEngine
    engine = RecommendationEngine()

    # Get base featured products
    base_featured = Product.objects.filter(is_featured=True, is_active=True).prefetch_related('images')

    # Get personalized recommendations (limited to featured products)
    personalized_recs = engine.get_recommendations(request, limit=6)
    if personalized_recs:
        # Filter recommendations to only include featured products
        personalized_featured = [p for p in personalized_recs if p in base_featured]
        
        # Get remaining featured products not in recommendations
        remaining_featured = base_featured.exclude(id__in=[p.id for p in personalized_featured])
        
        # Combine: personalized first, then remaining featured
        featured_products = list(personalized_featured) + list(remaining_featured)[:6]
    else:
        # Fallback to original featured products if no recommendations
        featured_products = base_featured[:6]

    # Get active special offer and testimonials
    special_offer = SpecialOffer.objects.filter(is_active=True).first()
    featured_testimonials = Testimonial.objects.filter(is_featured=True)[:4]

    context = {
        'site_config': site_config,
        'featured_collections': featured_collections,
        'all_collections': all_collections,
        'featured_products': featured_products,
        'special_offer': special_offer,
        'featured_testimonials': featured_testimonials,
        'has_personalized': bool(personalized_recs),  # For template to show "Recommended for You"
    }

    return render(request, './store/home.html', context)

def search(request):
    query = request.GET.get('q', '').strip()

     # Get popular categories (top 5 most common categories with active products)
    popular_categories = Product.objects.filter(is_active=True)\
        .values('category')\
        .annotate(count=Count('category'))\
        .order_by('-count')[:5]
    
    # Convert to proper category names
    category_choices = dict(Product.PRODUCT_CATEGORIES)
    popular_categories_list = [
        (cat['category'], category_choices[cat['category']]) 
        for cat in popular_categories
    ]
    
    # Get trending products (recently added)
    trending_products = Product.objects.filter(
        is_active=True,
        created_at__gte=datetime.now() - timedelta(days=30)
    ).order_by('-created_at')[:5]
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX request for live search
        if len(query) >= 2:
            # Search in name, description, and category
            products = Product.objects.filter(
                Q(name__icontains=query) | 
                Q(description__icontains=query) |
                Q(category__icontains=query),
                is_active=True
            )[:8]  # Limit to 8 results for live search
            
            results = []
            for product in products:
                first_image = product.images.first()
                results.append({
                    'name': product.name,
                    'slug': product.slug,
                    'price': str(product.price),
                    'category_name': product.get_category_display(),
                    'image': first_image.image.url if first_image else '/static/images/default-product.jpg'
                })
            
            return JsonResponse({'results': results})
        return JsonResponse({'results': []})
    
    # Regular search page
    if len(query) >= 2:
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__icontains=query),
            is_active=True
        )
    else:
        products = Product.objects.none()
    
    return render(request, './store/search_results.html', {
        'products': products,
        'query': query,
        'popular_categories': popular_categories_list,
        'trending_products': trending_products
    })



from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Cart, Product
import random

@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Get recommended products based on items in cart
    recommended_products = []
    if cart.items.exists():
        # Get categories of products in cart
        categories = set(item.product.category for item in cart.items.all())
        
        # Get 4 random products from the same categories
        for category in categories:
            products = Product.objects.filter(
                category=category,
                is_active=True
            ).exclude(
                id__in=[item.product.id for item in cart.items.all()]
            )
            
            if products.exists():
                sampled_products = random.sample(list(products), min(4, len(products)))
                recommended_products.extend(sampled_products)
    
    # If no recommendations from same categories, get random products
    if not recommended_products:
        recommended_products = Product.objects.filter(
            is_active=True
        ).order_by('?')[:3]
    
    # Ensure we don't show more than 4 recommendations
    recommended_products = list(set(recommended_products))[:3]
    
    
    return render(request, './store/cart.html', {
        'cart': cart,
        'recommended_products': recommended_products, 'active_special_offers': SpecialOffer.objects.filter(
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now(),
            is_active=True
        ).order_by('-start_date')[:3], 
    })

@login_required
def add_to_cart(request, product_id, offer_id=None):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Handle special offer if provided
        special_offer = None
        if offer_id:
            special_offer = get_object_or_404(SpecialOffer, id=offer_id)
            if not special_offer.is_currently_active():
                messages.error(request, "This offer is no longer active.")
                return redirect('special_offer_detail', pk=offer_id)
            if not special_offer.products.filter(id=product.id).exists():
                messages.error(request, "This product is not part of the current offer.")
                return redirect('special_offer_detail', pk=offer_id)
        
        # Check if item already in cart
        defaults = {'quantity': 1}
        if special_offer:
            defaults['special_offer'] = special_offer
            
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            **({'special_offer': special_offer} if special_offer else {}),
            defaults=defaults
        )
        
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        
        # Create appropriate success message
        if special_offer:
            discounted_price = product.price * (100 - special_offer.discount_percentage) / 100
            savings = product.price - discounted_price
            message = (f"{product.name} added to your cart with {special_offer.discount_percentage}% discount! "
                      f"You saved ${savings:.2f}")
        else:
            message = f"{product.name} added to your cart!"
        
        messages.success(request, message)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': cart.items.count(),
                'message': message
            })
        
        return redirect('cart')
    
    return redirect('home')

@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        action = request.POST.get('action')
        
        if action == 'increase':
            cart_item.quantity += 1
        elif action == 'decrease' and cart_item.quantity > 1:
            cart_item.quantity -= 1
        elif action == 'remove':
            cart_item.delete()
            messages.success(request, "Item removed from cart")
            return redirect('cart')
        
        cart_item.save()
        messages.success(request, "Cart updated")
    
    return redirect('cart')

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from cart")
    return redirect('cart')



@login_required
def cart_count(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return JsonResponse({'cart_count': cart.items.count()})



class SpecialOffersListView(ListView):
    model = SpecialOffer
    template_name = './store/special_offers_list.html'
    context_object_name = 'offers'
    
    def get_queryset(self):
        now = timezone.now()
        return SpecialOffer.objects.filter(
            start_date__lte=now,
            end_date__gte=now,
            is_active=True
        ).order_by('-start_date')

class SpecialOfferDetailView(DetailView):
    model = SpecialOffer
    template_name = './store/special_offer_detail.html'
    context_object_name = 'offer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = self.object.get_products_with_discounts()
        return context



#products view

def all_products(request):
    products = Product.objects.filter(is_active=True)
    
    # Get personalized recommendations
    recommended_products = recommendation_engine.get_recommendations(request)
    
    if not recommended_products or len(recommended_products) < 12:
        # Fall back to random if no recommendations
        products = products.order_by('?')
    else:
        # Get full product objects in recommendation order
        recommended_ids = [p.id for p in recommended_products]
        products = products.filter(id__in=recommended_ids)
        
        # Create a mapping from id to product for efficient lookup
        product_map = {p.id: p for p in products}
        
        # Reorder products to match recommendation order
        products = [product_map[pid] for pid in recommended_ids if pid in product_map]
    

    sort_option = request.GET.get('sort', 'default')
    if sort_option == 'price-low-high':
        products = products.order_by('price')
    elif sort_option == 'price-high-low':
        products = products.order_by('-price')
    elif sort_option == 'newest':
        products = products.order_by('-created_at')

        
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Track category view for anonymous users
    if not request.user.is_authenticated:
        track_interaction(request, None, 'view_category', 'all_products')
    
    context = {
        'products': page_obj,
        'title': 'All Products'
    }
    return render(request, './store/products/all_products.html', context)




from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import Http404
from .models import Product

def products_by_category(request, category_slug):
    # Create a mapping of URL-friendly slugs to category codes
    category_mapping = {
        # Fashion & Accessories
        'clothing': 'CLOTHING',
        'traditional-clothing': 'CLOTHING',
        'fashion': 'FASHION',
        'modern-clothing': 'FASHION',
        'footwear': 'FOOTWEAR',
        'shoes': 'FOOTWEAR',
        'bags': 'BAGS',
        'bags-purses': 'BAGS',
        'purses': 'BAGS',
        'jewelry': 'JEWELRY',
        'accessories': 'ACCESSORIES',
        'fashion-accessories': 'ACCESSORIES',
        'watches': 'WATCHES',

        # Beauty & Personal Care
        'beauty': 'BEAUTY',
        'beauty-products': 'BEAUTY',
        'skincare': 'SKINCARE',
        'skin-care': 'SKINCARE',
        'haircare': 'HAIRCARE',
        'hair-care': 'HAIRCARE',
        'fragrance': 'FRAGRANCE',
        'perfume': 'FRAGRANCE',
        'personal-care': 'PERSONAL_CARE',

        # Electronics
        'phones': 'PHONES',
        'mobile-phones': 'PHONES',
        'laptops': 'LAPTOPS',
        'computers': 'COMPUTERS',
        'desktops': 'COMPUTERS',
        'pcs': 'COMPUTERS',
        'tvs': 'TVS',
        'televisions': 'TVS',
        'audio': 'AUDIO',
        'speakers': 'AUDIO',
        'headphones': 'AUDIO',
        'gaming': 'GAMING',
        'consoles': 'GAMING',
        'cameras': 'CAMERAS',
        'photography': 'CAMERAS',

        # Home & Kitchen
        'furniture': 'FURNITURE',
        'home-decor': 'HOME_DECOR',
        'decor': 'HOME_DECOR',
        'kitchen': 'KITCHEN',
        'kitchenware': 'KITCHEN',
        'bedding': 'BEDDING',
        'linens': 'BEDDING',
        'lighting': 'LIGHTING',
        'tools': 'TOOLS',
        'hardware': 'TOOLS',

        # Food & Beverage
        'coffee': 'COFFEE',
        'ethiopian-coffee': 'COFFEE',
        'tea': 'TEA',
        'spices': 'SPICES',
        'herbs': 'SPICES',
        'packaged-foods': 'PACKAGED_FOODS',
        'snacks': 'SNACKS',
        'beverages': 'SNACKS',
        'gourmet': 'GOURMET',

        # Art & Craft
        'handicraft': 'HANDICRAFT',
        'handmade': 'HANDICRAFT',
        'paintings': 'PAINTINGS',
        'sculptures': 'SCULPTURE',
        'art-supplies': 'ART_SUPPLIES',

        # Books & Stationery
        'books': 'BOOKS',
        'literature': 'BOOKS',
        'notebooks': 'NOTEBOOKS',
        'journals': 'NOTEBOOKS',
        'office-supplies': 'OFFICE_SUPPLIES',

        # Kids & Baby
        'toys': 'TOYS',
        'games': 'TOYS',
        'baby-clothing': 'BABY_CLOTHING',
        'baby-care': 'BABY_CARE',
        'kids-furniture': 'KIDS_FURNITURE',

        # Sports & Outdoors
        'sports': 'SPORTS',
        'sports-equipment': 'SPORTS',
        'fitness': 'FITNESS',
        'gym': 'FITNESS',
        'camping': 'CAMPING',
        'hiking': 'CAMPING',
        'bicycles': 'BICYCLES',
        'bikes': 'BICYCLES',

        # Health & Wellness
        'health': 'HEALTH',
        'health-products': 'HEALTH',
        'vitamins': 'VITAMINS',
        'supplements': 'VITAMINS',
        'wellness': 'WELLNESS',
        'therapy': 'WELLNESS',

        # Automotive
        'car-accessories': 'CAR_ACCESSORIES',
        'motorcycle-parts': 'MOTORCYCLE_PARTS',
        'car-care': 'CAR_CARE',

        # Tech Accessories
        'phone-accessories': 'PHONE_ACCESSORIES',
        'computer-accessories': 'COMPUTER_ACCESSORIES',
        'chargers': 'CHARGERS',
        'power-banks': 'CHARGERS',
        'smart-devices': 'SMART_DEVICES',

        # Others
        'musical-instruments': 'MUSICAL_INSTRUMENTS',
        'instruments': 'MUSICAL_INSTRUMENTS',
        'pets': 'PETS',
        'pet-supplies': 'PETS',
        'plants': 'PLANTS',
        'gardening': 'PLANTS',
        'event-supplies': 'EVENT_SUPPLIES',
        'party-supplies': 'EVENT_SUPPLIES',
        'gifts': 'GIFTS',
        'special-items': 'GIFTS',
        'religious-items': 'RELIGIOUS_ITEMS',
        'cultural-items': 'RELIGIOUS_ITEMS',
        'cleaning': 'CLEANING',
        'cleaning-products': 'CLEANING',
    }

    
    # Try to get the category code from the mapping, or use the slug as-is
    category_code = category_mapping.get(category_slug.lower(), category_slug.upper())
    
    # Get the display name for the category
    category_name = dict(Product.PRODUCT_CATEGORIES).get(category_code)
    
    if not category_name:
        raise Http404("Category does not exist")
    
    # Get products in this category
    products = Product.objects.filter(
        category=category_code,
        is_active=True
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj,
        'category': {
            'name': category_name,
            'slug': category_slug,
            'code': category_code
        },
        'title': f'{category_name} Products'
    }
    return render(request, './store/products/products_by_category.html', context)

def product_detail(request, slug):
    # Get the single product
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # Get related products (same category)
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:3]
    
    context = {
        'product': product,
        'related_products': related_products,
        'title': product.name
    }
    return render(request, './store/products/product_detail.html', context)

def all_collections(request):
    # Get all active collections
    collections = Collection.objects.filter(is_active=True)
    
    context = {
        'collections': collections,
        'title': 'All Collections'
    }
    return render(request, './store/products/all_collections.html', context)

def collection_detail(request, slug):
    # Get the collection and its products
    collection = get_object_or_404(Collection, slug=slug, is_active=True)
    products = collection.products.filter(is_active=True)
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'collection': collection,
        'products': page_obj,
        'title': collection.name
    }
    return render(request, './store/products/collection_detail.html', context)



from django.core.cache import cache

def get_popular_categories():
    cache_key = 'popular_categories'
    categories = cache.get(cache_key)
    if not categories:
        categories = Product.objects.filter(is_active=True)\
            .values('category')\
            .annotate(count=Count('category'))\
            .order_by('-count')[:5]
        cache.set(cache_key, categories, 60*60*24)  # Cache for 24 hours
    return categories


#orders
# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Initialize encryption
cipher_suite = Fernet(settings.PAYMENT_ENCRYPTION_KEY)

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    payment_methods = PaymentMethod.objects.filter(is_active=True)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = create_order(request, cart, form.cleaned_data)
                payment_method = form.cleaned_data['payment_method']
                
                if payment_method == 'CARD':
                    return process_stripe_payment(request, order)
                elif payment_method == 'PAYPAL':
                    return redirect('process_paypal', order_id=order.id)
                elif payment_method == 'BANK':
                    return redirect('process_bank', order_id=order.id)
                    
            except Exception as e:
                logger.error(f"Checkout error: {str(e)}", exc_info=True)
                messages.error(request, "An error occurred during checkout. Please try again.")
        else:
            # Form is invalid - show errors
            messages.error(request, "Please correct the errors below.")
    else:
        form = CheckoutForm()
    
    return render(request, './store/checkout.html', {
        'form': form,  # Pass the form instance (not a new one)
        'cart': cart,
        'payment_methods': payment_methods,
        'countries': countries,  # Add this line
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })

def create_order(request, cart, cleaned_data):
    # Generate order number first to use in transaction ID if needed
    order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
    
    with transaction.atomic():
        # Create order
        order = Order(
            user=request.user,
            order_number=order_number,
            total_price=cart.total_price,
            shipping_address=json.dumps({
                'name': cleaned_data['shipping_name'],
                'address': cleaned_data['shipping_address'],
                'city': cleaned_data['shipping_city'],
                'postal_code': cleaned_data['shipping_postal_code'],
                'country': cleaned_data['shipping_country'],
                'phone': cleaned_data['shipping_phone'],
            }),
            billing_address=json.dumps(cleaned_data.get('billing_address', {})) if 'billing_address' in cleaned_data else None,
            customer_note=cleaned_data.get('customer_note', ''),
        )
        order.save()
        
        # Create order items and reduce product stock
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
            
            # Update product stock
            cart_item.product.stock -= cart_item.quantity
            cart_item.product.save()
        
        # Clear the cart
        cart.items.all().delete()
    
    return order


def process_stripe_payment(request, order):
    try:
        # Create Stripe PaymentIntent
        intent = stripe.PaymentIntent.create(
            amount=int(order.total_price * 100),  # in cents
            currency='usd',
            metadata={
                'order_number': order.order_number,
                'user_id': request.user.id
            }
        )
        
        # Create pending payment record
        payment = Payment.objects.create(
            order=order,
            payment_type='CARD',
            amount=order.total_price,
            status='PENDING',
            transaction_id=intent.id
        )
        
        return render(request, './store/payments/stripe.html', {
            'client_secret': intent.client_secret,
            'order': order,
            'payment': payment,
        })
        
    except stripe.error.StripeError as e:
        # Handle Stripe errors
        return render(request, './store/payments/error.html', {
            'error': str(e),
            'order': order,
        })

def process_paypal_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Create payment record
    payment = Payment.objects.create(
        order=order,
        payment_type='PAYPAL',
        amount=order.total_price,
        status='PENDING',
        transaction_id=f"PAYPAL-{uuid.uuid4().hex[:8].upper()}"
    )
    
    # In production, you would:
    # 1. Create PayPal order
    # 2. Store PayPal order ID in payment_details
    # 3. Redirect to PayPal approval URL
    
    # For testing, we'll mock the PayPal flow
    return render(request, 'store/payments/paypal_redirect.html', {
        'order': order,
        'payment': payment,
        # In production, you would add:
        # 'paypal_order_id': 'PAYPAL-ORDER-ID',
        # 'approval_url': 'https://www.paypal.com/checkout/...'
    })

def process_bank_transfer(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Create payment record
    payment = Payment.objects.create(
        order=order,
        payment_type='BANK',
        amount=order.total_price,
        status='PENDING',
        transaction_id=f"BANK-{uuid.uuid4().hex[:8].upper()}"
    )
    
    # Send bank transfer instructions email
    # send_bank_transfer_instructions(request.user, order)
    
    return render(request, './store/payments/bank_transfer.html', {
        'order': order,
        'payment': payment,
    })


@login_required
def order_confirmation(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Verify payment was successful
    if not order.payments.filter(status='COMPLETED').exists():
        return redirect('order_failed', order_number=order_number)
    
    return render(request, './store/payments/order_confirmation.html', {
        'order': order,
    })
@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, './store/payments/order_history.html', {
        'orders': orders,
    })
@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, './store/payments/order_detail.html', {
        'order': order,
    })
def order_failed(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, './store/payments/order_failed.html', {
        'order': order,
    })

@login_required
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    if order.status == 'PENDING':
        order.status = 'CANCELLED'
        order.save()
        messages.success(request, f"Order #{order_number} has been cancelled.")
    else:
        messages.error(request, f"Order #{order_number} cannot be cancelled.")
    
    return redirect('order_detail', order_number=order.order_number)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return JsonResponse({'status': 'invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return JsonResponse({'status': 'invalid signature'}, status=400)
    
    # Add more event types
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_payment_success(payment_intent)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        handle_payment_failure(payment_intent)

    if event['type'] == 'charge.refunded':
        charge = event['data']['object']
        handle_refund(charge)
    
    return JsonResponse({'status': 'success'})

def handle_refund(charge):
    try:
        payment = Payment.objects.get(
            transaction_id=charge['payment_intent'],
            status='COMPLETED'
        )
        payment.status = 'REFUNDED'
        payment.save()
        
        order = payment.order
        order.status = 'REFUNDED'
        order.save()
        
    except Payment.DoesNotExist:
        logger.error(f"Payment not found for refund: {charge['payment_intent']}")

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return JsonResponse({'status': 'invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return JsonResponse({'status': 'invalid signature'}, status=400)

    # Handle payment events
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_payment_success(payment_intent)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        handle_payment_failure(payment_intent)

    return JsonResponse({'status': 'success'})

def handle_payment_success(payment_intent):
    try:
        payment = Payment.objects.get(
            transaction_id=payment_intent['id'],
            status='PENDING'
        )
        payment.status = 'COMPLETED'
        
        # Encrypt and store payment details
        payment.payment_details = cipher_suite.encrypt(
            json.dumps(payment_intent).encode()
        ).decode()
        
        payment.save()
        
        # Update order status
        order = payment.order
        order.status = 'PROCESSING'
        order.save()
        
        # Send confirmation email
        send_order_confirmation(order)
        
    except Payment.DoesNotExist:
        pass

def handle_payment_failure(payment_intent):
    try:
        payment = Payment.objects.get(
            transaction_id=payment_intent['id'],
            status='PENDING'
        )
        payment.status = 'FAILED'
        payment.save()
        
        # Send failure notification
        send_payment_failure_notification(payment.order)
        
    except Payment.DoesNotExist:
        pass

def send_order_confirmation(order):
    subject = f"Order Confirmation - {order.order_number}"
    message = f"Thank you for your order!\n\nOrder Number: {order.order_number}\nTotal: ${order.total_price}"
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        fail_silently=False,
    )

def send_payment_failure_notification(order):
    subject = f"Payment Failed - Order {order.order_number}"
    message = f"Payment for order {order.order_number} failed. Please try again."
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        fail_silently=False,
    )

def send_bank_transfer_instructions(user, order):
    subject = f"Bank Transfer Instructions - Order {order.order_number}"
    message = f"""
    Please transfer ${order.total_price} to:
    
    Bank: Ethiopian Commercial Bank
    Account Name: Betegna Boutique
    Account Number: 1234567890
    
    After transferring, please reply to this email with your payment receipt.
    
    Order Number: {order.order_number}
    """
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def create_shipment(order):
    # In a real implementation, integrate with shipping provider API
    shipping_provider = ShippingProvider.objects.filter(is_active=True).first()
    
    if shipping_provider:
        # Generate tracking number (in real app, get from API)
        tracking_number = f"SHIP-{uuid.uuid4().hex[:10].upper()}"
        
        order.tracking_number = tracking_number
        order.tracking_url = shipping_provider.tracking_url_template.format(
            tracking_number=tracking_number
        )
        order.status = 'SHIPPED'
        order.save()
        
        # Send shipping notification
        # send_shipping_notification(order)
        
        return True
    return False

def send_shipping_notification(order):
    subject = f"Your Order Has Shipped - {order.order_number}"
    message = f"""
    Your order #{order.order_number} has been shipped!
    
    Tracking Number: {order.tracking_number}
    Track Your Package: {order.tracking_url}
    
    Estimated Delivery: {order.shipping_provider.delivery_time}
    """
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        fail_silently=False,
    )





from django.contrib.sessions.backends.db import SessionStore
from django.views.decorators.csrf import csrf_exempt
#AI features here
def track_interaction(request, product, interaction_type, search_query=None):
    """Helper function to track user interactions"""
    if not request.user.is_authenticated and not request.session.session_key:
        request.session.create()
    
    # Skip product tracking if product is None (like for category views)
    if product is None:
        UserInteraction.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            interaction_type=interaction_type,
            search_query=search_query
        )
    else:
        UserInteraction.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            product=product,
            interaction_type=interaction_type,
            search_query=search_query
        )

@csrf_exempt
def track_interaction_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            interaction_type = data.get('interaction_type')
            
            # Validate required fields
            if not interaction_type:
                return JsonResponse({'status': 'error', 'message': 'Interaction type required'}, status=400)
                
            # Handle category views (no product_id)
            if not product_id and interaction_type != 'category_view':
                return JsonResponse({'status': 'error', 'message': 'Product ID required for this interaction'}, status=400)
            
            # Create interaction
            interaction_data = {
                'user': request.user if request.user.is_authenticated else None,
                'session_key': request.session.session_key,
                'interaction_type': interaction_type,
                'search_query': data.get('search_query')
            }
            
            if product_id:
                try:
                    interaction_data['product'] = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Product not found'}, status=404)
            
            UserInteraction.objects.create(**interaction_data)
            
            return JsonResponse({'status': 'success'})
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)



    