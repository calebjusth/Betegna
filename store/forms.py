# forms.py
from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

class CheckoutForm(forms.Form):
    # Shipping Address
    shipping_name = forms.CharField(max_length=100)
    shipping_address = forms.CharField(widget=forms.Textarea)
    shipping_city = forms.CharField(max_length=100)
    shipping_postal_code = forms.CharField(max_length=20)
    shipping_country = CountryField().formfield(
        widget=CountrySelectWidget(attrs={
            'class': 'form-control',
        })
    )
    shipping_phone = forms.CharField(max_length=20)
    
    # Billing Address (optional)
    billing_same_as_shipping = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'billing-same',
        })
    )
    billing_name = forms.CharField(max_length=100, required=False)
    billing_address = forms.CharField(widget=forms.Textarea, required=False)
    billing_city = forms.CharField(max_length=100, required=False)
    billing_postal_code = forms.CharField(max_length=20, required=False)
    billing_country = CountryField().formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'form-control',
        })
    )
    
    # Payment Method
    PAYMENT_CHOICES = [
        ('CARD', 'Credit/Debit Card'),
        ('PAYPAL', 'PayPal'),
        ('BANK', 'Bank Transfer'),
    ]
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
        })
    )
    
    # Additional Info
    customer_note = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Special instructions...'
        }),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        billing_same = cleaned_data.get('billing_same_as_shipping')
        
        if not billing_same:
            if not cleaned_data.get('billing_name'):
                self.add_error('billing_name', 'This field is required')
            if not cleaned_data.get('billing_address'):
                self.add_error('billing_address', 'This field is required')
            if not cleaned_data.get('billing_city'):
                self.add_error('billing_city', 'This field is required')
            if not cleaned_data.get('billing_postal_code'):
                self.add_error('billing_postal_code', 'This field is required')
            if not cleaned_data.get('billing_country'):
                self.add_error('billing_country', 'This field is required')
        
        return cleaned_data