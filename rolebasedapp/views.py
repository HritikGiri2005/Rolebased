from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import LoginForm, RegisterForm
from .models import UserProfile

from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from django.http import HttpResponse

es = Elasticsearch(
    "http://localhost:9200"
)

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

# -----------------------------
# DOWNLOAD CSV
# -----------------------------

@login_required(login_url='login')
@login_required(login_url='login')
def download_excel(request):

    # Check Elasticsearch
    if not es.ping():

        return HttpResponse(
            "Elasticsearch is not available.",
            status=500
        )

    try:

        # Create Excel workbook
        workbook = Workbook()

        # Remove default sheet
        default_sheet = workbook.active
        workbook.remove(default_sheet)

        # Elasticsearch indices
        indices = {
            "ea_assets": "Assets",
            "ea-racks": "Racks"
        }

        # Process each index
        for index_name, sheet_name in indices.items():

            # Check if index exists
            if not es.indices.exists(index=index_name):
                continue

            # Create worksheet
            worksheet = workbook.create_sheet(
                title=sheet_name
            )

            # Get all Elasticsearch documents
            documents = scan(
                es,
                index=index_name,
                query={
                    "query": {
                        "match_all": {}
                    }
                }
            )

            all_data = []

            for document in documents:

                source = document.get(
                    "_source",
                    {}
                )

                all_data.append(source)

            # No data
            if not all_data:

                worksheet.append([
                    "No data found"
                ])

                continue

            # Get all unique columns
            columns = []

            for data in all_data:

                for key in data.keys():

                    if key not in columns:
                        columns.append(key)

            # Add headers
            worksheet.append(columns)

            # Add data
            for data in all_data:

                row = []

                for column in columns:

                    value = data.get(
                        column,
                        ""
                    )

                    # Handle None
                    if value is None:
                        value = ""

                    # Handle lists/dictionaries
                    if isinstance(value, (list, dict)):
                        value = str(value)

                    row.append(value)

                worksheet.append(row)

            # Freeze header row
            worksheet.freeze_panes = "A2"

            # Auto-adjust column width
            for column_number in range(
                1,
                worksheet.max_column + 1
            ):

                max_length = 0

                column_letter = get_column_letter(
                    column_number
                )

                for cell in worksheet[column_letter]:

                    if cell.value is not None:

                        length = len(
                            str(cell.value)
                        )

                        if length > max_length:
                            max_length = length

                # Limit very large columns
                max_length = min(
                    max_length + 2,
                    50
                )

                worksheet.column_dimensions[
                    column_letter
                ].width = max_length

        # Create response
        response = HttpResponse(
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

        # Excel filename
        response["Content-Disposition"] = (
            'attachment; filename="DataCenter_Data.xlsx"'
        )

        # Save workbook into response
        workbook.save(response)

        return response

    except Exception as e:

        return HttpResponse(
            f"Error creating Excel file: {str(e)}",
            status=500
        )
