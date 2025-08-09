from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    FacebookAccount, ThreadsApp, ThreadsAccount, InstagramAccount,
    ScheduledPost, Post, DMMessage, DMReplyTemplate, AutoReplyRule, WebhookEvent
)


class PerPageAdminMixin:
    def changelist_view(self, request, extra_context=None):
        per_page = request.GET.get('per_page')
        if per_page in ('50', '100'):
            self.list_per_page = int(per_page)
        extra_context = extra_context or {}
        extra_context['per_page'] = per_page or self.list_per_page
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(FacebookAccount)
class FacebookAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'facebook_user_id')
    search_fields = ('name', 'facebook_user_id')


@admin.register(ThreadsApp)
class ThreadsAppAdmin(admin.ModelAdmin):
    list_display = ('name', 'threads_app_id')
    search_fields = ('name', 'threads_app_id')


@admin.register(ThreadsAccount)
class ThreadsAccountAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'threads_user_id', 'username')
    search_fields = ('display_name', 'threads_user_id', 'username')


@admin.register(InstagramAccount)
class InstagramAccountAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'instagram_user_id', 'username')
    search_fields = ('display_name', 'instagram_user_id', 'username')


@admin.register(ScheduledPost)
class ScheduledPostAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ('status', 'platform', 'account', 'scheduled_at', 'title', 'topic')
    search_fields = ('title', 'body')
    list_filter = ('status', 'platform')
    ordering = ('-scheduled_at',)
    change_list_template = 'admin/social/change_list.html'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('approve/<int:pk>/', self.admin_site.admin_view(self.approve_view), name='social_scheduledpost_approve'),
        ]
        return custom + urls

    def approve_view(self, request, pk):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        obj = get_object_or_404(ScheduledPost, pk=pk)
        if obj.status == ScheduledPost.Status.DRAFT:
            obj.status = ScheduledPost.Status.APPROVED
            obj.save()
            messages.success(request, '承認しました。')
        return redirect('admin:social_scheduledpost_change', obj.pk)


@admin.register(Post)
class PostAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ('platform', 'account', 'posted_at', 'content', 'like_count', 'view_count')
    search_fields = ('content',)
    list_filter = ('platform',)
    ordering = ('-posted_at',)
    change_list_template = 'admin/social/post/change_list.html'

    def changelist_view(self, request, extra_context=None):
        from django.urls import reverse
        extra_context = extra_context or {}
        extra_context['import_url'] = reverse('social:post-import')
        extra_context['sync_url'] = reverse('social:post-sync')
        return super().changelist_view(request, extra_context=extra_context)

    class Media:
        css = {'all': ['admin/css/changelist.css']}


@admin.register(DMMessage)
class DMMessageAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ('platform', 'sender_external_user_id', 'text', 'received_at')
    search_fields = ('sender_external_user_id', 'text')
    list_filter = ('platform',)
    ordering = ('-received_at',)
    change_list_template = 'admin/social/change_list.html'


@admin.register(DMReplyTemplate)
class DMReplyTemplateAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(AutoReplyRule)
class AutoReplyRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'platform', 'enabled')
    search_fields = ('name', 'keywords')
    list_filter = ('platform', 'enabled')


@admin.register(WebhookEvent)
class WebhookEventAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ('platform', 'event_type', 'received_at', 'processed')
    list_filter = ('platform', 'processed')
    ordering = ('-received_at',)
    change_list_template = 'admin/social/change_list.html'
