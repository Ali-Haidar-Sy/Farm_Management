from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
import database

app = Flask(__name__)
app.secret_key = 'your-secret-key-keep-it-secret'

def get_db():
    conn = sqlite3.connect('farm.db')
    conn.row_factory = sqlite3.Row
    return conn

# ---------- Decorators ----------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('الرجاء تسجيل الدخول أولاً', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('هذه الصفحة مخصصة للمدير فقط', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ---------- Authentication ----------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج', 'info')
    return redirect(url_for('login'))

# ---------- Dashboard ----------
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    animals_count = conn.execute('SELECT type, COUNT(*) as count FROM animals GROUP BY type').fetchall()
    health_status = conn.execute('SELECT health_status, COUNT(*) as count FROM animals GROUP BY health_status').fetchall()
    today = datetime.now().strftime('%Y-%m-%d')
    today_production = conn.execute('''
        SELECT a.type, SUM(p.quantity) as total, p.unit
        FROM production p
        JOIN animals a ON p.animal_id = a.id
        WHERE p.date = ?
        GROUP BY a.type, p.unit
    ''', (today,)).fetchall()
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    income = conn.execute('SELECT SUM(amount) as total FROM finances WHERE type="income" AND date >= ?', (week_ago,)).fetchone()['total'] or 0
    expense = conn.execute('SELECT SUM(amount) as total FROM finances WHERE type="expense" AND date >= ?', (week_ago,)).fetchone()['total'] or 0
    deficit = income - expense
    conn.close()
    return render_template('dashboard.html',
                           animals_count=animals_count,
                           health_status=health_status,
                           today_production=today_production,
                           income=income,
                           expense=expense,
                           deficit=deficit)

# ---------- Animals ----------
def get_animals_with_last_production(animal_type):
    conn = get_db()
    rows = conn.execute('SELECT * FROM animals WHERE type = ? ORDER BY id', (animal_type,)).fetchall()
    animals = []
    for row in rows:
        animal = dict(row)
        last_prod = conn.execute('''
            SELECT quantity, unit, date FROM production
            WHERE animal_id = ? ORDER BY date DESC LIMIT 1
        ''', (animal['id'],)).fetchone()
        animal['last_production'] = last_prod
        animals.append(animal)
    conn.close()
    return animals

@app.route('/cows')
@login_required
def cows():
    cows = get_animals_with_last_production('cow')
    return render_template('cows.html', cows=cows)

@app.route('/sheep')
@login_required
def sheep():
    sheep = get_animals_with_last_production('sheep')
    return render_template('sheep.html', sheep=sheep)

@app.route('/animal/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_animal():
    if request.method == 'POST':
        type_ = request.form['type']
        barcode = request.form['barcode'] or None
        health_status = request.form['health_status']
        last_check = request.form['last_check']
        notes = request.form.get('notes', '')
        conn = get_db()
        conn.execute('''
            INSERT INTO animals (type, barcode, health_status, last_check, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (type_, barcode, health_status, last_check, notes))
        conn.commit()
        conn.close()
        flash('تم إضافة الحيوان بنجاح', 'success')
        return redirect(url_for(type_ + 's'))  # cows or sheep
    # GET: عرض النموذج مع التاريخ الحالي
    today_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_animal.html', today_date=today_date)

@app.route('/animal/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_animal(id):
    conn = get_db()
    if request.method == 'POST':
        type_ = request.form['type']
        barcode = request.form['barcode']
        health_status = request.form['health_status']
        last_check = request.form['last_check']
        notes = request.form.get('notes', '')
        conn.execute('''
            UPDATE animals SET type=?, barcode=?, health_status=?, last_check=?, notes=?
            WHERE id=?
        ''', (type_, barcode, health_status, last_check, notes, id))
        conn.commit()
        conn.close()
        flash('تم تحديث بيانات الحيوان', 'success')
        return redirect(url_for(type_ + 's'))
    # GET: show form
    animal = conn.execute('SELECT * FROM animals WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not animal:
        flash('الحيوان غير موجود', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('edit_animal.html', animal=animal)

@app.route('/animal/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_animal(id):
    conn = get_db()
    animal = conn.execute('SELECT type FROM animals WHERE id = ?', (id,)).fetchone()
    if animal:
        conn.execute('DELETE FROM production WHERE animal_id = ?', (id,))
        conn.execute('DELETE FROM animal_notes WHERE animal_id = ?', (id,))
        conn.execute('DELETE FROM animals WHERE id = ?', (id,))
        conn.commit()
        flash('تم حذف الحيوان', 'success')
    else:
        flash('الحيوان غير موجود', 'danger')
    conn.close()
    return redirect(request.referrer or url_for('dashboard'))

# ---------- Production ----------
@app.route('/add_production/<int:animal_id>', methods=['GET', 'POST'])
@login_required
def add_production(animal_id):
    if request.method == 'POST':
        quantity = request.form['quantity']
        unit = request.form['unit']
        notes = request.form.get('notes', '')
        date = datetime.now().strftime('%Y-%m-%d')
        conn = get_db()
        conn.execute('''
            INSERT INTO production (animal_id, date, quantity, unit, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (animal_id, date, quantity, unit, notes))
        conn.commit()
        conn.close()
        flash('تم تسجيل الإنتاج بنجاح', 'success')
        # redirect back to the appropriate animal list
        animal_type = request.args.get('type', 'cows')
        return redirect(url_for(animal_type))
    return render_template('add_production.html', animal_id=animal_id)

# ---------- Notes ----------
@app.route('/add_note/<int:animal_id>', methods=['POST'])
@login_required
def add_note(animal_id):
    note = request.form['note']
    if not note:
        flash('الرجاء كتابة الملاحظة', 'warning')
        return redirect(request.referrer or url_for('dashboard'))
    date = datetime.now().strftime('%Y-%m-%d')
    user_id = session['user_id']
    conn = get_db()
    conn.execute('''
        INSERT INTO animal_notes (animal_id, date, note, created_by)
        VALUES (?, ?, ?, ?)
    ''', (animal_id, date, note, user_id))
    conn.commit()
    conn.close()
    flash('تم إضافة الملاحظة', 'success')
    animal_type = request.args.get('type', 'cows')
    return redirect(url_for(animal_type))

# ---------- Barcode Search ----------
@app.route('/search_by_barcode', methods=['POST'])
@login_required
def search_by_barcode():
    barcode = request.form['barcode']
    conn = get_db()
    animal = conn.execute('SELECT * FROM animals WHERE barcode = ?', (barcode,)).fetchone()
    conn.close()
    if animal:
        if animal['type'] == 'cow':
            return redirect(url_for('cows') + f'?highlight={animal["id"]}')
        else:
            return redirect(url_for('sheep') + f'?highlight={animal["id"]}')
    else:
        flash('لا يوجد حيوان بهذا الباركود', 'warning')
        return redirect(request.referrer or url_for('dashboard'))

# ---------- Financial ----------
@app.route('/financial')
@login_required
def financial():
    conn = get_db()
    finances = conn.execute('SELECT * FROM finances ORDER BY date DESC LIMIT 50').fetchall()
    first_day = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    month_income = conn.execute('SELECT SUM(amount) FROM finances WHERE type="income" AND date >= ?', (first_day,)).fetchone()[0] or 0
    month_expense = conn.execute('SELECT SUM(amount) FROM finances WHERE type="expense" AND date >= ?', (first_day,)).fetchone()[0] or 0
    conn.close()
    return render_template('financial.html',
                           finances=finances,
                           month_income=month_income,
                           month_expense=month_expense,
                           month_balance=month_income - month_expense)

@app.route('/finance/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_finance():
    if request.method == 'POST':
        date = request.form['date']
        type_ = request.form['type']
        category = request.form['category']
        amount = request.form['amount']
        description = request.form.get('description', '')
        conn = get_db()
        conn.execute('''
            INSERT INTO finances (date, type, category, amount, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (date, type_, category, amount, description))
        conn.commit()
        conn.close()
        flash('تم إضافة المعاملة المالية', 'success')
        return redirect(url_for('financial'))
    return render_template('add_finance.html')

# ---------- Statistics ----------
@app.route('/stats')
@login_required
def stats():
    conn = get_db()
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    production_week = conn.execute('''
        SELECT p.date, a.type, SUM(p.quantity) as total
        FROM production p
        JOIN animals a ON p.animal_id = a.id
        WHERE p.date >= ?
        GROUP BY p.date, a.type
        ORDER BY p.date
    ''', (week_ago,)).fetchall()
    dates = sorted(set(row['date'] for row in production_week))
    animal_types = sorted(set(row['type'] for row in production_week))
    datasets = []
    for a_type in animal_types:
        data = []
        for d in dates:
            val = next((row['total'] for row in production_week if row['date'] == d and row['type'] == a_type), 0)
            data.append(val)
        datasets.append({
            'label': 'أبقار' if a_type == 'cow' else 'خراف',
            'data': data
        })
    conn.close()
    return render_template('stats.html', dates=dates, datasets=datasets)

if __name__ == '__main__':
    database.init_db()
    app.run(debug=True)