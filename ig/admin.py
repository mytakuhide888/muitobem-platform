from django.contrib import admin
from social_core.admin_mixins import TimeStampedAdminMixin
from .models import (
    InstagramBusinessAccount, IGPost, IGScheduledPost,
    IGBroadcast, IGDMThread, IGDMMessage,
    IGAutoReplyTemplate, IGAutoReplyRule, IGWebhookEvent,
)


@admin.register(InstagramBusinessAccount)
class InstagramBusinessAccountAdmin(TimeStampedAdminMixin):
    list_display = ('display_name', 'username', 'external_id', 'is_active')
    search_fields = ('display_name', 'username', 'external_id')


@admin.register(IGPost)
class IGPostAdmin(TimeStampedAdminMixin):
    list_display = ('external_post_id', 'account', 'posted_at', 'like_count')
    search_fields = ('external_post_id', 'caption')
    list_filter = ('posted_at',)


@admin.register(IGScheduledPost)
class IGScheduledPostAdmin(TimeStampedAdminMixin):
    list_display = ('title', 'account', 'scheduled_at', 'status')
    list_filter = ('status',)


@admin.register(IGWebhookEvent)
class IGWebhookEventAdmin(TimeStampedAdminMixin):
    list_display = ('event_type', 'account', 'received_at', 'processed')
    list_filter = ('processed',)
