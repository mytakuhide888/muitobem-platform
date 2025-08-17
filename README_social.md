# SNS管理機能 概要

## 予約投稿
- 管理画面から作成し、「承認」するとスケジューラ対象になります。
- Worker 実行: `python manage.py social_worker --loop`

## 投稿データ取り込み
- 投稿一覧画面上部の「取り込む」「最新化する」ボタンから実行します。

## Webhook テスト
- `/webhook/threads/` や `/webhook/instagram/` に POST すると `WebhookEvent` が作成されます。
- Threads の DM API は未提供で、リプライ/メンションを DM 相当として扱います。

### Auto Reply
`AutoReplyRule` を作成すると受信メッセージに自動返信できます。

- キーワード: カンマ区切りで指定。`use_regex` を有効にすると正規表現として扱います。
- 遅延: `delay_minutes` に返信までの分数を設定できます。
- 有効時間: `active_from`/`active_to` で時間帯を制限できます。

疑似 POST 例:

```
curl -X POST http://localhost:8000/webhook/instagram/ \
  -H 'Content-Type: application/json' \
  -d '{"entry":[{"messaging":[{"sender":{"id":"u1"},"message":{"text":"hello"}}]}]}'
```

ルールに一致すると `Job`(REPLY) が作成され、ワーカーが返信します。

## .env サンプル

```
FACEBOOK_APP_ID=123
FACEBOOK_APP_SECRET=xxx
IG_APP_ID=123
IG_APP_SECRET=xxx
IG_REDIRECT_URI=https://example.com/ig/callback/
VERIFY_TOKEN_IG=test_token_ig
VERIFY_TOKEN_TH=test_token_th
TH_APP_ID=123
TH_APP_SECRET=xxx
DEFAULT_API_VERSION=v23.0
WORKER_INTERVAL_SEC=5
```

## Webhook 登録と検証
- Facebook/Instagram 管理画面で上記の Verify Token を設定し、
  コールバック URL に `/webhook/instagram/` を指定します。
- Threads 用も同様に `/webhook/threads/` と `VERIFY_TOKEN_TH` を利用します。

## Worker 起動
バックグラウンドジョブは以下のコマンドで処理されます。

```
python manage.py social_worker --loop
```

## 疑似 POST 例

```
curl -X POST http://localhost:8000/webhook/instagram/ \
  -H 'Content-Type: application/json' \
  -d '{"entry":[{"changes":[{"field":"messages","value":{"messages":[{"from":{"id":"u1"},"text":"hello"}]}}]}]}'
```

## Admin アクション
- Job: 「今すぐ実行」「再送」「失敗をPENDINGに戻す」
- ScheduledPost: 「今すぐ送信」
- Post: 「メトリクス再取得」

## WebhookEvent ビュー
管理画面の WebhookEvent では JSON が整形表示され、「前回と比較」ボタンで差分を確認できます。
