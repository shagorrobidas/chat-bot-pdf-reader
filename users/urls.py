
from django.contrib import admin
from django.urls import path, include
from users import views


urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('home/', views.DashboardView.as_view(), name='home'),
    path('chatbot/', views.ChatbotView.as_view(), name='chatbot'),
]