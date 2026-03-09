from django.shortcuts import render
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
import json
from django.http import HttpResponse
from datetime import datetime
import cloudinary.uploader
from rest_framework_simplejwt.tokens import RefreshToken

from ChronasAdmin.models import Category, Brand, FineArtSize, Product, Order, Coupon, ProductImage, SubCategory

# Create your views here.


@require_http_methods(["GET"])
def view_users(request):
    users = User.objects.all()

    #  SEARCH
    search_query = request.GET.get("search")
    if search_query:
        users = users.filter(
            username__icontains=search_query
        ) | users.filter(
            email__icontains=search_query
        )

    #  FILTER BY ACTIVE STATUS
    is_active = request.GET.get("is_active")
    if is_active is not None:
        if is_active.lower() == "true":
            users = users.filter(is_active=True)
        elif is_active.lower() == "false":
            users = users.filter(is_active=False)

    #  FILTER BY STAFF
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
        name = request.POST.get("name")
        description = request.POST.get("description", "")
        image = request.FILES.get("image")
        subdescription = request.POST.get("subdescription")

        if not name:
            return JsonResponse({"error": "Category name is required"}, status=400)

        category = Category.objects.create(
            name=name,
            description=description,
            image=image,
            subdescription=subdescription
        )

        return JsonResponse({
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "image": category.image.url if category.image else None,
            "created_at": category.created_at,
            "subdescription": category.subdescription
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



from django.db.models import Count

@require_http_methods(["GET"])
def view_categories(request):
    search = request.GET.get("search", "")

    categories = Category.objects.filter(
        Q(name__icontains=search)
    ).annotate(product_count=Count("product")).order_by("-id")

    data = [
        {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "image": category.image.url if category.image else None,
            "created_at": category.created_at,
            "product_count": category.product_count,
            "subdescription": category.subdescription,
        }
        for category in categories
    ]

    return JsonResponse({"categories": data}, status=200)

@csrf_exempt
@require_http_methods(["POST"])
def update_category(request, category_id):
    try:
        category = Category.objects.get(id=category_id)

        name = request.POST.get("name")
        description = request.POST.get("description")
        image = request.FILES.get("image")
        subdescription = request.POST.get("subdescription")

        if not name:
            return JsonResponse({"error": "Category name is required"}, status=400)

        category.name = name

        if description is not None:
            category.description = description

        if subdescription is not None:
            category.subdescription = subdescription

        if image:
            category.image = image

        category.save()

        return JsonResponse({
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "subdescription": category.subdescription,
            "image": category.image.url if category.image else None,
            "created_at": category.created_at
        })

    except Category.DoesNotExist:
        return JsonResponse({"error": "Category not found"}, status=404)

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
    import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt
@require_http_methods(["POST"])
def add_products(request):
    try:
        name = request.POST.get("name")
        category_id = request.POST.get("category")
        brand_id = request.POST.get("brand")
        price = request.POST.get("price")
        description = request.POST.get("description")
        stock = request.POST.get("stock")
        image = request.FILES.get("image")

        specification = request.POST.get("specification")

        # Convert specification JSON string → dictionary
        if specification:
            try:
                specification = json.loads(specification)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid specification format"}, status=400)
        else:
            specification = {}

        if not name:
            return JsonResponse({"error": "Product name is required"}, status=400)

        if not price:
            return JsonResponse({"error": "Price is required"}, status=400)

        category = None
        if category_id:
            category = Category.objects.filter(id=category_id).first()
            if not category:
                return JsonResponse({"error": "Invalid category"}, status=400)

        subcategory_id = request.POST.get("subcategory")

        subcategory = None
        if subcategory_id:
            subcategory = SubCategory.objects.filter(id=subcategory_id).first()

        brand = None
        if brand_id:
            brand = Brand.objects.filter(id=brand_id).first()
            if not brand:
                return JsonResponse({"error": "Invalid brand"}, status=400)

        is_featured = request.POST.get("is_featured") in ["true", "True", "1"]
        is_best_seller = request.POST.get("is_best_seller") in ["true", "True", "1"]

        product = Product.objects.create(
            name=name,
            category=category,
            subcategory=subcategory,
            brand=brand,
            price=price,
            description=description,
            stock=stock,
            image=image,
            is_featured=is_featured,
            is_best_seller=is_best_seller,
            specification=specification
        )
        sizes = request.POST.get("sizes")

        if sizes:
            try:
                sizes = json.loads(sizes)

                for item in sizes:
                    FineArtSize.objects.create(
                        product=product,
                        size=item.get("size"),
                        price=item.get("price")
                    )

            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid sizes format"}, status=400)

        gallery_images = request.FILES.getlist("images")

        for img in gallery_images:
            ProductImage.objects.create(
                product=product,
                image=img
            )

        return JsonResponse({
            "id": product.id,
            "name": product.name,
            "category": product.category.id if product.category else None,
            "brand": product.brand.id if product.brand else None,
            "price": str(product.price),
            "subcategory": {
                "id": product.subcategory.id,
                "name": product.subcategory.name
            } if product.subcategory else None,
            "description": product.description,
            "stock": product.stock,
            "image": product.image.url if product.image else None,
            "specification": product.specification,
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
            "subcategory": {
                "id": product.subcategory.id,
                "name": product.subcategory.name
            } if getattr(product, "subcategory", None) else None,
            "price": str(product.price),
            "description": product.description,
            "stock": product.stock,
            "image": product.image.url if product.image else None,
            "created_at": product.created_at,
            "gallery": [
                img.image.url for img in product.gallery.all()
            ],
            "specification": product.specification,   
            "is_featured": product.is_featured,
            "is_best_seller": product.is_best_seller,
            "sizes":[
                {
                    "size": s.size,
                    "price": str(s.price)
                }
                for s in product.sizes.all()
            ]
        }
        for product in products
    ]

    return JsonResponse({"products": data}, status=200)

import json

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
        specification = request.POST.get("specification")

        if name:
            product.name = name

        if category_id:
            category = Category.objects.filter(id=category_id).first()
            if not category:
                return JsonResponse({"error": "Invalid category"}, status=400)
            product.category = category

        subcategory_id = request.POST.get("subcategory")

        if subcategory_id is not None:
            if subcategory_id == "":
                product.subcategory = None
            else:
                subcategory = SubCategory.objects.filter(id=subcategory_id).first()
                product.subcategory = subcategory

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
            if product.image:
                cloudinary.uploader.destroy(product.image.public_id)

            product.image = image

        # specification update
        if specification:
            try:
                specification = json.loads(specification)
                product.specification = specification
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid specification format"}, status=400)

        
        
        sizes = request.POST.get("sizes")

        if sizes:
            try:
                sizes = json.loads(sizes)

                # delete old sizes
                product.sizes.all().delete()

                for item in sizes:
                    FineArtSize.objects.create(
                        product=product,
                        size=item.get("size"),
                        price=item.get("price")
                    )

            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid sizes format"}, status=400)
                
        
        product.save()

        gallery_images = request.FILES.getlist("images")

        if gallery_images:
            # delete old gallery files from cloudinary
            for img in product.gallery.all():
                cloudinary.uploader.destroy(img.image.public_id)

            product.gallery.all().delete()

            # add new images
            for img in gallery_images:
                ProductImage.objects.create(product=product, image=img)

        return JsonResponse({
            "message": "Product updated successfully",
            "id": product.id,
            "specification": product.specification
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

        if product.image and getattr(product.image, "public_id", None):
            cloudinary.uploader.destroy(product.image.public_id)

        for img in product.gallery.all():
            if img.image and getattr(img.image, "public_id", None):
                cloudinary.uploader.destroy(img.image.public_id)

        product.delete()

        return JsonResponse({"message": "Product deleted successfully"}, status=200)

    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)
    

@require_http_methods(["GET"])
def view_orders(request):
    orders = Order.objects.prefetch_related("items", "user").all()

    data = []

    for order in orders:
        data.append({
            "id": order.id,
            "user": order.user.username if order.user else "Guest",
            "email": order.email,
            "phone": order.phone,
            "status": order.status,
            "tracking_link": order.tracking_link,
            "shipped_at": order.shipped_at,
            "total_amount": str(order.total_amount),
            "created_at": order.created_at,
        })

    return JsonResponse({"orders": data}, status=200)

from django.utils import timezone

@require_http_methods(["POST"])
def update_order_status(request, order_id):
    try:
        data = json.loads(request.body)

        order = Order.objects.get(id=order_id)

        status = data.get("status")
        tracking_link = data.get("tracking_link")

        if status:
            order.status = status

        # If marked as shipped
        if status == "shipped":
            order.tracking_link = tracking_link
            order.shipped_at = timezone.now()

        order.save()

        return JsonResponse({
            "message": "Order updated successfully",
            "id": order.id,
            "status": order.status,
            "tracking_link": order.tracking_link
        })

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
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


# @csrf_exempt
# def stripe_webhook(request):
#     print("🔔 Stripe webhook called")

#     payload = request.body
#     sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

#     try:
#         event = stripe.Webhook.construct_event(
#             payload,
#             sig_header,
#             settings.STRIPE_WEBHOOK_SECRET
#         )
#     except Exception:
#         return HttpResponse(status=400)

#     print("Stripe Event:", event["type"])
#     return HttpResponse(status=200)

from django.http import HttpResponse
from ChronasAdmin.models import Order
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


# @csrf_exempt
# def stripe_webhook(request):
#     payload = request.body
#     sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

#     try:
#         event = stripe.Webhook.construct_event(
#             payload,
#             sig_header,
#             settings.STRIPE_WEBHOOK_SECRET
#         )
#     except stripe.error.SignatureVerificationError:
#         return HttpResponse(status=400)
#     except Exception:
#         return HttpResponse(status=400)

#     # ✅ handle successful payment
#     if event["type"] == "payment_intent.succeeded":
#         intent = event["data"]["object"]

#         order_id = intent["metadata"].get("order_id")
#         payment_id = intent["id"]

#         try:
#             order = Order.objects.get(id=order_id)
#             order.payment_status = "paid"
#             order.payment_id = payment_id
#             order.status = "processing"
#             order.save()
#             print(f" Order {order_id} marked paid")
#         except Order.DoesNotExist:
#             print(f" Order {order_id} not found")

#     return HttpResponse(status=200)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        print("Webhook signature error:", str(e))
        return HttpResponse(status=400)

    print("WEBHOOK EVENT:", event["type"])

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]

        metadata = intent.get("metadata", {})
        order_id = metadata.get("order_id")

        print("METADATA:", metadata)
        print("ORDER_ID:", order_id)

        if not order_id:
            print("❌ No order_id in metadata")
            return HttpResponse(status=200)

        try:
            order = Order.objects.get(id=int(order_id))
            order.payment_status = "paid"
            order.payment_id = intent["id"]
            order.status = "processing"
            order.save()
            print(f"✅ Order {order_id} marked paid")
        except Order.DoesNotExist:
            print(f"❌ Order {order_id} not found")

    return HttpResponse(status=200)

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
from .models import Order, OrderItem, Product


@require_http_methods(["GET"])
def dashboard_stats(request):

    now = timezone.now()
    today = now.date()
    last_30_days = now - timedelta(days=30)
    previous_30_days = now - timedelta(days=60)

    # BASIC COUNTS

    total_orders = Order.objects.count()

    completed_orders = Order.objects.filter(status="completed").count()
    pending_orders = Order.objects.filter(status="pending").count()
    shipped_orders = Order.objects.filter(status="shipped").count()

    # REVENUE

    total_revenue = Order.objects.filter(
        status="completed"
    ).aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    revenue_last_30_days = Order.objects.filter(
        status="completed",
        created_at__gte=last_30_days
    ).aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    revenue_previous_30_days = Order.objects.filter(
        status="completed",
        created_at__gte=previous_30_days,
        created_at__lt=last_30_days
    ).aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    growth_rate = 0
    if revenue_previous_30_days > 0:
        growth_rate = (
            (revenue_last_30_days - revenue_previous_30_days)
            / revenue_previous_30_days
        ) * 100

    # TODAY ORDERS
    today_orders = Order.objects.filter(
        created_at__date=today
    ).count()

    # AVERAGE ORDER VALUE
    avg_order_value = Order.objects.filter(
        status="completed"
    ).aggregate(
        avg=Avg("total_amount")
    )["avg"] or 0

    # LOW STOCK PRODUCTS

    low_stock_products = Product.objects.filter(
        stock__lt=5
    ).count()

    # MONTHLY SALES (Last 6 Months)

    monthly_sales = defaultdict(float)

    six_months_ago = now - timedelta(days=180)

    orders = Order.objects.filter(
        status="completed",
        created_at__gte=six_months_ago
    )

    for order in orders:
        month_label = order.created_at.strftime("%b")
        monthly_sales[month_label] += float(order.total_amount)

    monthly_sales_data = [
        {"month": k, "revenue": v}
        for k, v in monthly_sales.items()
    ]

    # REVENUE BY CATEGORY

    category_revenue = defaultdict(float)

    items = OrderItem.objects.filter(
        order__status="completed"
    ).select_related("product")

    for item in items:
        category_name = item.product.category.name if item.product and item.product.category else "Unknown"
        category_revenue[category_name] += float(item.get_total_price())

    category_revenue_data = [
        {"category": k, "revenue": v}
        for k, v in category_revenue.items()
    ]

    # TOP SELLING PRODUCTS
    top_products = (
        OrderItem.objects
        .values("product_name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")[:5]
    )


    return JsonResponse({
        "cards": {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "pending_orders": pending_orders,
            "shipped_orders": shipped_orders,
            "today_orders": today_orders,
            "avg_order_value": avg_order_value,
            "low_stock_products": low_stock_products,
            "growth_rate": round(growth_rate, 2),
        },
        "monthly_sales": monthly_sales_data,
        "category_revenue": category_revenue_data,
        "top_products": list(top_products),
    })


from django.contrib.admin.views.decorators import staff_member_required

@csrf_exempt
@require_http_methods(["POST"])
def create_subcategory(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = data.get("name")

    if not name:
        return JsonResponse({"error": "name required"}, status=400)

    if SubCategory.objects.filter(name__iexact=name).exists():
        return JsonResponse({"error": "Subcategory already exists"}, status=400)

    sub = SubCategory.objects.create(name=name)

    return JsonResponse(
        {"id": sub.id, "name": sub.name},
        status=201
    )

from django.http import JsonResponse
from .models import SubCategory


def list_subcategories(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)

    subs = SubCategory.objects.all().order_by("name")

    data = [
        {"id": s.id, "name": s.name}
        for s in subs
    ]

    return JsonResponse(data, safe=False)


from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
import json

@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
@staff_member_required
def update_subcategory(request, pk):
    sub = get_object_or_404(SubCategory, pk=pk)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = data.get("name")

    if not name:
        return JsonResponse({"error": "name required"}, status=400)

    if SubCategory.objects.filter(name__iexact=name).exclude(id=sub.id).exists():
        return JsonResponse({"error": "Subcategory already exists"}, status=400)

    sub.name = name
    sub.save()

    return JsonResponse({"id": sub.id, "name": sub.name})




from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["DELETE"])
@staff_member_required
def delete_subcategory(request, pk):
    sub = get_object_or_404(SubCategory, pk=pk)
    sub.delete()
    return JsonResponse({"message": "Subcategory deleted"})


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

@api_view(["POST"])
@permission_classes([AllowAny])
def admin_login(request):
    email = request.data.get("email")
    password = request.data.get("password")

    try:
        user_obj = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "Invalid credentials"}, status=401)

    user = authenticate(request, username=user_obj.username, password=password)

    if user is None:
        return Response({"error": "Invalid credentials"}, status=401)

    if not user.is_staff:
        return Response({"error": "Access denied. Admins only."}, status=403)

    tokens = get_tokens_for_user(user)

    full_name = f"{user.first_name} {user.last_name}".strip()

    return Response({
        "message": "Admin login successful",
        "user_id": user.id,
        "email": user.email,
        "full_name": full_name,
        "tokens": tokens
    })
