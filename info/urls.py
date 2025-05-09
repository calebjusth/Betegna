from django.urls import path
from .views import *

urlpatterns = [
    path('', about, name='about'),
    path('faq/', faq_category_list, name='category_list'),
    path('faq/<slug:slug>/', faq_category_detail, name='category_detail'),
    path('unsubscribe/<str:code>/', unsubscribe, name='newsletter_unsubscribe'),
    path('admin/send-newsletter/', send_newsletter, name='send_newsletter'),




    #policies
    path('privacy/', privacy, name='privacy'),
    path('terms/', terms, name='terms'),
    path('return/', return_policy, name='return')
]