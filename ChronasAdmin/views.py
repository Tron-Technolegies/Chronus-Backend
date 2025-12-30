from django.shortcuts import render
from django.contrib.auth.models import User
from django.http import JsonResponse
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