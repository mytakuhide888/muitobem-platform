from django.db import models
from django.conf import settings
from social_core.models import (
    BaseSocialAccount, BasePost, BaseScheduledPost,
    BaseBroadcast, BaseDMThread, BaseDMMessage,
    BaseAutoReplyTemplate, BaseAutoReplyRule, BaseWebhookEvent,
)


class InstagramBusinessAccount(BaseSocialAccount):
    ig_business_id = models.CharField('IGビジネスID', max_length=100)
    fb_page_id = models.CharField('FacebookページID', max_length=100, blank=True, null=True)
    access_token = models.TextField('アクセストークン', blank=True, default='')
    webhook_verify_token = models.CharField('Webhook検証トークン', max_length=100, blank=True, null=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    permissions = models.JSONField(default=dict, blank=True)  # {"granted":[...], "declined":[...]}
    webhook_subscribed = models.BooleanField(default=False)
    webhook_subscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'meta_ig_accounts'
        verbose_name = 'Instagramビジネスアカウント'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.display_name


class IGPost(BasePost):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.CASCADE, related_name='posts')

    class Meta:
        db_table = 'meta_ig_posts'
        verbose_name = 'Instagram投稿'
        verbose_name_plural = verbose_name


class IGScheduledPost(BaseScheduledPost):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.CASCADE, related_name='scheduled_posts')

    class Meta:
        db_table = 'meta_ig_scheduled_posts'
        verbose_name = 'Instagram予約投稿'
        verbose_name_plural = verbose_name


class IGBroadcast(BaseBroadcast):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.CASCADE, related_name='broadcasts', null=True, blank=True)

    class Meta:
        db_table = 'meta_ig_broadcasts'
        verbose_name = 'Instagram時間指定配信'
        verbose_name_plural = verbose_name


class IGDMThread(BaseDMThread):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.CASCADE, related_name='dm_threads')

    class Meta:
        db_table = 'meta_ig_dm_threads'
        verbose_name = 'InstagramDMスレッド'
        verbose_name_plural = verbose_name


class IGDMMessage(BaseDMMessage):
    thread = models.ForeignKey(IGDMThread, on_delete=models.CASCADE, related_name='messages')

    class Meta:
        db_table = 'meta_ig_dm_messages'
        verbose_name = 'InstagramDMメッセージ'
        verbose_name_plural = verbose_name


class IGAutoReplyTemplate(BaseAutoReplyTemplate):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.CASCADE, related_name='auto_reply_templates')

    class Meta:
        db_table = 'meta_ig_auto_reply_templates'
        verbose_name = 'Instagram自動返信テンプレート'
        verbose_name_plural = verbose_name


class IGAutoReplyRule(BaseAutoReplyRule):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.CASCADE, related_name='auto_reply_rules')
    template = models.ForeignKey(IGAutoReplyTemplate, on_delete=models.CASCADE, related_name='rules')

    class Meta:
        db_table = 'meta_ig_auto_reply_rules'
        verbose_name = 'Instagram自動返信ルール'
        verbose_name_plural = verbose_name


class IGWebhookEvent(BaseWebhookEvent):
    account = models.ForeignKey(InstagramBusinessAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_events')

    class Meta:
        db_table = 'meta_ig_webhook_events'
        verbose_name = 'InstagramWebhookイベント'
        verbose_name_plural = verbose_name
