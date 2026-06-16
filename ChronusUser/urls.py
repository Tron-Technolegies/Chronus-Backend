from django.urls import path
from . import views

urlpatterns = [

    # -------- Guest Session --------
    path('guest/create/', views.create_guest, name='create_guest'),

    # -------- Cart --------
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name='remove_from_cart'),
    # path("cart/clear/", views.clear_cart, name= 'clear_cart'),

    # -------- Wishlist --------
    path('wishlist/add/', views.add_to_wishlist, name='add_to_wishlist'),

    # -------- Reviews --------
    path('review/add/', views.add_review, name='add_review'),

    # -------- Checkout & Orders --------
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.my_orders, name='my_orders'),
    path("payments/create-intent/", views.CreatePaymentIntentView.as_view(), name="create-payment-intent"),

    path("signup/", views.signup, name='signup'),
    path("login/", views.login, name='login'),

    path("products/", views.view_products, name='view_products'),
    path("products/<int:product_id>/", views.view_single_product, name='view_single_product'),
    path('view_brands/', views.view_brands, name='view_brands'),
    path('view_categories/', views.view_categories, name='view_categories'),
    path('view_coupons/', views.view_coupons, name='view_coupons'),
    path("subcategories/", views.list_subcategories, name='subcategories'),
    path("payments/ziina/create/", views.CreateZiinaPayment.as_view(), name='ziina-payment-intent'),
    path("calculate-price/", views.calculate_price, name="calculate_price"),


    path("track-order/<int:order_id>/", views.track_order, name='track_order'),
    path("payments/tabby/",views.CreateTabbyPayment.as_view(),name="tabby-payment"),
    path("forgot-password/",views.forgot_password, name='forgot_password'),
    path("reset-password/",views.reset_password, name='reset_password'),

    path("addresses/", views.view_addresses, name="view_addresses"),
    path("addresses/add/", views.add_address, name="add_address"),
    path("addresses/<int:address_id>/update/", views.update_address, name="update_address"),
    path("addresses/<int:address_id>/delete/", views.delete_address, name="delete_address"),

]