from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['DB_NAME'] = 'kakeibo.db'

# DB初期化
def init_db(db_path=None):
    db_file = db_path if db_path else app.config['DB_NAME']
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount INTEGER NOT NULL,
            memo TEXT,
            type TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

## アプリ起動時は明示的に初期化すること（テスト時は不要）

# ホーム画面
@app.route('/')
def home():
    conn = sqlite3.connect(app.config['DB_NAME'])
    c = conn.cursor()
    c.execute("SELECT type, SUM(amount) FROM entries GROUP BY type")
    summary = dict(c.fetchall())
    conn.close()
    return render_template('home.html', summary=summary)

# 収支・収入登録
@app.route('/entry', methods=['GET', 'POST'])
def entry():
    if request.method == 'POST':
        date = request.form['date']
        category = request.form['category']
        amount = request.form['amount']
        memo = request.form['memo']
        type_ = request.form['type']
        # バリデーション
        if not date or not category or not amount or not type_:
            flash('必須項目を入力してください')
            return redirect(url_for('entry'))
        if not amount.isdigit():
            flash('金額は数字で入力してください')
            return redirect(url_for('entry'))
        conn = sqlite3.connect(app.config['DB_NAME'])
        c = conn.cursor()
        c.execute('INSERT INTO entries (date, category, amount, memo, type) VALUES (?, ?, ?, ?, ?)',
                  (date, category, int(amount), memo, type_))
        conn.commit()
        conn.close()
        flash('登録しました')
        return redirect(url_for('entries'))
    return render_template('entry.html')

# 一覧表示
@app.route('/entries')
def entries():
    sort = request.args.get('sort', 'date')
    conn = sqlite3.connect(app.config['DB_NAME'])
    c = conn.cursor()
    if sort == 'category':
        c.execute('SELECT * FROM entries ORDER BY category, date DESC')
    else:
        c.execute('SELECT * FROM entries ORDER BY date DESC')
    data = c.fetchall()
    conn.close()
    return render_template('entries.html', entries=data)

# 編集
@app.route('/entry/<int:id>/edit', methods=['GET', 'POST'])
def edit_entry(id):
    conn = sqlite3.connect(app.config['DB_NAME'])
    c = conn.cursor()
    c.execute('SELECT * FROM entries WHERE id=?', (id,))
    entry = c.fetchone()
    if not entry:
        conn.close()
        flash('データが見つかりません')
        return redirect(url_for('entries'))
    if request.method == 'POST':
        date = request.form['date']
        category = request.form['category']
        amount = request.form['amount']
        memo = request.form['memo']
        type_ = request.form['type']
        if not date or not category or not amount or not type_:
            flash('必須項目を入力してください')
            return redirect(url_for('edit_entry', id=id))
        if not amount.isdigit():
            flash('金額は数字で入力してください')
            return redirect(url_for('edit_entry', id=id))
        c.execute('UPDATE entries SET date=?, category=?, amount=?, memo=?, type=? WHERE id=?',
                  (date, category, int(amount), memo, type_, id))
        conn.commit()
        conn.close()
        flash('編集しました')
        return redirect(url_for('entries'))
    conn.close()
    return render_template('edit.html', entry=entry)

# 削除
@app.route('/entry/<int:id>/delete', methods=['POST'])
def delete_entry(id):
    conn = sqlite3.connect(app.config['DB_NAME'])
    c = conn.cursor()
    c.execute('DELETE FROM entries WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('削除しました')
    return redirect(url_for('entries'))

# 集計
@app.route('/summary')
def summary():
    conn = sqlite3.connect(app.config['DB_NAME'])
    c = conn.cursor()
    c.execute('SELECT strftime("%Y-%m", date) as month, type, SUM(amount) FROM entries GROUP BY month, type')
    monthly = c.fetchall()
    c.execute('SELECT category, SUM(amount) FROM entries GROUP BY category')
    category = c.fetchall()
    conn.close()
    return render_template('summary.html', monthly=monthly, category=category)

if __name__ == '__main__':
    app.run(debug=True)
