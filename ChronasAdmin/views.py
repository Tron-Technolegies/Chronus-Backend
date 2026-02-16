from django.shortcuts import render
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
import json
from django.http import HttpResponse
from datetime import datetime


from .models import Category, Brand, Product, Order, Coupon

# Create your views here.


@require_http_methods(["GET"])
def view_users(request):
    users = User.objects.all()

    # 🔎 SEARCH
    search_query = request.GET.get("search")
    if search_query:
        users = users.filter(
            username__icontains=search_query
        ) | users.filter(
            email__icontains=search_query
        )

    # 🔽 FILTER BY ACTIVE STATUS
    is_active = request.GET.get("is_active")
    if is_active is not None:
        if is_active.lower() == "true":
            users = users.filter(is_active=True)
        elif is_active.lower() == "false":
            users = users.filter(is_active=False)

    # 🔽 FILTER BY STAFF
    is_staff = request.GET.get("is_staff")
    if is_staff is not None:
        if is_staff.lower() == "true":
            users = users.filter(is_staff=True)
        elif is_staff.lower() == "false":
            users = users.filter(is_staff=False)

    data = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "date_joined": user.date_joined,
        }
        for user in users
    ]

    return JsonResponse({
        "count": users.count(),
        "users": data
    }, status=200)

@csrf_exempt
@require_http_methods(["POST"])
def add_category(request):
    try:
        data = json.loads(request.body)
        name = data.get("name")

        if not name:
            return JsonResponse({"error": "Category name is required"}, status=400)

        category = Category.objects.create(name=name)

        return JsonResponse({
            "id": category.id,
            "name": category.name,
            "created_at": category.created_at
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

@require_http_methods(["GET"])
def view_categories(request):
    search = request.GET.get("search", "")

    categories = Category.objects.filter(
        Q(name__icontains=search)
    ).order_by("-id")

    data = [
        {
            "id": category.id,
            "name": category.name,
            "created_at": category.created_at
        }
        for category in categories
    ]

    return JsonResponse({"categories": data}, status=200)


@csrf_exempt
@csrf_exempt
@require_http_methods(["PUT"])
def update_category(request, category_id):
    try:
        category = Category.objects.get(id=category_id)
        data = json.loads(request.body)

        name = data.get("name")
        if not name:
            return JsonResponse({"error": "Category name is required"}, status=400)

        category.name = name
        category.save()

        return JsonResponse({
            "id": category.id,
            "name": category.name,
            "created_at": category.created_at
        })

    except Category.DoesNotExist:
        return JsonResponse({"error": "Category not found"}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_category(request, category_id):
    try:
        category = Category.objects.get(id=category_id)
        category.delete()

        return JsonResponse({"message": "Category deleted successfully"}, status=200)

    except Category.DoesNotExist:
        return JsonResponse({"error": "Category not found"}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def add_brand(request):
    try:
        data = json.loads(request.body)
        name = data.get("name")
        if not name:
            return JsonResponse({"error": "Brand name is required"}, status=400)

        brand = Brand.objects.create(name=name)

        return JsonResponse({
            "id": brand.id,
            "name": brand.name,
            "created_at": brand.created_at
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

@require_http_methods(["GET"])
def view_brands(request):
    search = request.GET.get("search", "")

    brands = Brand.objects.filter(
        Q(name__icontains=search)
    ).order_by("-id")

    data = [
        {
            "id": brand.id,
            "name": brand.name,
            "created_at": brand.created_at
        }
        for brand in brands
    ]

    return JsonResponse({"brands": data}, status=200)


@csrf_exempt
@csrf_exempt
@require_http_methods(["PUT"])
def update_brand(request, brand_id):
    try:
        brand = Brand.objects.get(id=brand_id)
        data = json.loads(request.body)

        name = data.get("name")
        if not name:
            return JsonResponse({"error": "Brand name is required"}, status=400)

        brand.name = name
        brand.save()

        return JsonResponse({
            "id": brand.id,
            "name": brand.name,
            "created_at": brand.created_at
        })

    except Brand.DoesNotExist:
        return JsonResponse({"error": "Brand not found"}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_brand(request, brand_id):
    try:
        brand = Brand.objects.get(id=brand_id)
        brand.delete()

        return JsonResponse({"message": "Brand deleted successfully"}, status=200)

    except Brand.DoesNotExist:
        return JsonResponse({"error": "Brand not found"}, status=404)
    
@csrf_exempt
@require_http_methods(["POST"])
def add_products(request):
    try:
        # ✅ Handle FormData correctly
        name = request.POST.get("name")
        category_id = request.POST.get("category")
        brand_id = request.POST.get("brand")
        price = request.POST.get("price")
        description = request.POST.get("description")
        stock = request.POST.get("stock")
        image = request.FILES.get("image")

        # ✅ Basic validation
        if not name:
            return JsonResponse({"error": "Product name is required"}, status=400)

        if not price:
            return JsonResponse({"error": "Price is required"}, status=400)

        # ✅ Convert Foreign Keys properly
        category = None
        if category_id:
            category = Category.objects.filter(id=category_id).first()
            if not category:
                return JsonResponse({"error": "Invalid category"}, status=400)

        brand = None
        if brand_id:
            brand = Brand.objects.filter(id=brand_id).first()
            if not brand:
                return JsonResponse({"error": "Invalid brand"}, status=400)

        # ✅ Create product
        product = Product.objects.create(
            name=name,
            category=category,
            brand=brand,
            price=price,
            description=description,
            stock=stock,
            image=image
        )

        return JsonResponse({
            "id": product.id,
            "name": product.name,
            "category": product.category.id if product.category else None,
            "brand": product.brand.id if product.brand else None,
            "price": str(product.price),
            "description": product.description,
            "stock": product.stock,
            "image": product.image.url if product.image else None,
            "created_at": product.created_at,
        }, status=201)

    except Exception as e:
        return JsonResponse({
            "error": "Something went wrong",
            "details": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def view_products(request):
    products = Product.objects.all()

    data = [
        {
            "id": product.id,
            "name": product.name,
            "category": {
                "id": product.category.id,
                "name": product.category.name
            } if product.category else None,
            "brand": {
                "id": product.brand.id,
                "name": product.brand.name
            } if product.brand else None,
            "price": str(product.price),
            "description": product.description,
            "stock": product.stock,
            "image": product.image.url if product.image else None,
            "created_at": product.created_at,
        }
        for product in products
    ]

    return JsonResponse({"products": data}, status=200)

@csrf_exempt
@require_http_methods(["POST"])
def update_product(request, product_id):
    try:
        product = Product.objects.get(id=product_id)

        name = request.POST.get("name")
        category_id = request.POST.get("category")
        brand_id = request.POST.get("brand")
        price = request.POST.get("price")
        description = request.POST.get("description")
        stock = request.POST.get("stock")
        image = request.FILES.get("image")

        if name:
            product.name = name

        if category_id:
            category = Category.objects.filter(id=category_id).first()
            if not category:
                return JsonResponse({"error": "Invalid category"}, status=400)
            product.category = category

        if brand_id:
            brand = Brand.objects.filter(id=brand_id).first()
            if not brand:
                return JsonResponse({"error": "Invalid brand"}, status=400)
            product.brand = brand

        if price:
            product.price = price

        if description:
            product.description = description

        if stock:
            product.stock = stock

        if image:
            product.image = image

        product.save()

        return JsonResponse({
            "message": "Product updated successfully",
            "id": product.id
        })

    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_product(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        product.delete()

        return JsonResponse({"message": "Product deleted successfully"}, status=200)

    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)
    

@csrf_exempt
@require_http_methods(["GET"])
def view_orders(request):
    orders = Order.objects.all()

    data = [
        {
            "id": order.id,
            "user": order.user,
            "product": order.product,
            "quantity": order.quantity,
            "created_at": order.created_at
        }
        for order in orders
    ]

    return JsonResponse({"orders": data}, status=200)

@csrf_exempt
@require_http_methods(["POST"])
def update_order_status(request, order_id):
    try:
        data = json.loads(request.body)
        status = data.get("status")

        order = Order.objects.get(id=order_id)
        order.status = status
        order.save()

        return JsonResponse({"message": "Order status updated successfully"}, status=200)

    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    

@csrf_exempt
@require_http_methods(["POST"])
def add_coupon(request):
    try:
        data = json.loads(request.body)

        code = data.get("code")
        discount = data.get("discount")
        expiration_date = data.get("expiration_date")

        if not expiration_date:
            return JsonResponse({"error": "Expiration date is required"}, status=400)

        # Convert string to date
        expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()

        coupon = Coupon.objects.create(
            code=code,
            discount=discount,
            expiration_date=expiration_date
        )

        return JsonResponse({
            "id": coupon.id,
            "code": coupon.code,
            "discount": coupon.discount,
            "expiration_date": coupon.expiration_date,
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

@csrf_exempt
@require_http_methods(["GET"])
def view_coupons(request):
    coupons = Coupon.objects.all()

    data = [
        {
            "id": coupon.id,
            "code": coupon.code,
            "discount": coupon.discount,
            "expiration_date": coupon.expiration_date,
            "created_at": coupon.created_at,
        }
        for coupon in coupons
    ]

    return JsonResponse({"coupons": data}, status=200)


@csrf_exempt
@require_http_methods(["PUT"])

def update_coupon(request, coupon_id):
    try:
        coupon = Coupon.objects.get(id=coupon_id)
        data = json.loads(request.body)

        code = data.get("code")
        discount = data.get("discount")

        coupon.code = code
        coupon.discount = discount
        coupon.save()

        return JsonResponse({
            "id": coupon.id,
            "code": coupon.code,
            "discount": coupon.discount,
            "created_at": coupon.created_at
        })

    except Coupon.DoesNotExist:
        return JsonResponse({"error": "Coupon not found"}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_coupon(request, coupon_id):
    try:
        coupon = Coupon.objects.get(id=coupon_id)
        coupon.delete()

        return JsonResponse({"message": "Coupon deleted successfully"}, status=200)

    except Coupon.DoesNotExist:
        return JsonResponse({"error": "Coupon not found"}, status=404)
       


from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
def stripe_webhook(request):
    print("🔔 Stripe webhook called")

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        return HttpResponse(status=400)

    print("Stripe Event:", event["type"])
    return HttpResponse(status=200)
