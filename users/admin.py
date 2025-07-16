from django.contrib import admin
from users.models import CustomUser, ChatSession, ChatMessage
# Register your models here.
admin.site.site_header = "Core Admin"
admin.site.site_title = "Core Admin Portal"
admin.site.index_title = "Welcome to Core Researcher Portal"

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_active', 'is_staff')


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'user', 'created_at')
    


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'sender', )
    
