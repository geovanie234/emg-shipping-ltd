from django import forms
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})


class AdminAwareLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        redirect_url = self.get_redirect_url()
        if redirect_url:
            return redirect_url

        if self.request.user.is_staff:
            return reverse_lazy('admin_dashboard')
        return reverse_lazy('product_list')


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome {user.username}! Your account has been created successfully.")

            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('product_list')

        messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()

    return render(request, 'register.html', {
        'form': form,
        'next': request.POST.get('next') or request.GET.get('next', ''),
    })


def custom_logout(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('product_list')


@login_required
def profile(request):
    recent_orders = request.user.orders.all()[:3]

    return render(request, 'profile.html', {
        'total_orders': request.user.orders.count(),
        'delivered_orders': request.user.orders.filter(status='Delivered').count(),
        'pending_orders': request.user.orders.filter(status='Pending').count(),
        'recent_orders': recent_orders,
    })
