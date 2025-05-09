from django import forms
from .models import NewsletterTemplate

class NewsletterSendForm(forms.Form):
    template = forms.ModelChoiceField(queryset=NewsletterTemplate.objects.all())
    test_email = forms.EmailField(required=False, 
                                help_text="Send test email before bulk sending")