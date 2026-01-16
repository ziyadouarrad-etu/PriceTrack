from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),      # Pure aesthetic root
    path('search/', views.search_view, name='search'), # The scraper (protected)
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('history/', views.history_view, name='history'),
    path('history/snapshot/<int:pk>/', views.snapshot_view, name='snapshot_view'),
]