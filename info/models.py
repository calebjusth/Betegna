from django.db import models

# Create your models here.
class FAQCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, help_text="Slug for URL if needed (auto linkable)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "FAQ Category"
        verbose_name_plural = "FAQ Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class FAQ(models.Model):
    category = models.ForeignKey(FAQCategory, related_name='faqs', on_delete=models.CASCADE)
    question = models.CharField(max_length=255)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.question
    

class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribe_code = models.CharField(max_length=50, unique=True, editable=False)
    
    def save(self, *args, **kwargs):
        if not self.unsubscribe_code:
            import secrets
            self.unsubscribe_code = secrets.token_urlsafe(24)
        super().save(*args, **kwargs)

class NewsletterTemplate(models.Model):
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=200)
    html_content = models.TextField()
    plain_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class SentNewsletter(models.Model):
    template = models.ForeignKey(NewsletterTemplate, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)
    recipients_count = models.PositiveIntegerField()