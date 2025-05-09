from django.shortcuts import render, get_object_or_404
from .models import FAQCategory, FAQ
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.admin.views.decorators import staff_member_required
from .forms import NewsletterSendForm
from .models import Subscriber, NewsletterTemplate, SentNewsletter


@staff_member_required
def send_newsletter(request):
    if request.method == 'POST':
        form = NewsletterSendForm(request.POST)
        if form.is_valid():
            template = form.cleaned_data['template']
            test_email = form.cleaned_data['test_email']
            
            if test_email:
                # Send test email
                send_single_newsletter(test_email, template)
                messages.success(request, f"Test email sent to {test_email}")
            else:
                # Bulk send to active subscribers
                subscribers = Subscriber.objects.filter(is_active=True)
                count = 0
                for subscriber in subscribers:
                    send_single_newsletter(subscriber.email, template, subscriber.unsubscribe_code)
                    count += 1
                
                # Record the sending
                SentNewsletter.objects.create(
                    template=template,
                    recipients_count=count
                )
                messages.success(request, f"Newsletter sent to {count} subscribers")
            return redirect('admin:index')
    else:
        form = NewsletterSendForm()
    
    return render(request, './admin/newsletter_send.html', {'form': form})

def send_single_newsletter(email, template, unsubscribe_code=None):
    # Prepare context
    context = {
        'content': template.html_content,
        'unsubscribe_link': None
    }
    
    if unsubscribe_code:
        context['unsubscribe_link'] = f"{settings.SITE_URL}/newsletter/unsubscribe/{unsubscribe_code}/"
    
    # Render both HTML and text versions
    html_body = render_to_string('./info/newsletter/email_template.html', context)
    text_body = template.plain_text
    
    # Create email
    email_msg = EmailMultiAlternatives(
        subject=template.subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
        reply_to=[settings.NEWSLETTER_REPLY_TO]
    )
    email_msg.attach_alternative(html_body, "text/html")
    email_msg.send()

def unsubscribe(request, code):
    subscriber = get_object_or_404(Subscriber, unsubscribe_code=code)
    subscriber.is_active = False
    subscriber.save()
    return render(request, './info/newsletter/unsubscribe_success.html')


def faq_category_list(request):
    categories = FAQCategory.objects.prefetch_related('faqs').filter(faqs__is_active=True).distinct()
    context = {
        'categories': categories,
        'page_title': 'Frequently Asked Questions',
    }
    return render(request, './info/category_list.html', context)

def faq_category_detail(request, slug):
    category = get_object_or_404(FAQCategory, slug=slug)
    faqs = category.faqs.filter(is_active=True).order_by('order')
    
    context = {
        'category': category,
        'faqs': faqs,
        'page_title': f'FAQs - {category.name}',
    }
    return render(request, './info/category_detail.html', context)


def about(request):
    context = {

    }

    return render(request, './info/about.html' ,context)


def privacy(request):
    return render(request, './info/privacy.html')

def terms(request):
    return render(request, './info/terms.html')

def return_policy(request):
    return render(request, './info/return.html')