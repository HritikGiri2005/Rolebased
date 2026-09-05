from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import LoginForm, RegisterForm
from .models import UserProfile


# -----------------------------
# LOGIN
# -----------------------------

def login_view(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':

        form = LoginForm(
            request,
            data=request.POST
        )

        if form.is_valid():

            user = form.get_user()

            login(request, user)

            return redirect('dashboard')

    else:
        form = LoginForm()

    return render(
        request,
        'login.html',
        {
            'form': form
        }
    )


# -----------------------------
# LOGOUT
# -----------------------------

def logout_view(request):

    logout(request)

    return redirect('login')


# -----------------------------
# REGISTER
# -----------------------------

def register_view(request):

    if request.method == 'POST':

        form = RegisterForm(request.POST)

        if form.is_valid():

            # Create User
            user = form.save(commit=False)

            user.set_password(
                form.cleaned_data['password']
            )

            user.save()

            # Get selected role
            role = form.cleaned_data['role']

            # Create UserProfile
            UserProfile.objects.create(
                user=user,
                role=role
            )

            messages.success(
                request,
                'Registration successful. Please login.'
            )

            return redirect('login')

    else:

        form = RegisterForm()

    return render(
        request,
        'register.html',
        {
            'form': form
        }
    )


# -----------------------------
# MAIN DASHBOARD
# -----------------------------

@login_required(login_url='login')
def dashboard_view(request):

    try:
        role = request.user.profile.role

    except UserProfile.DoesNotExist:
        messages.error(
            request,
            'No role has been assigned to your account.'
        )
        return redirect('logout')

    # Admin → Asset dashboard by default
    if role == 'admin':
        return redirect('asset')

    # Asset user → Asset dashboard
    elif role == 'asset':
        return redirect('asset')

    # Rack user → Rack dashboard
    elif role == 'rack':
        return redirect('rack')

    # Unknown role
    else:
        messages.error(
            request,
            'Invalid user role.'
        )

        return redirect('logout')


# -----------------------------
# ASSET DASHBOARD
# -----------------------------

@login_required(login_url='login')
def asset_dashboard(request):

    role = request.user.profile.role

    # Admin and Asset users can access
    if role not in ['admin', 'asset']:

        messages.error(
            request,
            'You do not have permission to access Asset Data.'
        )

        return redirect('dashboard')

    return render(
        request,
        'asset.html',
        {
            'role': role
        }
    )


# -----------------------------
# RACK DASHBOARD
# -----------------------------

@login_required(login_url='login')
def rack_dashboard(request):

    role = request.user.profile.role

    # Admin and Rack users can access
    if role not in ['admin', 'rack']:

        messages.error(
            request,
            'You do not have permission to access Rack Data.'
        )

        return redirect('dashboard')

    return render(
        request,
        'rack.html',
        {
            'role': role
        }
    )


# -----------------------------
# ALL DATA DASHBOARD
# -----------------------------

@login_required(login_url='login')
def all_dashboard(request):

    role = request.user.profile.role

    # Only Admin can access
    if role != 'admin':

        messages.error(
            request,
            'Only administrators can access all data.'
        )

        return redirect('dashboard')

    return render(
        request,
        'all.html',
        {
            'role': role
        }
    )