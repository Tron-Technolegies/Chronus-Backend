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

    path('add_products/', views.add_products, name='add_products'),
    path('view_products/', views.view_products, name='view_products'),
    path('update_product/<int:product_id>/', views.update_product, name='update_product'),
    path('delete_product/<int:product_id>/', views.delete_product, name='delete_product'),

    path('view_orders/', views.view_orders, name='view_orders'),
    path('update_order/<int:order_id>/', views.update_order_status, name='update_order_status'),

    path('add_coupon/', views.add_coupon, name='add_coupon'),
    path('view_coupons/', views.view_coupons, name='view_coupons'),
    path('update_coupon/<int:coupon_id>/', views.update_coupon, name='update_coupon'),
    path('delete_coupon/<int:coupon_id>/', views.delete_coupon, name='delete_coupon'),

    path("stripe/webhook/", views.stripe_webhook, name='stripe_webhook'),

]