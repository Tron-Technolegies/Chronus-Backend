from django.urls import path
from ChronasAdmin import views

urlpatterns = [
    path('view_users/', views.view_users, name='view_users'),
]