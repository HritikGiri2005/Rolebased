from django.urls import path
from rolebasedapp import views

urlpatterns = [

    # -----------------------------
    # AUTH
    # -----------------------------
    path("", views.login_view, name="home"),
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
    path('export-racks/', views.export_racks_excel, name='export-racks'),
    path("export-assets/",views.export_assets_excel,name="export-assets"),
]