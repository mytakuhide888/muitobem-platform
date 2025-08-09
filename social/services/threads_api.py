"""Threads API クライアントのスタブ"""
from datetime import datetime
from typing import List, Dict


def fetch_posts(access_token: str, user_id: str, since: datetime | None = None) -> List[Dict]:
    """Threads の投稿を取得するスタブ"""
    dummy = {
        'id': 'thr1',
        'content': 'Threadsテスト投稿',
        'like_count': 1,
        'view_count': 10,
        'posted_at': datetime.now().isoformat(),
    }
    return [dummy]


def post_thread(access_token: str, user_id: str, text: str) -> Dict:
    """投稿スタブ"""
    return {'id': 'posted', 'text': text}
