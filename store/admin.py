from django.contrib import admin
from .models import *
from django.utils.html import format_html

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_featured', 'is_active')
    list_filter = ('category', 'is_featured', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_featured', 'is_active')
    filter_horizontal = ('products',)
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(SpecialOffer)

admin.site.register(Testimonial)
admin.site.register(PaymentMethod)
admin.site.register(SiteConfiguration)
admin.site.register(Cart)
admin.site.register(CartItem)
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price', 'created_at')
    can_delete = False
    show_change_link = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'total_price', 'tracking_url', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'user__username', 'tracking_number')
    readonly_fields = ('order_number', 'created_at', 'updated_at', 'shipping_address_display', 'billing_address_display')
    inlines = [OrderItemInline]
    fieldsets = (
        ("Order Info", {
            'fields': ('order_number', 'user', 'status', 'total_price', 'created_at', 'updated_at')
        }),
        ("Shipping & Billing", {
            'fields': ('shipping_address_display', 'billing_address_display')
        }),
        ("Tracking", {
            'fields': ('tracking_number', 'tracking_url')
        }),
        ("Customer Notes", {
            'fields': ('customer_note',)
        }),
    )

    def status_badge(self, obj):
        color = {
            'PENDING': 'gray',
            'PROCESSING': 'blue',
            'SHIPPED': 'orange',
            'DELIVERED': 'green',
            'CANCELLED': 'red',
            'REFUNDED': 'purple'
        }.get(obj.status, 'black')
        return format_html('<span style="color:{}; font-weight:bold;">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'

    def tracking_link(self, obj):
        if obj.tracking_url:
            return format_html('<a href="{}" target="_blank">Track Shipment</a>', obj.tracking_url)
        return '-'
    tracking_link.short_description = 'Tracking'

    def shipping_address_display(self, obj):
        return format_html('<pre>{}</pre>', obj.shipping_address)
    shipping_address_display.short_description = 'Shipping Address'

    def billing_address_display(self, obj):
        if obj.billing_address:
            return format_html('<pre>{}</pre>', obj.billing_address)
        return '-'
    billing_address_display.short_description = 'Billing Address'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'payment_type', 'amount', 'status', 'created_at')
    list_filter = ('status', 'payment_type')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('payment_details',)
        return self.readonly_fields