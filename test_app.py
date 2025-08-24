import os
import tempfile
import pytest
from app import app, init_db
import sqlite3

def client():
    pass  # Placeholder for the first definition of client function

@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config['DB_NAME'] = db_path
    init_db(db_path)
    with app.test_client() as client:
        yield client
    os.close(db_fd)
    os.unlink(db_path)

# DB初期化テスト
def test_init_db(client):
    from app import init_db
    init_db(app.config['DB_NAME'])
    conn = sqlite3.connect(app.config['DB_NAME'])
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
    assert c.fetchone() is not None
    conn.close()

# 収支・収入登録API 正常
def test_entry_post_success(client):
    rv = client.post('/entry', data={
        'date': '2025-08-01',
        'category': '食費',
        'amount': '2000',
        'memo': '昼食',
        'type': '支出'
    }, follow_redirects=True)
    assert '登録しました'.encode() in rv.data

# 収支・収入登録API 必須項目未入力
def test_entry_post_required(client):
    rv = client.post('/entry', data={
        'date': '',
        'category': '',
        'amount': '',
        'memo': '',
        'type': ''
    }, follow_redirects=True)
    assert '必須項目を入力してください'.encode() in rv.data

# 収支・収入登録API 金額に文字入力
def test_entry_post_amount_text(client):
    rv = client.post('/entry', data={
        'date': '2025-08-01',
        'category': '食費',
        'amount': 'abc',
        'memo': '昼食',
        'type': '支出'
    }, follow_redirects=True)
    assert '金額は数字で入力してください'.encode() in rv.data

# 一覧取得API
def test_entries_get(client):
    # 事前登録
    client.post('/entry', data={
        'date': '2025-08-01',
        'category': '食費',
        'amount': '2000',
        'memo': '昼食',
        'type': '支出'
    })
    rv = client.get('/entries')
    assert '食費'.encode() in rv.data
    assert '2000'.encode() in rv.data

# 編集API 正常
def test_edit_entry_success(client):
    # 事前登録
    client.post('/entry', data={
        'date': '2025-08-01',
        'category': '食費',
        'amount': '2000',
        'memo': '昼食',
        'type': '支出'
    })
    # 編集
    conn = sqlite3.connect(app.config['DB_NAME'])
    c = conn.cursor()
    c.execute('SELECT id FROM entries LIMIT 1')
    entry_id = c.fetchone()[0]
    conn.close()
    rv = client.post(f'/entry/{entry_id}/edit', data={
        'date': '2025-08-02',
        'category': '給与',
        'amount': '100000',
        'memo': '8月分',
        'type': '収入'
    }, follow_redirects=True)
    assert '編集しました'.encode() in rv.data

# 編集API 存在しないID
def test_edit_entry_notfound(client):
    rv = client.post('/entry/999/edit', data={
        'date': '2025-08-02',
        'category': '給与',
        'amount': '100000',
        'memo': '8月分',
        'type': '収入'
    }, follow_redirects=True)
    assert 'データが見つかりません'.encode() in rv.data

# 削除API 正常
def test_delete_entry_success(client):
    client.post('/entry', data={
        'date': '2025-08-01',
        'category': '食費',
        'amount': '2000',
        'memo': '昼食',
        'type': '支出'
    })
    conn = sqlite3.connect(app.config['DB_NAME'])
    c = conn.cursor()
    c.execute('SELECT id FROM entries LIMIT 1')
    entry_id = c.fetchone()[0]
    conn.close()
    rv = client.post(f'/entry/{entry_id}/delete', follow_redirects=True)
    assert '削除しました'.encode() in rv.data

# 削除API 存在しないID
def test_delete_entry_notfound(client):
    rv = client.post('/entry/999/delete', follow_redirects=True)
    # 削除はエラー返却しないが一覧にデータがないことを確認
    assert '削除しました'.encode() in rv.data or 'データが見つかりません'.encode() in rv.data

# 集計API
def test_summary_get(client):
    client.post('/entry', data={
        'date': '2025-08-01',
        'category': '食費',
        'amount': '2000',
        'memo': '昼食',
        'type': '支出'
    })
    client.post('/entry', data={
        'date': '2025-08-02',
        'category': '給与',
        'amount': '100000',
        'memo': '8月分',
        'type': '収入'
    })
    rv = client.get('/summary')
    assert '食費'.encode() in rv.data
    assert '給与'.encode() in rv.data
    assert '2000'.encode() in rv.data
    assert '100000'.encode() in rv.data

# 画面表示
@pytest.mark.parametrize('url, text', [
    ('/', 'ホーム'),
    ('/entry', '収支・収入登録'),
    ('/entries', '収支一覧'),
    ('/summary', '集計')
])
def test_page_display(client, url, text):
    rv = client.get(url)
    assert text.encode() in rv.data
