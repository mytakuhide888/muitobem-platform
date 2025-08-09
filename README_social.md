# SNS管理機能 概要

## 予約投稿
- 管理画面から作成し、「承認」するとスケジューラ対象になります。
- スケジューラ実行: `python manage.py shell -c "from social.services.scheduler import run_once; run_once()"`

## 投稿データ取り込み
- 投稿一覧画面上部の「取り込む」「最新化する」ボタンから実行します。

## Webhook テスト
- `/webhooks/threads/` や `/webhooks/instagram/` に POST すると `WebhookEvent` と `DMMessage` が作成されます。
