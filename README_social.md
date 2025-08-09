# SNS管理機能 概要

## 予約投稿
- 管理画面から作成し、「承認」するとスケジューラ対象になります。
- スケジューラ実行(スタブ): `python manage.py shell -c "from social_core.services.scheduler import dispatch_scheduled_posts; dispatch_scheduled_posts()"`

## 投稿データ取り込み
- 投稿一覧画面上部の「取り込む」「最新化する」ボタンから実行します。

## Webhook テスト
- `/webhooks/threads/` や `/webhooks/instagram/` に POST すると `WebhookEvent` が作成されます。

## スケジューラ
- 予約投稿や配信のディスパッチはスタブです: `python manage.py shell -c "from social_core.services.scheduler import dispatch_scheduled_posts, dispatch_broadcasts; dispatch_scheduled_posts(); dispatch_broadcasts()"`
