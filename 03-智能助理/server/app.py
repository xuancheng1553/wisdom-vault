#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智慧宝库 - Flask 后端服务"""
import json, sqlite3, os
from flask import Flask, g, request, jsonify, send_from_directory
from flask_cors import CORS

DB = os.path.join(os.path.dirname(__file__), 'knowledge.db')
STATIC = os.path.join(os.path.dirname(__file__), '..')

app = Flask(__name__, static_folder=STATIC, static_url_path='')
CORS(app)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

app.teardown_appcontext(close_db)

# ─── 初始化数据库 ───
def init_db():
    with app.app_context():
        db = get_db()
        db.executescript('''
            CREATE TABLE IF NOT EXISTS dimensions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                icon TEXT DEFAULT '',
                description TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS figures (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                short_name TEXT DEFAULT '',
                title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                color TEXT DEFAULT '#666'
            );
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                figure_id TEXT,
                dimension_id TEXT,
                category TEXT DEFAULT '',
                quote TEXT NOT NULL,
                source TEXT DEFAULT '',
                interpretation TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (figure_id) REFERENCES figures(id),
                FOREIGN KEY (dimension_id) REFERENCES dimensions(id)
            );
        ''')
        db.commit()
init_db()

# ─── API: 维度列表 ───
@app.route('/api/dimensions')
def api_dimensions():
    rows = get_db().execute('SELECT * FROM dimensions ORDER BY sort_order').fetchall()
    return jsonify([dict(r) for r in rows])

# ─── API: 人物/来源列表 ───
@app.route('/api/figures')
def api_figures():
    rows = get_db().execute('SELECT * FROM figures ORDER BY name').fetchall()
    return jsonify([dict(r) for r in rows])

# ─── API: 条目列表 ───
@app.route('/api/entries')
def api_entries():
    dim = request.args.get('dimension')
    fig = request.args.get('figure')
    q = request.args.get('q')
    sql = 'SELECT e.*, f.name as figure_name, d.name as dimension_name FROM entries e LEFT JOIN figures f ON e.figure_id=f.id LEFT JOIN dimensions d ON e.dimension_id=d.id WHERE 1=1'
    params = []
    if dim:
        sql += ' AND e.dimension_id=?'
        params.append(dim)
    if fig:
        sql += ' AND e.figure_id=?'
        params.append(fig)
    if q:
        sql += ' AND (e.quote LIKE ? OR e.interpretation LIKE ? OR e.source LIKE ? OR e.tags LIKE ?)'
        kw = f'%{q}%'
        params.extend([kw, kw, kw, kw])
    sql += ' ORDER BY e.id'
    rows = get_db().execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])

# ─── API: 单条 ───
@app.route('/api/entries/<int:eid>')
def api_entry(eid):
    row = get_db().execute('SELECT e.*, f.name as figure_name, d.name as dimension_name FROM entries e LEFT JOIN figures f ON e.figure_id=f.id LEFT JOIN dimensions d ON e.dimension_id=d.id WHERE e.id=?', (eid,)).fetchone()
    if not row:
        return jsonify({'error': 'not found'}), 404
    return jsonify(dict(row))

# ─── API: 新增 ───
@app.route('/api/entries', methods=['POST'])
def api_create():
    data = request.json
    db = get_db()
    cur = db.execute(
        'INSERT INTO entries (figure_id, dimension_id, category, quote, source, interpretation, tags) VALUES (?,?,?,?,?,?,?)',
        (data.get('figure_id',''), data.get('dimension_id',''), data.get('category',''), data['quote'], data.get('source',''), data.get('interpretation',''), data.get('tags',''))
    )
    db.commit()
    return jsonify({'id': cur.lastrowid, 'ok': True})

# ─── API: 修改 ───
@app.route('/api/entries/<int:eid>', methods=['PUT'])
def api_update(eid):
    data = request.json
    db = get_db()
    db.execute(
        'UPDATE entries SET figure_id=?,dimension_id=?,category=?,quote=?,source=?,interpretation=?,tags=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
        (data.get('figure_id',''), data.get('dimension_id',''), data.get('category',''), data['quote'], data.get('source',''), data.get('interpretation',''), data.get('tags',''), eid)
    )
    db.commit()
    return jsonify({'ok': True})

# ─── API: 删除 ───
@app.route('/api/entries/<int:eid>', methods=['DELETE'])
def api_delete(eid):
    get_db().execute('DELETE FROM entries WHERE id=?', (eid,))
    get_db().commit()
    return jsonify({'ok': True})

# ─── API: 统计数据 ───
@app.route('/api/stats')
def api_stats():
    db = get_db()
    total = db.execute('SELECT COUNT(*) as c FROM entries').fetchone()['c']
    dims = db.execute('SELECT COUNT(*) as c FROM dimensions').fetchone()['c']
    figs = db.execute('SELECT COUNT(*) as c FROM figures').fetchone()['c']
    return jsonify({'total': total, 'dimensions': dims, 'figures': figs})

# ─── 首页 ───
@app.route('/')
def index():
    return send_from_directory(STATIC, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(STATIC, path)

if __name__ == '__main__':
    print(f'智慧宝库启动: http://localhost:5000')
    app.run(host='0.0.0.0', port=5001, debug=False)
