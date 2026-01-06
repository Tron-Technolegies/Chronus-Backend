from django.shortcuts import render
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
import json
from django.http import HttpResponse


from .models import Category, Brand, Product, Order, Coupon

# Create your views here.

def view_users(request):
    try:
        user = User.objects.get(id=1)
        return JsonResponse({
            "id": user.id,
            "username": user.username,
            "email": user.email
        })
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)     

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
        data = json.loads(request.body)
        name = data.get("name")
        category = data.get("category")
        brand = data.get("brand")
        price = data.get("price")
        description = data.get("description")
        stock = data.get("stock")
        image = data.get("image")

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
            "category": product.category,
            "brand": product.brand,
            "price": product.price,
            "description": product.description,
            "stock": product.stock,
            "image": product.image,
            "created_at": product.created_at
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def view_products(request):
    products = Product.objects.all()

    data = [
        {
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "brand": product.brand,
            "price": product.price,
            "description": product.description,
            "stock": product.stock,
            "image": product.image,
            "created_at": product.created_at
        }
        for product in products
    ]

    return JsonResponse({"products": data}, status=200)

@csrf_exempt
@require_http_methods(["PUT"])
def update_product(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        data = json.loads(request.body)

        name = data.get("name")
        category = data.get("category")
        brand = data.get("brand")
        price = data.get("price")
        description = data.get("description")
        stock = data.get("stock")
        image = data.get("image")

        product.name = name
        product.category = category
        product.brand = brand
        product.price = price
        product.description = description
        product.stock = stock
        product.image = image
        product.save()

        return JsonResponse({
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "brand": product.brand,
            "price": product.price,
            "description": product.description,
            "stock": product.stock,
            "image": product.image,
            "created_at": product.created_at
        })

    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    

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
        expiries_at = data.get("expires_at")

        coupon = Coupon.objects.create(code=code, discount=discount)

        return JsonResponse({
            "id": coupon.id,
            "code": coupon.code,
            "discount": coupon.discount,
            "expires_at": coupon.expires_at,
            "created_at": coupon.created_at
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
            "created_at": coupon.created_at
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
       
