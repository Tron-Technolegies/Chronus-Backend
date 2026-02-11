from django.urls import path
from . import views

urlpatterns = [

    # -------- Guest Session --------
    path('guest/create/', views.create_guest, name='create_guest'),

    # -------- Cart --------
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),

    # -------- Wishlist --------
    path('wishlist/add/', views.add_to_wishlist, name='add_to_wishlist'),

    # -------- Reviews --------
    path('review/add/', views.add_review, name='add_review'),

    # -------- Checkout & Orders --------
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.my_orders, name='my_orders'),
    path("payments/create-intent/", views.CreatePaymentIntentView.as_view(), name="create-payment-intent")

]