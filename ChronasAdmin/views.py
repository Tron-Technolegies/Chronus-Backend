from django.shortcuts import render
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
import json

from .models import Category, Brand

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
    

