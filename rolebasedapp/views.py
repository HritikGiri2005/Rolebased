from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import os
import tempfile
from .forms import LoginForm, RegisterForm
from .models import UserProfile
import pandas as pd
from elasticsearch import Elasticsearch
import matplotlib.pyplot as plt
from openpyxl.drawing.image import Image

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


@login_required(login_url='login')
def metrics_dashboard(request):

    role = request.user.profile.role

    # Admin and Rack users can access
    if role not in ['admin', 'rack', 'asset']:

        messages.error(
            request,
            'You do not have permission to access metrics Data.'
        )

        return redirect('dashboard')

    return render(
        request,
        'metrics.html',
        {
            'role': role
        }
    )



from django.http import HttpResponse
from elasticsearch import Elasticsearch
import pandas as pd
from io import BytesIO


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

        # All racks sheet
        df.to_excel(
            writer,
            sheet_name="All Racks",
            index=False
        )

        # Get floor numbers from Rack Name column
        floors = (
            df["Rack Name"]
            .dropna()
            .str.extract(r"(\d+)F")[0]
            .dropna()
            .unique()
        )

        # Floor-wise sheets in numerical order
        for floor in sorted(floors, key=int):

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


                df["Consumed U"] = pd.to_numeric(df["Consumed U"],errors="coerce").fillna(0)
                df["Free U"] = pd.to_numeric(df["Free U"],errors="coerce").fillna(0)

         # ==================================
        # 4. OVERALL LOCATION-WISE SUMMARY
        # ==================================
        #
        # IMPORTANT:
        # Use df here, NOT floor_df
        #

        location_summary = (
            df.groupby("Location")[
                ["Consumed U", "Free U"]
            ]
            .sum()
        )

        # ==================================
        # 5. CREATE OVERALL STACKED BAR CHART
        # ==================================

        fig, ax = plt.subplots(
            figsize=(8, 5)
        )

        location_summary.plot(
            kind="bar",
            stacked=True,
            ax=ax
        )

        ax.set_title(
            "Overall - Consumed U vs Free U"
        )

        ax.set_xlabel("Location")
        ax.set_ylabel("U")

        ax.legend(
            ["Consumed U", "Free U"]
        )

        plt.xticks(
            rotation=30,
            ha="right",
            fontsize = 8
        )

        plt.tight_layout()

        # ==================================
        # 6. SAVE MATPLOTLIB GRAPH IN MEMORY
        # ==================================

        image_data = BytesIO()

        fig.savefig(
            image_data,
            format="png",
            dpi=150,
            bbox_inches="tight"
        )

        plt.close(fig)

        # Move pointer to beginning
        image_data.seek(0)

        # ==================================
        # 7. INSERT GRAPH INTO ALL RACKS
        # ==================================

        worksheet = writer.book["All Racks"]

        img = Image(image_data)

        worksheet.add_image(
            img,
            "P2"
        )

    # ==================================
    # 8. RETURN EXCEL FILE
    # ==================================

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
        floors = df["Rack"].dropna().str.extract(r"(\d+)F")[0].dropna().unique()
        for floor in sorted(floors, key=int):

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
                    sheet_name=f"Floor {floor} Racks",
                    index=False
                )

    return response


def export_metrics_excel(request):

    # -----------------------------------------
    # Fetch data from Elasticsearch
    # -----------------------------------------
    es_response = es.search(
        index="ea-metrics",
        query={
            "match_all": {}
        },
        size=10000
    )

    # -----------------------------------------
    # Extract _source from every document
    # -----------------------------------------
    records = [
        hit["_source"]
        for hit in es_response["hits"]["hits"]
    ]

    # -----------------------------------------
    # Convert to DataFrame
    # -----------------------------------------
    df = pd.DataFrame(records)

    # -----------------------------------------
    # Check if data exists
    # -----------------------------------------
    if df.empty:
        return HttpResponse(
            "No data found",
            status=404
        )

    # -----------------------------------------
    # Check current_timestamp exists
    # -----------------------------------------
    if "current_timestamp" not in df.columns:
        return HttpResponse(
            "current_timestamp field not found",
            status=400
        )

    # -----------------------------------------
    # Convert epoch milliseconds
    # to India datetime
    # -----------------------------------------
    df["current_timestamp"] = pd.to_datetime(
        df["current_timestamp"],
        unit="ms",
        utc=True,
        errors="coerce"
    ).dt.tz_convert("Asia/Kolkata")

    # -----------------------------------------
    # Remove records with invalid timestamp
    # -----------------------------------------
    df = df.dropna(
        subset=["current_timestamp"]
    )

    # -----------------------------------------
    # Sort all data by timestamp
    # -----------------------------------------
    df = df.sort_values(
        by="current_timestamp"
    )

    # -----------------------------------------
    # Create separate DataFrame for filtering
    # -----------------------------------------
    filter_df = df.copy()

    # -----------------------------------------
    # Create 5-minute time bucket
    # -----------------------------------------
    filter_df["time_bucket"] = (
        filter_df["current_timestamp"]
        .dt.floor("5min")
    )

    # -----------------------------------------
    # Create Excel response
    # -----------------------------------------
    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    response["Content-Disposition"] = (
        'attachment; filename="ea-metrics.xlsx"'
    )

    # -----------------------------------------
    # Create Excel workbook
    # -----------------------------------------
    with pd.ExcelWriter(
        response,
        engine="openpyxl"
    ) as writer:

        # =========================================
        # ALL METRICS
        # =========================================
        # Everything is displayed here.
        # No filtering.
        # No column removal.
        # =========================================

        all_df = df.copy()

        # Excel does not support timezone-aware datetime
        all_df["current_timestamp"] = (
            all_df["current_timestamp"]
            .dt.tz_localize(None)
        )

        all_df.to_excel(
            writer,
            sheet_name="All Metrics",
            index=False
        )

        # Set column width for All Metrics
        worksheet = writer.sheets["All Metrics"]

        worksheet.column_dimensions["A"].width = 22

        # =========================================
        # 5-MINUTE TIME-WISE SHEETS
        # =========================================

        for time_bucket, time_df in filter_df.groupby(
            "time_bucket"
        ):

            # -------------------------------------
            # Start time
            # -------------------------------------
            start_time = time_bucket.strftime(
                "%H-%M"
            )

            # -------------------------------------
            # End time
            # -------------------------------------
            end_time = (
                time_bucket +
                pd.Timedelta(minutes=5)
            ).strftime("%H-%M")

            # -------------------------------------
            # Sheet name
            # Example:
            # 18-50_to_18-55
            # -------------------------------------
            sheet_name = (
                f"{start_time}_to_{end_time}"
            )

            # Excel sheet name maximum = 31
            sheet_name = sheet_name[:31]

            # =====================================
            # ONLY THESE 3 COLUMNS
            # =====================================

            time_df = time_df[
                [
                    "current_timestamp",
                    "humidity",
                    "location"
                ]
            ].copy()

            # -------------------------------------
            # Remove timezone information
            # -------------------------------------
            time_df["current_timestamp"] = (
                time_df["current_timestamp"]
                .dt.tz_localize(None)
            )

            # -------------------------------------
            # Write time-wise sheet
            # -------------------------------------
            time_df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False
            )

            # -------------------------------------
            # Set column widths
            # -------------------------------------
            worksheet = writer.sheets[sheet_name]

            worksheet.column_dimensions["A"].width = 22
            worksheet.column_dimensions["B"].width = 12
            worksheet.column_dimensions["C"].width = 30

    # -----------------------------------------
    # Return Excel file
    # -----------------------------------------
    return response