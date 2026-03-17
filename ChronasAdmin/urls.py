from django.urls import path
from ChronasAdmin import views

urlpatterns = [
    path("adminlogin/", views.admin_login, name='login'),
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
    path("dashboard_stats/", views.dashboard_stats, name='dashboard_stats'),

    path("subcategories/create/", views.create_subcategory, name="create_subcategory"),
    path("subcategories/", views.list_subcategories, name='subcategories'),
    path("subcategories/<int:pk>/update/", views.update_subcategory, name='update_subcategory'),
    path("subcategories/<int:pk>/delete/", views.delete_subcategory, name='delete_subcategory'),
    path("payments/ziina/webhook/", views.ziina_webhook, name='ziina_webhook'),
    
    # FRAME
    path("frames/create/", views.create_frame, name="create_frame"),
    path("frames/", views.list_frames, name="list_frames"),
    path("frames/update/<int:frame_id>/", views.update_frame, name="update_frame"),
    path("frames/delete/<int:frame_id>/", views.delete_frame, name="delete_frame"),

    # MATERIAL
    path("materials/create/", views.create_material, name="create_material"),
    path("materials/", views.list_materials, name="list_materials"),
    path("materials/update/<int:material_id>/", views.update_material, name="update_material"),
    path("materials/delete/<int:material_id>/", views.delete_material, name="delete_material"),



]