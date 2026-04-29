import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

def init_db():
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()

    # Users table with hashed passwords
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL   -- 'admin' or 'worker'
        )
    ''')

    # Animals table
    c.execute('''
        CREATE TABLE IF NOT EXISTS animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            barcode TEXT UNIQUE,
            health_status TEXT NOT NULL,
            last_check DATE,
            notes TEXT
        )
    ''')

    # Production table
    c.execute('''
        CREATE TABLE IF NOT EXISTS production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id INTEGER NOT NULL,
            date DATE NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (animal_id) REFERENCES animals (id)
        )
    ''')

    # Animal notes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS animal_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id INTEGER NOT NULL,
            date DATE NOT NULL,
            note TEXT NOT NULL,
            created_by INTEGER,
            FOREIGN KEY (animal_id) REFERENCES animals (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')

    # Finances table
    c.execute('''
        CREATE TABLE IF NOT EXISTS finances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT
        )
    ''')

    # Insert sample users with hashed passwords
    admin_pw = generate_password_hash('admin123')
    worker_pw = generate_password_hash('worker123')
    c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
              ('admin', admin_pw, 'admin'))
    c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
              ('worker', worker_pw, 'worker'))

    # Sample animals
    animals_data = [
        ('cow', 'COW001', 'جيد', (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'), ''),
        ('cow', 'COW002', 'بحاجة علاج', (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'), ''),
        ('sheep', 'SHP001', 'ممتاز', (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), ''),
        ('sheep', 'SHP002', 'جيد', (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'), ''),
        ('sheep', 'SHP003', 'بحاجة مراقبة', (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d'), ''),
    ]
    for a in animals_data:
        c.execute('''
            INSERT OR IGNORE INTO animals (type, barcode, health_status, last_check, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', a)

    # Sample production (last 7 days)
    base_date = datetime.now()
    for i in range(7):
        date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
        # Cow 1
        c.execute('''
            INSERT OR IGNORE INTO production (animal_id, date, quantity, unit, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (1, date, 20.5 + i*0.5, 'لتر', ''))
        # Cow 2
        c.execute('''
            INSERT OR IGNORE INTO production (animal_id, date, quantity, unit, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (2, date, 15.0 + i*0.3, 'لتر', ''))
        # Sheep 1
        c.execute('''
            INSERT OR IGNORE INTO production (animal_id, date, quantity, unit, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (3, date, 2.0 + i*0.1, 'كغم', ''))

    # Sample note
    c.execute('''
        INSERT OR IGNORE INTO animal_notes (animal_id, date, note, created_by)
        VALUES (?, ?, ?, ?)
    ''', (2, datetime.now().strftime('%Y-%m-%d'), 'يلزم متابعة العلاج', 2))

    # Sample finances
    finances_data = [
        (datetime.now().strftime('%Y-%m-%d'), 'income', 'مبيعات حليب', 600.0, ''),
        (datetime.now().strftime('%Y-%m-%d'), 'expense', 'أعلاف', 150.0, ''),
        ((datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), 'income', 'مبيعات بيض', 300.0, ''),
        ((datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), 'expense', 'أدوية', 80.0, ''),
    ]
    for f in finances_data:
        c.execute('''
            INSERT OR IGNORE INTO finances (date, type, category, amount, description)
            VALUES (?, ?, ?, ?, ?)
        ''', f)

    conn.commit()
    conn.close()
    print("Database initialized with expanded sample data.")

if __name__ == '__main__':
    init_db()