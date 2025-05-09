from django.contrib import admin
from .models import *
from django.utils.html import format_html
from django.urls import reverse
# Register your models here.


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}



@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('category', 'question', 'answer', 'is_active', 'order')
    list_filter = ('category', 'is_active')
    search_fields = ('question', 'answer')




@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'subscribed_at')
    list_filter = ('is_active',)
    search_fields = ('email',)

@admin.register(NewsletterTemplate)
class NewsletterTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    prepopulated_fields = {'name': ('subject',)}

@admin.register(SentNewsletter)
class SentNewsletterAdmin(admin.ModelAdmin):
    list_display = ('template', 'sent_at', 'recipients_count')
    readonly_fields = ('sent_at', 'recipients_count')