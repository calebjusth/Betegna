from datetime import timezone
from django.db import models
from django.core.validators import MinValueValidator

from django.contrib.auth import get_user_model
from datetime import timezone
import uuid
from django.utils import timezone

from main import settings


User = get_user_model()

class Product(models.Model):
    PRODUCT_CATEGORIES = [
    # Fashion & Accessories
    ('CLOTHING', 'Traditional Clothing'),
    ('FASHION', 'Modern Clothing'),
    ('FOOTWEAR', 'Footwear'),
    ('BAGS', 'Bags & Purses'),
    ('JEWELRY', 'Jewelry'),
    ('ACCESSORIES', 'Fashion Accessories'),
    ('WATCHES', 'Watches'),

    # Beauty & Personal Care
    ('BEAUTY', 'Beauty Products'),
    ('SKINCARE', 'Skincare'),
    ('HAIRCARE', 'Haircare'),
    ('FRAGRANCE', 'Fragrances & Perfumes'),
    ('PERSONAL_CARE', 'Personal Care'),

    # Electronics
    ('PHONES', 'Mobile Phones'),
    ('LAPTOPS', 'Laptops'),
    ('COMPUTERS', 'Desktops & PCs'),
    ('TVS', 'Televisions'),
    ('AUDIO', 'Audio Equipment'),
    ('GAMING', 'Gaming Consoles & Accessories'),
    ('CAMERAS', 'Cameras & Photography'),

    # Home & Kitchen
    ('FURNITURE', 'Furniture'),
    ('HOME_DECOR', 'Home Decor'),
    ('KITCHEN', 'Kitchenware'),
    ('BEDDING', 'Bedding & Linens'),
    ('LIGHTING', 'Lighting'),
    ('TOOLS', 'Home Tools & Hardware'),

    # Food & Beverage
    ('COFFEE', 'Ethiopian Coffee'),
    ('TEA', 'Tea'),
    ('SPICES', 'Spices & Herbs'),
    ('PACKAGED_FOODS', 'Packaged Foods'),
    ('SNACKS', 'Snacks & Beverages'),
    ('GOURMET', 'Gourmet Foods'),

    # Art & Craft
    ('HANDICRAFT', 'Handicrafts'),
    ('PAINTINGS', 'Paintings'),
    ('SCULPTURE', 'Sculptures'),
    ('ART_SUPPLIES', 'Art Supplies'),

    # Books & Stationery
    ('BOOKS', 'Books & Literature'),
    ('NOTEBOOKS', 'Notebooks & Journals'),
    ('OFFICE_SUPPLIES', 'Office Supplies'),

    # Kids & Baby
    ('TOYS', 'Toys & Games'),
    ('BABY_CLOTHING', 'Baby Clothing'),
    ('BABY_CARE', 'Baby Care'),
    ('KIDS_FURNITURE', 'Kids Furniture'),

    # Sports & Outdoors
    ('SPORTS', 'Sports Equipment'),
    ('FITNESS', 'Fitness & Gym'),
    ('CAMPING', 'Camping & Hiking'),
    ('BICYCLES', 'Bicycles & Accessories'),

    # Health & Wellness
    ('HEALTH', 'Health Products'),
    ('VITAMINS', 'Vitamins & Supplements'),
    ('WELLNESS', 'Wellness & Therapy'),

    # Automotive
    ('CAR_ACCESSORIES', 'Car Accessories'),
    ('MOTORCYCLE_PARTS', 'Motorcycle Parts'),
    ('CAR_CARE', 'Car Care Products'),

    # Tech Accessories
    ('PHONE_ACCESSORIES', 'Phone Accessories'),
    ('COMPUTER_ACCESSORIES', 'Computer Accessories'),
    ('CHARGERS', 'Chargers & Power Banks'),
    ('SMART_DEVICES', 'Smart Devices'),

    # Others
    ('MUSICAL_INSTRUMENTS', 'Musical Instruments'),
    ('PETS', 'Pet Supplies'),
    ('PLANTS', 'Indoor Plants & Gardening'),
    ('EVENT_SUPPLIES', 'Event & Party Supplies'),
    ('GIFTS', 'Gifts & Special Items'),
    ('RELIGIOUS_ITEMS', 'Religious & Cultural Items'),
    ('CLEANING', 'Cleaning Products'),
]

    
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=PRODUCT_CATEGORIES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name

    def get_discount_percentage(self):
        if self.old_price:
            return int(((self.old_price - self.price) / self.old_price) * 100)
        return 0
    

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=100, blank=True)
    is_feature = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['is_feature', 'created_at']

    def __str__(self):
        return f"Image for {self.product.name}"
    

class Collection(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For the hero image in collection cards
    hero_image = models.ImageField(upload_to='collections/')
    
    # For the new arrivals section with multiple images
    additional_image_1 = models.ImageField(upload_to='collections/', blank=True, null=True)
    additional_image_2 = models.ImageField(upload_to='collections/', blank=True, null=True)
    
    products = models.ManyToManyField(Product, related_name='collections', blank=True)

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    

class SpecialOffer(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    discount_percentage = models.PositiveIntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    products = models.ManyToManyField(Product, related_name='special_offers')
    image = models.ImageField(upload_to='offers/')
    created_at = models.DateTimeField(auto_now_add=True)

    def get_discounted_price(self, product):
        """
        Calculate the discounted price for a product in this offer
        """
        if product in self.products.all():
            return product.price * (100 - self.discount_percentage) / 100
        return product.price
    
    def get_products_with_discounts(self):
        """
        Return a queryset of products with their discounted prices
        """
        products = self.products.all()
        for product in products:
            product.discounted_price = self.get_discounted_price(product)
        return products
    
    def is_product_in_offer(self, product):
        """
        Check if a product is included in this offer
        """
        return self.products.filter(pk=product.pk).exists()

    class Meta:
        ordering = ['-start_date']
        
    def __str__(self):
        return self.title

    def is_currently_active(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date and self.is_active
    

class Testimonial(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    customer_name = models.CharField(max_length=100)
    customer_location = models.CharField(max_length=100)
    content = models.TextField()
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # For the avatar image
    avatar = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Testimonial by {self.customer_name}"

    def get_star_rating(self):
        return range(self.rating)
    

class PaymentMethod(models.Model):
    PAYMENT_TYPES = [
        ('CARD', 'Credit/Debit Card'),
        ('MOBILE', 'Mobile Payment'),
        ('BANK', 'Bank Transfer'),
        ('CASH', 'Cash on Delivery'),
    ]
    
    name = models.CharField(max_length=100)
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPES)
    is_active = models.BooleanField(default=True)
    icon_class = models.CharField(max_length=50, help_text="Font Awesome icon class")
    additional_info = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name
    

class Payment(models.Model):
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    PAYMENT_TYPES = [
        ('CARD', 'Credit/Debit Card'),
        ('PAYPAL', 'PayPal'),
        ('BANK', 'Bank Transfer'),
    ]
    
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_details = models.JSONField(default=dict)  # Stores encrypted payment info
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.get_payment_type_display()} Payment - {self.amount}"
    

class SiteConfiguration(models.Model):
    site_name = models.CharField(max_length=100, default="Zema Boutique")
    hero_title = models.CharField(max_length=200)
    hero_description = models.TextField()
    hero_button_text = models.CharField(max_length=50, default="Shop Now")
    hero_button_link = models.CharField(max_length=100, default="/products")
    hero_image = models.ImageField(upload_to='site/')
    secondary_button_text = models.CharField(max_length=50, default="Learn More")
    secondary_button_link = models.CharField(max_length=100, default="/about")
    
    # Social media links
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Configuration"
        
    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)




class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self):
        """Total before any discounts or shipping"""
        return sum(item.product.price * item.quantity for item in self.items.all())
    
    @property
    def total_discount(self):
        """Total savings from all special offers"""
        return sum(item.savings for item in self.items.all())
    
    @property
    def total_price(self):
        """Final total after discounts"""
        return self.subtotal - self.total_discount
    
    def get_discount_summary(self):
        """Returns a summary of all applied discounts"""
        offers = {}
        for item in self.items.filter(special_offer__isnull=False):
            offer = item.special_offer
            if offer.id not in offers:
                offers[offer.id] = {
                    'offer': offer,
                    'total_savings': 0,
                    'items': []
                }
            offers[offer.id]['total_savings'] += item.savings
            offers[offer.id]['items'].append(item)
        return offers.values()

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)


    special_offer = models.ForeignKey(SpecialOffer, on_delete=models.SET_NULL, null=True, blank=True)
    
    @property
    def unit_price(self):
        """Returns the price per unit, considering any active offer"""
        if self.special_offer and self.special_offer.is_currently_active():
            return self.product.price * (100 - self.special_offer.discount_percentage) / 100
        return self.product.price
    
    @property
    def total_price(self):
        """Returns the total price for this line item (unit_price * quantity)"""
        return self.unit_price * self.quantity
    
    @property
    def savings(self):
        """Returns how much the customer saved with this offer"""
        if self.special_offer and self.special_offer.is_currently_active():
            return (self.product.price * self.quantity) - self.total_price
        return 0
    
    def __str__(self):
        offer_text = f" ({self.special_offer.discount_percentage}% OFF)" if self.special_offer else ""
        return f"{self.quantity} x {self.product.name}{offer_text}"

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def total_price(self):
        return self.product.price * self.quantity

class Order(models.Model):
    ORDER_STATUS = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='PENDING')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.JSONField()  # Stores address as JSON
    billing_address = models.JSONField(null=True, blank=True)
    customer_note = models.TextField(blank=True)
    tracking_number = models.CharField(max_length=50, blank=True)
    tracking_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.order_number
    def can_cancel(self):
        return self.status == 'PENDING'
    
    def cancel(self):
        if self.can_cancel():
            self.status = 'CANCELLED'
            self.save()
            return True
        return False

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        return f"ORD-{uuid.uuid4().hex[:10].upper()}"

        
    def __str__(self):
        return self.order_number

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        offer_text = f" ({self.special_offer.discount_percentage}% OFF)" if self.special_offer else ""
        return f"{self.quantity} x {self.product.name}{offer_text}"

    def __str__(self):
        return f"{self.quantity} x {self.product.name if self.product else '[deleted]'}"
    
class ShippingProvider(models.Model):
    name = models.CharField(max_length=100)
    tracking_url_template = models.CharField(
        max_length=200,
        help_text="Use {tracking_number} as placeholder"
    )
    is_active = models.BooleanField(default=True)
    delivery_time = models.CharField(max_length=50, help_text="e.g., 3-5 business days")

    def __str__(self):
        return self.name


class SearchLog(models.Model):
    query = models.CharField(max_length=255)
    count = models.PositiveIntegerField(default=1)
    last_searched = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-count', '-last_searched']
        
    def __str__(self):
        return f"{self.query} ({self.count})"
    


#Ai features
# models.py
class UserInteraction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)  # Changed this line
    interaction_type = models.CharField(max_length=20, choices=[
        ('view', 'Product View'),
        ('search_click', 'Search Click'), 
        ('wishlist', 'Added to Wishlist'),
        ('cart', 'Added to Cart'),
        ('category_view', 'Category View')  # Added new type
    ])
    search_query = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'session_key']),
            models.Index(fields=['product']),
            models.Index(fields=['interaction_type']),
        ]
        