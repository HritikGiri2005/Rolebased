from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import LoginForm, RegisterForm
from .models import UserProfile
import pandas as pd
from elasticsearch import Elasticsearch

es = Elasticsearch([{'host': 'localhost', 'port':9200, 'scheme':'http'}]) #update host and port as needed



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


from django.http import HttpResponse
from elasticsearch import Elasticsearch
import pandas as pd


# Elasticsearch connection
es = Elasticsearch("http://localhost:9200")


def export_racks_excel(request):

    # Fetch data from ea-racks
    response = es.search(
        index="ea-racks",
        query={
            "match_all": {}
        },
        size=10000
    )

    # Extract _source from every document
    records = [
        hit["_source"]
        for hit in response["hits"]["hits"]
    ]

    # Convert to DataFrame
    df = pd.DataFrame(records)

    # Arrange columns in required order
    df = df[
        [
            "Rack Name",
            "Location",
            "Row",
            "Rack U Size",
            "Consumed U",
            "Free U",
            "Rack Make",
            "Rack Type",
            "IP Address",
            "Gateway ID",
            "Module ID",
            "Address ID",
            "Created By",
            "timestamp"
        ]
    ]

    #  # Drop unwanted columns
    # columns_to_drop = [
    #     "SR No.",
    #     "Asset Mount",
    #     "Application Name"
    # ]
    
    # df = df.drop(columns=columns_to_drop, errors="ignore")

    # Create Excel response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response["Content-Disposition"] = (
        'attachment; filename="ea_racks.xlsx"'
    )

# Create multiple sheets
    with pd.ExcelWriter(response, engine="openpyxl") as writer:

        # All assets sheet
        df.to_excel(
            writer,
            sheet_name="All Racks   ",
            index=False
        )

        # Floor-wise sheets
        for floor in range(1, 10):

            floor_df = df[
                df["Rack Name"].str.contains(
                    f"{floor}F",
                    na=False
                )
            ]

            # Create sheet only if records exist
            if not floor_df.empty:

                floor_df.to_excel(
                    writer,
                    sheet_name=f"Floor {floor} Racks",
                    index=False
                )

    return response


def export_assets_excel(request):

    # Fetch data from ea-racks
    response = es.search(
        index="ea_assets",
        query={
            "match_all": {}
        },
        size=10000
    )

    # Extract _source from every document
    records = [
        hit["_source"]
        for hit in response["hits"]["hits"]
    ]

    # Convert to DataFrame
    df = pd.DataFrame(records)

    #  # Drop unwanted columns
    df = df.drop( 
        columns=[
        "SR No.",
        "asset_id",
        "timestamp"
    ],
    errors="ignore")

    #Filter Rack Names floorwise

    
    # Create Excel response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response["Content-Disposition"] = (
        'attachment; filename="ea_assets.xlsx"'
    )

    # Create multiple sheets
    with pd.ExcelWriter(response, engine="openpyxl") as writer:

        # All assets sheet
        df.to_excel(
            writer,
            sheet_name="All Assets",
            index=False
        )

        # Floor-wise sheets
        for floor in range(1, 10):

            floor_df = df[
                df["Rack"].str.contains(
                    f"{floor}F",
                    na=False
                )
            ]

            # Create sheet only if records exist
            if not floor_df.empty:

                floor_df.to_excel(
                    writer,
                    sheet_name=f"{floor}th Floor Racks",
                    index=False
                )

    return response