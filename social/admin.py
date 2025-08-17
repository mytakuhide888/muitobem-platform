from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    FacebookAccount, ThreadsApp, ThreadsAccount, InstagramAccount,
    ScheduledPost, Post, DMMessage, DMReplyTemplate, AutoReplyRule, WebhookEvent,
    Job,
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
    actions = ['send_now']

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

    def send_now(self, request, queryset):
        from django.utils import timezone
        for obj in queryset:
            Job.objects.update_or_create(
                job_type=Job.Type.PUBLISH,
                platform=obj.platform,
                account=obj.account,
                defaults={'run_at': timezone.now(), 'status': Job.Status.PENDING, 'args': {'scheduled_post_id': obj.pk}},
            )
    send_now.short_description = '今すぐ送信'


@admin.register(Post)
class PostAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ('platform', 'account', 'posted_at', 'content', 'like_count', 'view_count')
    search_fields = ('content',)
    list_filter = ('platform',)
    ordering = ('-posted_at',)
    change_list_template = 'admin/social/post/change_list.html'
    actions = ['refresh_metrics']

    def changelist_view(self, request, extra_context=None):
        from django.urls import reverse
        extra_context = extra_context or {}
        extra_context['import_url'] = reverse('social:post-import')
        extra_context['sync_url'] = reverse('social:post-sync')
        return super().changelist_view(request, extra_context=extra_context)

    class Media:
        css = {'all': ['admin/css/changelist.css']}

    def refresh_metrics(self, request, queryset):
        from django.utils import timezone
        for obj in queryset:
            Job.objects.create(
                job_type=Job.Type.INSIGHT,
                platform=obj.platform,
                account=obj.account,
                run_at=timezone.now(),
                args={'post_id': obj.external_post_id},
            )
    refresh_metrics.short_description = 'メトリクス再取得'


@admin.register(DMMessage)
class DMMessageAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ('platform', 'user_id', 'text', 'sent_at', 'direction')
    search_fields = ('user_id', 'text')
    list_filter = ('platform', 'direction')
    ordering = ('-sent_at',)
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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'content_type':
            from django.contrib.contenttypes.models import ContentType

            kwargs['queryset'] = ContentType.objects.filter(
                app_label='social',
                model__in=['instagramaccount', 'threadsaccount']
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(WebhookEvent)
class WebhookEventAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ('platform', 'field', 'received_at', 'signature_valid')
    list_filter = ('platform', 'signature_valid')
    ordering = ('-received_at',)
    change_list_template = 'admin/social/change_list.html'
    readonly_fields = ('pretty_payload',)

    def pretty_payload(self, obj):
        import json
        from django.utils.safestring import mark_safe
        return mark_safe('<pre>{}</pre>'.format(json.dumps(obj.payload, indent=2, ensure_ascii=False)))
    pretty_payload.short_description = 'payload'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('<int:pk>/compare/', self.admin_site.admin_view(self.compare_latest), name='social_webhookevent_compare'),
        ]
        return custom + urls

    def compare_latest(self, request, pk):
        from django.shortcuts import get_object_or_404
        from django.http import HttpResponse
        import json, difflib
        obj = get_object_or_404(WebhookEvent, pk=pk)
        other = (
            WebhookEvent.objects.filter(platform=obj.platform, field=obj.field)
            .exclude(pk=obj.pk)
            .order_by('-received_at')
            .first()
        )
        if not other:
            return HttpResponse('比較対象なし')
        a = json.dumps(other.payload, indent=2, ensure_ascii=False).splitlines()
        b = json.dumps(obj.payload, indent=2, ensure_ascii=False).splitlines()
        diff = '\n'.join(difflib.unified_diff(a, b, fromfile='prev', tofile='curr'))
        return HttpResponse(f'<pre>{diff}</pre>')


@admin.register(Job)
class JobAdmin(PerPageAdminMixin, admin.ModelAdmin):
    list_display = ('job_type', 'platform', 'run_at', 'status', 'retries', 'last_error')
    list_filter = ('platform', 'status', 'job_type')
    search_fields = ('job_type', 'platform', 'args')
    ordering = ('-run_at',)
    actions = ['run_now', 'resend', 'reset_failed']

    def run_now(self, request, queryset):
        queryset.update(run_at=timezone.now(), status=Job.Status.PENDING)
    run_now.short_description = '今すぐ実行'

    def resend(self, request, queryset):
        for job in queryset.filter(status__in=[Job.Status.DONE, Job.Status.FAILED]):
            job.pk = None
            job.status = Job.Status.PENDING
            job.run_at = timezone.now()
            job.retries = 0
            job.last_error = ''
            job.save()
    resend.short_description = '再送'

    def reset_failed(self, request, queryset):
        queryset.filter(status=Job.Status.FAILED).update(
            status=Job.Status.PENDING,
            run_at=timezone.now(),
            retries=0,
            last_error='',
        )
    reset_failed.short_description = '失敗をPENDINGに戻す'
