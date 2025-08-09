from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Platform(models.TextChoices):
    THREADS = 'THREADS', 'Threads'
    INSTAGRAM = 'INSTAGRAM', 'Instagram'


class FacebookAccount(models.Model):
    name = models.CharField('名前', max_length=255)
    facebook_user_id = models.CharField('FacebookユーザーID', max_length=100, unique=True)
    app_id = models.CharField('アプリID', max_length=100, null=True, blank=True)
    app_secret = models.TextField('アプリシークレット', blank=True, null=True)
    access_token = models.TextField('アクセストークン', blank=True, null=True)
    access_token_expires_at = models.DateTimeField('アクセストークン有効期限', null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return self.name


class ThreadsApp(models.Model):
    name = models.CharField('名前', max_length=255)
    threads_app_id = models.CharField('ThreadsアプリID', max_length=100)
    threads_app_secret = models.TextField('Threadsアプリシークレット')
    callback_url = models.URLField('コールバックURL')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return self.name


class ThreadsAccount(models.Model):
    display_name = models.CharField('表示名', max_length=255)
    threads_user_id = models.CharField('ThreadsユーザーID', max_length=100, unique=True)
    username = models.CharField('ユーザー名', max_length=255)
    linked_facebook = models.ForeignKey(FacebookAccount, verbose_name='紐付けFacebook', on_delete=models.SET_NULL, null=True, blank=True)
    default_app = models.ForeignKey(ThreadsApp, verbose_name='デフォルトアプリ', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return self.display_name


class InstagramAccount(models.Model):
    display_name = models.CharField('表示名', max_length=255)
    instagram_user_id = models.CharField('InstagramユーザーID', max_length=100, unique=True)
    username = models.CharField('ユーザー名', max_length=255)
    linked_facebook = models.ForeignKey(FacebookAccount, verbose_name='紐付けFacebook', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return self.display_name


class ScheduledPost(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', '下書き'
        APPROVED = 'APPROVED', '承認済み'
        SENT = 'SENT', '送信済み'
        FAILED = 'FAILED', '失敗'

    platform = models.CharField('プラットフォーム', max_length=20, choices=Platform.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    account = GenericForeignKey('content_type', 'object_id')
    title = models.CharField('タイトル', max_length=255)
    topic = models.CharField('トピック', max_length=255)
    body = models.TextField('本文')
    scheduled_at = models.DateTimeField('投稿予定時刻')
    status = models.CharField('ステータス', max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='作成者', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return self.title


class Post(models.Model):
    platform = models.CharField('プラットフォーム', max_length=20, choices=Platform.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    account = GenericForeignKey('content_type', 'object_id')
    external_post_id = models.CharField('外部投稿ID', max_length=100, unique=True)
    posted_at = models.DateTimeField('投稿時間')
    content = models.TextField('内容')
    like_count = models.IntegerField('いいね数', default=0)
    view_count = models.IntegerField('閲覧数', null=True, blank=True)
    raw_json = models.JSONField('取得JSON', default=dict)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    def __str__(self):
        return f"{self.platform}:{self.external_post_id}"


class DMMessage(models.Model):
    platform = models.CharField('プラットフォーム', max_length=20, choices=Platform.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    object_id = models.PositiveIntegerField(null=True)
    account = GenericForeignKey('content_type', 'object_id')
    sender_external_user_id = models.CharField('送信者ID', max_length=100)
    text = models.TextField('本文')
    received_at = models.DateTimeField('受信時間')
    raw_json = models.JSONField('受信JSON', default=dict)

    def __str__(self):
        return f"{self.sender_external_user_id}"


class DMReplyTemplate(models.Model):
    name = models.CharField('名称', max_length=100)
    reply_text = models.TextField('返信本文')

    def __str__(self):
        return self.name


class AutoReplyRule(models.Model):
    name = models.CharField('名称', max_length=100)
    platform = models.CharField('プラットフォーム', max_length=20, choices=Platform.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    object_id = models.PositiveIntegerField(null=True)
    account = GenericForeignKey('content_type', 'object_id')
    keywords = models.TextField('キーワード')
    delay_minutes = models.IntegerField('遅延分', default=0)
    reply_template = models.ForeignKey(DMReplyTemplate, verbose_name='返信テンプレート', on_delete=models.CASCADE)
    enabled = models.BooleanField('有効', default=True)

    def __str__(self):
        return self.name


class WebhookEvent(models.Model):
    platform = models.CharField('プラットフォーム', max_length=20, choices=Platform.choices)
    received_at = models.DateTimeField('受信時間', auto_now_add=True)
    event_type = models.CharField('イベント種類', max_length=100)
    payload = models.JSONField('ペイロード', default=dict)
    processed = models.BooleanField('処理済み', default=False)

    def __str__(self):
        return f"{self.platform}:{self.event_type}"
