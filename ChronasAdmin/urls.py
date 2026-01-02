from django.urls import path
from ChronasAdmin import views

urlpatterns = [
    path('view_users/', views.view_users, name='view_users'),
    path('add_category/', views.add_category, name='add_category'),
    path('view_categories/', views.view_categories, name='view_categories'),
    path('update_category/<int:category_id>/', views.update_category, name='update_category'),
    path('delete_category/<int:category_id>/', views.delete_category, name='delete_category'),

    path('add_brand/', views.add_brand, name='add_brand'),
    path('view_brands/', views.view_brands, name='view_brands'),
    path('update_brand/<int:brand_id>/', views.update_brand, name='update_brand'),
    path('delete_brand/<int:brand_id>/', views.delete_brand, name='delete_brand'),
]