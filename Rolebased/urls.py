from django.urls import path
from rolebasedapp import views

urlpatterns = [

    # -----------------------------
    # AUTH
    # -----------------------------
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # -----------------------------
    # DASHBOARDS
    # -----------------------------
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/asset/', views.asset_dashboard, name='asset'),
    path('dashboard/rack/', views.rack_dashboard, name='rack'),
    path('dashboard/all/', views.all_dashboard, name='all'),

    # -----------------------------
    # EXCEL DOWNLOADS
    # -----------------------------
    # path('download/asset/', views.download_asset_excel, name='download_asset_excel'),
    path('export-racks/', views.export_racks_excel, name='export-racks'),
    # path('download/all/', views.download_all_excel, name='download_all_excel'),

]