from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages

def is_cashier(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'cashier'

@login_required
@user_passes_test(is_cashier)
def cashier_dashboard(request):
    return render(request, 'users/cashier_dashboard.html', {})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login') # Assuming 'login' is the name of your login URL
    else:
        form = UserCreationForm()
    return render(request, 'users/register.html', {'form': form})
