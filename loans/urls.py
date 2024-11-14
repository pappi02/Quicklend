from django.urls import include, path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from . import views
from django.contrib.auth.views import LogoutView


urlpatterns = [
    # Set the login page as the homepage (root URL '/')
    path('', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'), # Login page at root
    
    # Redirect to loan list page after login
    path('loan-list/', login_required(views.loan_list), name='loan_list'),  # Loan list after login

    # Other URL patterns
    path('loan/<int:loan_id>/', views.loan_detail, name='loan_detail'),
    path('loan_reation_success/', views.loan_creation_success, name='loan_creation_success'),
    
    path('create/', views.create_loan, name='create_loan'),
    
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    
    path('account/', include('two_factor.urls')),  # Two-factor authentication (if you have it enabled)

    path('dashboard/', login_required(views.dashboard), name='dashboard'),
    

    path('loan/<int:loan_id>/payment-confirmation/', views.payment_confirmation, name='payment_confirmation'),

    # Django's default authentication URLs (login, logout, password reset, etc.)
    path('accounts/', include('django.contrib.auth.urls')),  # Default authentication URLs for login, logout, password reset
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)