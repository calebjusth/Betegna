from django.urls import path
from .views import *


urlpatterns =[
    path('', home, name='home'),
    path('search/', search, name='search'),
    path('cart/', view_cart, name='cart'),
    path('cart/add/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/count/', cart_count, name='cart_count'),
    # Product URLs
    path('products/', all_products, name='all_products'),
    path('products/<str:category_slug>/', products_by_category, name='products_by_category'),
    path('product/<slug:slug>/', product_detail, name='product_detail'),



    #orders
    path('check-out/', checkout, name='checkout'),
    path('order/confirm/<str:order_number>/', order_confirmation, name='order_confirmation'),
    path('order/failed/<str:order_number>/', order_failed, name='order_failed'),
    path('orders/', order_history, name='order_history'),
    path('orders/<str:order_number>/', order_detail, name='order_detail'),
    path('order/cancel/<str:order_number>/', cancel_order, name='cancel_order'),
    path('offers/', SpecialOffersListView.as_view(), name='special_offers_list'),
    path('offers/<int:pk>/', SpecialOfferDetailView.as_view(), name='special_offer_detail'),
    path('cart/add/<int:product_id>/offer/<int:offer_id>/', add_to_cart, name='add_to_cart_with_offer'),
    path('payment/paypal/<int:order_id>/', process_paypal_payment, name='process_paypal'),
    path('payment/bank/<int:order_id>/', process_bank_transfer, name='process_bank'),
    
    # Webhooks
    path('webhooks/stripe/', stripe_webhook, name='stripe_webhook'),
    path('track-interaction/', track_interaction_view, name='track_interaction'),
    
    # Collection URLs
    path('collections/', all_collections, name='all_collections'),
    path('collections/<slug:slug>/', collection_detail, name='collection_detail'),
]
