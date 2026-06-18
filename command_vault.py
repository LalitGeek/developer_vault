#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3
import json
import csv
import os
import requests
from datetime import datetime

DB_NAME = "vault.db"

CATEGORIES = [
    "Git", "React", "Next.js", "Django", "FastAPI", "Docker", 
    "Kubernetes", "Linux", "Bash", "Python", "AWS", "GCP", 
    "Nginx", "PostgreSQL", "MongoDB", "Cybersecurity", "Networking"
]

AI_PROVIDERS = [
    "Google Gemini", "OpenAI", "Anthropic Claude", "Ollama (Local)", "Meta AI", "Alibaba Qwen",
    "DeepSeek", "Mistral AI", "xAI", "Microsoft AI", "Cohere",
    "AI21 Labs", "Perplexity AI", "Groq", "Together AI", "Hugging Face",
    "OpenRouter", "Fireworks AI", "Cerebras", "NVIDIA AI", "Amazon Bedrock",
    "IBM Watsonx", "SAP Joule", "Oracle AI", "Baidu ERNIE", "Tencent Hunyuan",
    "Moonshot AI", "Zhipu AI", "01.AI", "Stability AI"
]

class CommandVaultDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.create_tables()
        self.seed_categories()
        self.seed_default_commands()

    def create_tables(self):
        cursor = self.conn.cursor()
        # ... categories table creation ...
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                parent_id INTEGER DEFAULT NULL,
                FOREIGN KEY (parent_id) REFERENCES categories (id),
                UNIQUE(name, parent_id)
            )
        ''')
        # ... migration checks ...
        cursor.execute("PRAGMA table_info(categories)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'parent_id' not in cols:
            cursor.execute('ALTER TABLE categories ADD COLUMN parent_id INTEGER DEFAULT NULL')

        # Commands table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                title TEXT,
                command_text TEXT,
                description TEXT,
                usage_example TEXT,
                tags TEXT,
                is_favorite INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories (id)
            )
        ''')
        # Check if usage_example exists (migration)
        cursor.execute("PRAGMA table_info(commands)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'usage_example' not in columns:
            cursor.execute('ALTER TABLE commands ADD COLUMN usage_example TEXT')
        
        # API Keys table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT UNIQUE,
                api_key TEXT,
                is_active INTEGER DEFAULT 0,
                is_custom INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Check for is_custom
        cursor.execute("PRAGMA table_info(api_keys)")
        api_cols = [c[1] for c in cursor.fetchall()]
        if 'is_custom' not in api_cols:
            cursor.execute('ALTER TABLE api_keys ADD COLUMN is_custom INTEGER DEFAULT 0')
            
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ("response_mode", "single"))
        self.conn.commit()

    def get_setting(self, key, default=None):
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        res = cursor.fetchone()
        return res[0] if res else default

    def save_setting(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        self.conn.commit()

    def add_custom_provider(self, name):
        cursor = self.conn.cursor()
        try:
            cursor.execute('INSERT INTO api_keys (provider, is_custom) VALUES (?, 1)', (name,))
            self.conn.commit()
            return True
        except:
            return False

    def delete_custom_provider(self, name):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM api_keys WHERE provider = ? AND is_custom = 1', (name,))
        self.conn.commit()

    def get_all_providers(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT provider FROM api_keys WHERE is_custom = 1')
        customs = [r[0] for r in cursor.fetchall()]
        return AI_PROVIDERS + customs

    def seed_categories(self):
        if self.get_setting("is_seeded") == "1": return
        cursor = self.conn.cursor()
        for cat in CATEGORIES:
            cursor.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (cat,))
        self.conn.commit()
        self.save_setting("is_seeded", "1")

    def get_categories(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, name, parent_id FROM categories ORDER BY name')
        return cursor.fetchall()

    def get_category_hierarchy_ids(self, category_id):
        ids = [category_id]
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM categories WHERE parent_id = ?', (category_id,))
        children = cursor.fetchall()
        for child in children:
            ids.extend(self.get_category_hierarchy_ids(child[0]))
        return ids

    def add_category(self, name, parent_id=None):
        cursor = self.conn.cursor()
        try:
            cursor.execute('INSERT INTO categories (name, parent_id) VALUES (?, ?)', (name, parent_id))
            self.conn.commit()
            return True, "Added"
        except sqlite3.IntegrityError:
            return False, "Category already exists under this parent."

    def update_category_name(self, cat_id, new_name):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE categories SET name = ? WHERE id = ?', (new_name, cat_id))
        self.conn.commit()

    def get_or_create_category(self, name):
        """Supports hierarchical paths like 'Parent > Child'"""
        parts = [p.strip() for p in name.split(">")]
        parent_id = None
        
        cursor = self.conn.cursor()
        for part in parts:
            if parent_id is None:
                cursor.execute('SELECT id FROM categories WHERE name = ? AND parent_id IS NULL', (part,))
            else:
                cursor.execute('SELECT id FROM categories WHERE name = ? AND parent_id = ?', (part, parent_id))
            
            res = cursor.fetchone()
            if res:
                parent_id = res[0]
            else:
                cursor.execute('INSERT INTO categories (name, parent_id) VALUES (?, ?)', (part, parent_id))
                self.conn.commit()
                parent_id = cursor.lastrowid
                
        return parent_id

    def delete_category(self, cat_id):
        cursor = self.conn.cursor()
        # Delete associated commands first
        cursor.execute('DELETE FROM commands WHERE category_id = ?', (cat_id,))
        cursor.execute('DELETE FROM categories WHERE id = ?', (cat_id,))
        self.conn.commit()
        return True, "Category and its commands deleted."

    def delete_all_categories(self):
        cursor = self.conn.cursor()
        # Delete all commands and categories
        cursor.execute('DELETE FROM commands')
        cursor.execute('DELETE FROM categories')
        cursor.execute('DELETE FROM sqlite_sequence WHERE name="categories"')
        cursor.execute('DELETE FROM sqlite_sequence WHERE name="commands"')
        self.conn.commit()
        return True, "All categories and commands deleted permanently."

    def update_category_parent(self, cat_id, parent_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE categories SET parent_id = ? WHERE id = ?', (parent_id, cat_id))
        self.conn.commit()

    def add_command(self, cat_id, title, cmd, desc, usage, tags):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO commands (category_id, title, command_text, description, usage_example, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cat_id, title, cmd, desc, usage, tags))
        self.conn.commit()

    def get_commands(self, category_id=None, search_term=None):
        cursor = self.conn.cursor()
        query = '''
            SELECT c.id, cat.name, c.title, c.command_text, c.description, c.usage_example, c.tags, c.is_favorite 
            FROM commands c
            JOIN categories cat ON c.category_id = cat.id
            WHERE 1=1
        '''
        params = []
        if category_id:
            ids = self.get_category_hierarchy_ids(category_id)
            placeholders = ','.join(['?'] * len(ids))
            query += f' AND c.category_id IN ({placeholders})'
            params.extend(ids)
            
        if search_term:
            query += ' AND (c.title LIKE ? OR c.command_text LIKE ? OR c.tags LIKE ? OR c.usage_example LIKE ?)'
            term = f'%{search_term}%'
            params.extend([term, term, term, term])
        query += ' ORDER BY c.created_at DESC'
        cursor.execute(query, params)
        return cursor.fetchall()

    def delete_command(self, cmd_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM commands WHERE id = ?', (cmd_id,))
        self.conn.commit()

    def seed_default_commands(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM commands')
        if cursor.fetchone()[0] > 0: return

        seed_data = [
            ("Git", "Push to Remote", "git push origin main", "Push local commits to the remote main branch.", "git push origin feature-branch", "git, push"),
            ("Git", "Clone Repository", "git clone <url>", "Create a local copy of a remote repository.", "git clone https://github.com/user/repo.git", "git, clone"),
            ("Docker", "List Containers", "docker ps -a", "Show all containers, including stopped ones.", "docker ps -a --format 'table {{.Names}}\t{{.Status}}'", "docker, container"),
            ("Docker", "Build Image", "docker build -t <name> .", "Build an image from a Dockerfile in current dir.", "docker build -t my-app:v1 .", "docker, build"),
            ("Linux", "Check Disk Usage", "df -h", "Display free disk space in human-readable format.", "df -h /home", "linux, disk"),
            ("Linux", "Find Large Files", "find . -type f -size +100M", "Find files larger than 100MB in current directory.", "find /var/log -size +500M", "linux, find"),
            ("Python", "Create Virtual Env", "python -m venv venv", "Create a new isolated Python environment.", "python3 -m venv .env", "python, venv"),
            ("React", "Create New App", "npx create-react-app my-app", "Initialize a new React project using CRA.", "npx create-react-app dashboard --template typescript", "react, npx"),
            ("Next.js", "Start Dev Server", "npm run dev", "Run the Next.js development server.", "npm run dev -p 3001", "nextjs, dev"),
            ("Django", "Run Migrations", "python manage.py migrate", "Apply database migrations to the schema.", "python manage.py migrate app_name", "django, db"),
            ("FastAPI", "Run with Uvicorn", "uvicorn main:app --reload", "Start a FastAPI development server with hot-reload.", "uvicorn api.index:app --host 0.0.0.0", "fastapi, uvicorn"),
            ("Kubernetes", "Get Pods", "kubectl get pods", "List all pods in the default namespace.", "kubectl get pods -n kube-system", "k8s, pods"),
            ("Bash", "Check Ports", "netstat -tuln", "List all listening ports on the system.", "netstat -tuln | grep :80", "bash, network"),
            ("AWS", "List S3 Buckets", "aws s3 ls", "List all S3 buckets in the current account.", "aws s3 ls s3://my-bucket", "aws, s3"),
            ("Nginx", "Test Config", "nginx -t", "Check the Nginx configuration for syntax errors.", "sudo nginx -t", "nginx, config"),
            ("PostgreSQL", "Backup DB", "pg_dump <db_name> > backup.sql", "Create a SQL dump of a PostgreSQL database.", "pg_dump production_db > june_9.sql", "postgres, sql"),
            ("MongoDB", "Show Databases", "show dbs", "List all databases in the current MongoDB instance.", "use admin; show dbs", "mongodb, nosql"),
            ("Cybersecurity", "Nmap Scan", "nmap -sV <target>", "Scan target for open ports and service versions.", "nmap -sV 192.168.1.1", "security, nmap"),
            ("Networking", "Check IP Address", "ip addr show", "Display all network interfaces and IP addresses.", "ip addr show eth0", "network, ip")
        ]

        # Map category names to IDs
        cursor.execute('SELECT id, name FROM categories')
        cat_map = {name: cid for cid, name in cursor.fetchall()}

        for cat_name, title, cmd, desc, usage, tags in seed_data:
            if cat_name in cat_map:
                self.add_command(cat_map[cat_name], title, cmd, desc, usage, tags)
    
    def clear_api_key(self, provider):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM api_keys WHERE provider = ?', (provider,))
        self.conn.commit()

    def save_api_key(self, provider, key, activate=True):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO api_keys (provider, api_key, is_active, updated_at) 
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(provider) DO UPDATE SET 
                api_key=excluded.api_key, 
                is_active=excluded.is_active,
                updated_at=CURRENT_TIMESTAMP
        ''', (provider, key, 1 if activate else 0))
        self.conn.commit()

    def get_api_key(self, provider):
        cursor = self.conn.cursor()
        cursor.execute('SELECT api_key FROM api_keys WHERE provider = ?', (provider,))
        res = cursor.fetchone()
        return res[0] if res else ""

    def get_all_api_keys(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT provider, api_key, is_active FROM api_keys')
        return {row[0]: {'key': row[1], 'active': row[2]} for row in cursor.fetchall()}

    def get_active_providers(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT provider FROM api_keys WHERE is_active = 1 AND api_key != ""')
        res = cursor.fetchall()
        return [r[0] for r in res]

    def get_stats(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM commands')
        total = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM categories')
        cats = cursor.fetchone()[0]
        return {"total": total, "categories": cats}

class CommandVaultApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Developer Command Vault v2 - LalitGeek")
        self.root.geometry("1100x750")
        self.root.configure(bg="#f5f7f9")
        
        self.db = CommandVaultDB()
        self.chat_history = [] # For human interaction/history
        self.export_cat_var = tk.StringVar(value="All Categories")
        self.setup_styles()
        self.create_layout()
        self.load_categories()
        self.show_dashboard()

    def setup_styles(self):
        self.style = ttk.Style()
        if 'clam' in self.style.theme_names():
            self.style.theme_use('clam')
            
        self.style.configure("TFrame", background="#f5f7f9")
        self.style.configure("Sidebar.TFrame", background="#2c3e50")
        self.style.configure("Header.TLabel", font=('Segoe UI', 20, 'bold'), background="#f5f7f9", foreground="#2c3e50")
        self.style.configure("Card.TFrame", background="#ffffff", relief="flat")
        self.style.configure("Action.TButton", font=('Segoe UI', 10))
        self.style.configure("Delete.TButton", foreground="red")

        # Fonts for AI Output
        import tkinter.font as tkfont
        self.ai_font_normal = tkfont.Font(family="Segoe UI", size=11)
        self.ai_font_bold = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.ai_font_header = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self.ai_font_code = tkfont.Font(family="Consolas", size=10)

    def create_layout(self):
        # Use PanedWindow for resizable sidebar
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#f5f7f9", sashwidth=4, sashrelief="flat")
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Left Sidebar
        self.sidebar = ttk.Frame(self.paned, style="Sidebar.TFrame", width=260)
        self.paned.add(self.sidebar, minsize=200)
        self.sidebar.pack_propagate(False)

        ttk.Label(self.sidebar, text="🛡️ VAULT", font=('Segoe UI', 18, 'bold'), foreground="white", background="#2c3e50").pack(pady=20)
        
        # Navigation Buttons
        self.nav_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        self.nav_frame.pack(fill=tk.X, padx=10)

        nav_btns = [
            ("📊 Dashboard", self.show_dashboard),
            ("🤖 AI Helper", self.show_ai_section),
            ("🔐 API Locker", self.show_api_locker),
            ("⚙️ Data Management", self.show_export_options),
            ("📥 Import JSON", self.import_json)
        ]
        
        for text, cmd in nav_btns:
            btn = tk.Button(self.nav_frame, text=text, command=cmd, font=('Segoe UI', 11), 
                           bg="#34495e", fg="white", relief="flat", activebackground="#1abc9c", 
                           anchor="w", padx=15, pady=8)
            btn.pack(fill=tk.X, pady=2)

        ttk.Label(self.sidebar, text="CATEGORIES", font=('Segoe UI', 10, 'bold'), foreground="#95a5a6", background="#2c3e50").pack(pady=(20, 5), padx=15, anchor="w")
        
        # Category Buttons Frame (Responsive Grid)
        self.cat_btn_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        self.cat_btn_frame.pack(fill=tk.X, padx=15, pady=5)
        self.cat_btn_frame.columnconfigure((0, 1), weight=1)

        self.add_cat_btn = tk.Button(self.cat_btn_frame, text="+ Add", command=self.open_add_category_dialog, 
                                    font=('Segoe UI', 9), bg="#1abc9c", fg="white", relief="flat", pady=5)
        self.add_cat_btn.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=2)
        
        self.del_cat_btn = tk.Button(self.cat_btn_frame, text="- Delete", command=self.delete_selected_categories, 
                                    font=('Segoe UI', 9), bg="#e74c3c", fg="white", relief="flat", pady=5)
        self.del_cat_btn.grid(row=0, column=1, sticky="nsew", padx=(2, 0), pady=2)

        self.clear_cats_btn = tk.Button(self.cat_btn_frame, text="🗑️ Clear All Categories", command=self.clear_all_categories, 
                                       font=('Segoe UI', 9), bg="#c0392b", fg="white", relief="flat", pady=5)
        self.clear_cats_btn.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=2)

        # Categories Treeview (Hierarchy Support)
        cat_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        cat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.cat_tree = ttk.Treeview(cat_frame, show="tree", selectmode="extended")
        self.cat_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Drag and Drop Bindings
        self.cat_tree.bind("<ButtonPress-1>", self.on_tree_drag_start)
        self.cat_tree.bind("<ButtonRelease-1>", self.on_tree_drag_release)
        self.cat_tree.bind("<B1-Motion>", self.on_tree_drag_motion)
        
        tree_scroll = ttk.Scrollbar(cat_frame, orient="vertical", command=self.cat_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.cat_tree.configure(yscrollcommand=tree_scroll.set)
        
        # Enable Mouse Wheel for Treeview
        self._bind_mousewheel(self.cat_tree)
        
        self.cat_tree.bind('<<TreeviewSelect>>', self.on_category_select)
        
        # Main Content Area
        self.main_container = ttk.Frame(self.paned, padding=0)
        self.paned.add(self.main_container, stretch="always")
        
        # Add a scrollable canvas for the main area to handle overflow
        self.main_canvas = tk.Canvas(self.main_container, bg="#f5f7f9", highlightthickness=0)
        self.main_scrollbar = ttk.Scrollbar(self.main_container, orient="vertical", command=self.main_canvas.yview)
        self.main_area = ttk.Frame(self.main_canvas, padding=30)
        
        self.main_area_window = self.main_canvas.create_window((0, 0), window=self.main_area, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        
        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.main_area.bind("<Configure>", self._on_main_area_configure)
        self.main_canvas.bind("<Configure>", self._on_main_canvas_configure)
        self._bind_mousewheel(self.main_canvas)

    def _on_main_area_configure(self, event):
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

    def _on_main_canvas_configure(self, event):
        # Expand main_area to fill canvas width
        self.main_canvas.itemconfig(self.main_area_window, width=event.width)

    def _bind_mousewheel(self, widget, orient="vertical"):
        """Bind mouse wheel events to a widget for cross-platform support."""
        if orient == "vertical":
            # Windows/macOS
            widget.bind("<MouseWheel>", lambda e: widget.yview_scroll(int(-1*(e.delta/120)), "units"))
            # Linux
            widget.bind("<Button-4>", lambda e: widget.yview_scroll(-1, "units"))
            widget.bind("<Button-5>", lambda e: widget.yview_scroll(1, "units"))
        else:
            widget.bind("<MouseWheel>", lambda e: widget.xview_scroll(int(-1*(e.delta/120)), "units"))
            widget.bind("<Button-4>", lambda e: widget.xview_scroll(-1, "units"))
            widget.bind("<Button-5>", lambda e: widget.xview_scroll(1, "units"))

    def clear_main(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()
        # Reset scroll position
        self.main_canvas.yview_moveto(0)


    # --- Drag and Drop ---
    def on_tree_drag_start(self, event):
        item = self.cat_tree.identify_row(event.y)
        if item:
            self.dragged_item = item
            self.root.config(cursor="hand2")

    def on_tree_drag_motion(self, event):
        if not hasattr(self, 'dragged_item'): return
        target = self.cat_tree.identify_row(event.y)
        if target:
            self.cat_tree.selection_set(target)

    def on_tree_drag_release(self, event):
        self.root.config(cursor="")
        if not hasattr(self, 'dragged_item'): return
        
        target = self.cat_tree.identify_row(event.y)
        source_item = self.cat_tree.item(self.dragged_item)
        source_cid = source_item['values'][0]
        source_name = source_item['text']
        
        if target == self.dragged_item:
            del self.dragged_item
            return

        if not target:
            # Move to root
            if messagebox.askyesno("Move Category", f"Move '{source_name}' to root?"):
                self.db.update_category_parent(source_cid, None)
        else:
            target_item = self.cat_tree.item(target)
            target_cid = target_item['values'][0]
            target_name = target_item['text']
            
            # Cycle detection
            if self.is_descendant(source_cid, target_cid):
                messagebox.showerror("Error", "Cannot move a category into its own subcategory.")
            elif messagebox.askyesno("Move Category", f"Move '{source_name}' into '{target_name}'?"):
                self.db.update_category_parent(source_cid, target_cid)
            
        self.load_categories()
        del self.dragged_item

    def is_descendant(self, parent_cid, potential_child_cid):
        # Recursively check if potential_child_cid has parent_cid as an ancestor
        current = potential_child_cid
        while current:
            # Find current in memory categories to avoid excessive DB calls
            cat = next((c for c in self.categories if c[0] == current), None)
            if not cat: break
            parent = cat[2] # parent_id
            if parent == parent_cid: return True
            current = parent
        return False

    def load_categories(self):
        # Clear existing
        for item in self.cat_tree.get_children():
            self.cat_tree.delete(item)
            
        self.categories = self.db.get_categories()
        # {id: tree_id} mapping to handle nested items
        tree_map = {}
        
        # Sort so parents come before children
        cats_to_process = list(self.categories)
        while cats_to_process:
            deferred = []
            for cid, name, pid in cats_to_process:
                if pid is None:
                    tid = self.cat_tree.insert("", "end", text=name, values=(cid,))
                    tree_map[cid] = tid
                elif pid in tree_map:
                    tid = self.cat_tree.insert(tree_map[pid], "end", text=name, values=(cid,))
                    tree_map[cid] = tid
                else:
                    deferred.append((cid, name, pid))
            
            if len(deferred) == len(cats_to_process):
                for cid, name, pid in deferred:
                    tid = self.cat_tree.insert("", "end", text=name, values=(cid,))
                    tree_map[cid] = tid
                break
            cats_to_process = deferred

    def show_dashboard(self):
        self.clear_main()
        stats = self.db.get_stats()
        active_ais = self.db.get_active_providers()
        
        header_box = ttk.Frame(self.main_area)
        header_box.pack(fill=tk.X, pady=(0, 20))
        ttk.Label(header_box, text="Overview", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Button(header_box, text="+ New Command", command=self.open_add_dialog).pack(side=tk.RIGHT)

        # Responsive Grid for Stat Cards
        self.cards_container = ttk.Frame(self.main_area)
        self.cards_container.pack(fill=tk.X)
        
        # Browse Categories Section (New & Responsive)
        self.cat_header = ttk.Label(self.main_area, text="Browse Categories", font=("Segoe UI", 14, "bold"), background="#f5f7f9")
        self.cat_header.pack(anchor="w", pady=(30, 15))
        
        self.cat_grid_container = ttk.Frame(self.main_area)
        self.cat_grid_container.pack(fill=tk.X)

        # Quick Search
        search_frame = tk.Frame(self.main_area, bg="white", padx=15, pady=15, highlightbackground="#dcdde1", highlightthickness=1)
        search_frame.pack(fill=tk.X, pady=40)
        
        tk.Label(search_frame, text="🔍 Quick Search", font=("Segoe UI", 12, "bold"), bg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Segoe UI", 11), bg="#f8f9fa", borderwidth=0)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=20)
        entry.bind("<Return>", lambda e: self.run_search())
        tk.Button(search_frame, text="Search", command=self.run_search, bg="#1abc9c", fg="white", relief="flat", padx=15).pack(side=tk.RIGHT)

        def refresh_grids(event=None):
            if not hasattr(self, 'cards_container') or not self.cards_container.winfo_exists(): return
            
            # --- Refresh Stats Grid ---
            width = self.cards_container.winfo_width()
            if width < 100: return
            
            for widget in self.cards_container.winfo_children(): widget.grid_forget()
            
            s_cols = max(1, width // 320)
            for i in range(s_cols): self.cards_container.columnconfigure(i, weight=1)
            
            stat_items = [
                ("Total Commands", stats['total'], "#3498db"),
                ("Categories", stats['categories'], "#e67e22"),
                ("Active AI", ", ".join(active_ais) if active_ais else "None", "#2ecc71")
            ]
            
            for i, (title, val, color) in enumerate(stat_items):
                self.create_stat_card(self.cards_container, title, val, color, i // s_cols, i % s_cols)

            # --- Refresh Categories Grid ---
            for widget in self.cat_grid_container.winfo_children(): widget.grid_forget()
            
            c_cols = max(1, width // 220)
            for i in range(c_cols): self.cat_grid_container.columnconfigure(i, weight=1)
            
            for i, (cid, name, pid) in enumerate(self.db.get_categories()):
                self.create_category_card(self.cat_grid_container, cid, name, i // c_cols, i % c_cols)

        self.main_area.bind("<Configure>", refresh_grids)

    def create_category_card(self, parent, cid, name, row, col):
        card = tk.Button(parent, text=f"📁 {name}", font=("Segoe UI", 10, "bold"), 
                        bg="white", fg="#2c3e50", relief="flat", padx=15, pady=15,
                        highlightbackground="#dcdde1", highlightthickness=1,
                        command=lambda: self.show_commands(category_id=cid, category_name=name))
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        card.bind("<Enter>", lambda e: card.config(bg="#f8f9fa", fg="#1abc9c"))
        card.bind("<Leave>", lambda e: card.config(bg="white", fg="#2c3e50"))

    def create_stat_card(self, parent, title, val, color, row, col):
        frame = tk.Frame(parent, bg="white", padx=20, pady=20, highlightbackground="#dcdde1", highlightthickness=1)
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        tk.Label(frame, text=title, font=("Segoe UI", 10, "bold"), bg="white", fg="#7f8c8d").pack(anchor="w")
        
        is_list = "," in str(val) or len(str(val)) > 15
        val_font = ("Segoe UI", 12, "bold") if is_list else ("Segoe UI", 24, "bold")
        
        lbl = tk.Label(frame, text=str(val), font=val_font, bg="white", fg=color, 
                       wraplength=250, justify=tk.LEFT)
        lbl.pack(anchor="w", pady=(5, 0), fill=tk.X)

    def on_category_select(self, event):
        selection = self.cat_tree.selection()
        if not selection: return
        item_id = selection[0]
        item = self.cat_tree.item(item_id)
        cid = item['values'][0]
        name = item['text']
        
        # Expand the category on click
        self.cat_tree.item(item_id, open=True)
        
        self.show_commands(category_id=cid, category_name=name)

    def run_search(self):
        term = self.search_var.get().strip()
        if term:
            self.show_commands(search_term=term)

    def show_commands(self, category_id=None, category_name=None, search_term=None):
        self.clear_main()
        
        header = ttk.Frame(self.main_area)
        header.pack(fill=tk.X, pady=(0, 20))
        
        title = f"📁 {category_name}" if category_name else f"🔍 Results for '{search_term}'"
        ttk.Label(header, text=title, style="Header.TLabel").pack(side=tk.LEFT)
        
        # Action Buttons in Command View
        action_frame = ttk.Frame(header)
        action_frame.pack(side=tk.RIGHT)
        
        if category_id:
            tk.Button(action_frame, text="✏️ Rename", command=lambda: self.rename_category(category_id, category_name), bg="#3498db", fg="white", relief="flat", padx=10, pady=5).pack(side=tk.LEFT, padx=2)
            tk.Button(action_frame, text="📄 PDF", command=lambda: self.export_pdf(category_id), bg="#e74c3c", fg="white", relief="flat", padx=10, pady=5).pack(side=tk.LEFT, padx=2)
            tk.Button(action_frame, text="📋 JSON", command=lambda: self.export_json(category_id), bg="#9b59b6", fg="white", relief="flat", padx=10, pady=5).pack(side=tk.LEFT, padx=2)
            tk.Button(action_frame, text="🗑️ Delete Category", bg="#95a5a6", fg="white", relief="flat", 
                      padx=10, pady=5, font=("Segoe UI", 9),
                      command=lambda: self.confirm_delete_category(category_id)).pack(side=tk.LEFT, padx=(10, 0))

        commands = self.db.get_commands(category_id, search_term)
        
        # Command List (Now using the main_area scrollable canvas)
        for cmd in commands:
            self.create_command_item(self.main_area, cmd)

    def rename_category(self, cid, old_name):
        new_name = simpledialog.askstring("Rename Category", f"Enter new name for '{old_name}':", initialvalue=old_name)
        if new_name and new_name.strip() != old_name:
            self.db.update_category_name(cid, new_name.strip())
            self.load_categories()
            self.show_commands(category_id=cid, category_name=new_name.strip())
            messagebox.showinfo("Success", "Category renamed.")

    def create_command_item(self, parent, cmd):
        # cmd: id, cat_name, title, cmd_text, desc, usage, tags, is_fav
        cid, cat, title, text, desc, usage, tags, fav = cmd
        
        card = tk.Frame(parent, bg="white", padx=20, pady=20, highlightbackground="#dcdde1", highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 15), padx=5)
        
        tk.Label(card, text=title, font=("Segoe UI", 13, "bold"), bg="white", fg="#2c3e50").pack(anchor="w")
        
        code_box = tk.Frame(card, bg="#282c34", padx=15, pady=10)
        code_box.pack(fill=tk.X, pady=10)
        
        code_lbl = tk.Label(code_box, text=text, font=("Consolas", 11), fg="#abb2bf", bg="#282c34", justify=tk.LEFT, anchor="w")
        code_lbl.pack(fill=tk.X)
        
        if desc:
            tk.Label(card, text=desc, font=("Segoe UI", 10), bg="white", fg="#57606f", wraplength=700, justify=tk.LEFT).pack(anchor="w")
            
        if usage:
            tk.Label(card, text=f"Example: {usage}", font=("Segoe UI", 9, "italic"), bg="white", fg="#1abc9c", wraplength=700, justify=tk.LEFT).pack(anchor="w", pady=(5,0))
            
        btn_row = ttk.Frame(card)
        btn_row.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(btn_row, text="📋 Copy", command=lambda: self.copy(text), bg="#f1f2f6", relief="flat", padx=10).pack(side=tk.LEFT)
        tk.Button(btn_row, text="🤖 Explain", command=lambda: self.ai_explain(text), bg="#f1f2f6", relief="flat", padx=10).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_row, text="🗑️", command=lambda: self.delete_cmd(cid), bg="#ffeaa7", relief="flat", padx=10).pack(side=tk.RIGHT)

    def copy(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Success", "Copied to clipboard!")

    def delete_cmd(self, cid):
        if messagebox.askyesno("Confirm", "Delete this command?"):
            self.db.delete_command(cid)
            self.show_dashboard()

    def confirm_delete_category(self, cid):
        if messagebox.askyesno("Confirm", "Delete this category and ALL its commands?"):
            ok, msg = self.db.delete_category(cid)
            if not ok:
                messagebox.showerror("Error", msg)
            else:
                self.load_categories()
                self.show_dashboard()

    # --- AI Section ---
    def show_ai_section(self):
        self.clear_main()
        active_ais = self.db.get_active_providers()
        
        header = ttk.Frame(self.main_area)
        header.pack(fill=tk.X, pady=(0, 20))
        
        left_info = ttk.Frame(header)
        left_info.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(left_info, text="🤖 Interactive AI Chat", style="Header.TLabel").pack(side=tk.LEFT)
        
        # Responsive Active AI Badge
        ai_frame = tk.Frame(left_info, bg="#eafaf1", padx=10, pady=5)
        ai_frame.pack(side=tk.LEFT, padx=15)
        
        ai_text = "Active: " + (", ".join(active_ais) if active_ais else "NONE")
        tk.Label(ai_frame, text=ai_text, font=("Segoe UI", 9, "bold"), 
                 fg="#27ae60", bg="#eafaf1", wraplength=400, justify=tk.LEFT).pack()
        
        tk.Button(header, text="🧹 Clear Chat", command=self.clear_chat, bg="#7f8c8d", fg="white", relief="flat", padx=10).pack(side=tk.RIGHT)
        
        # Chat History Area
        self.ai_output = tk.Text(self.main_area, height=18, font=("Segoe UI", 11), bg="white", padx=15, pady=15)
        self.ai_output.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Enable Mouse Wheel for AI Output
        self._bind_mousewheel(self.ai_output)
        
        # Prevent direct editing but allow selection/copy
        def prevent_editing(event):
            # Allow Ctrl+C
            if (event.state & 4) and event.keysym.lower() == 'c':
                return
            # Allow navigation/selection keys
            if event.keysym in ['Left', 'Right', 'Up', 'Down', 'Shift_L', 'Shift_R', 'Home', 'End']:
                return
            return "break"
        
        self.ai_output.bind("<Key>", prevent_editing)
        
        # Context menu for copying
        self.chat_menu = tk.Menu(self.root, tearoff=0)
        self.chat_menu.add_command(label="Copy", command=lambda: self.ai_output.event_generate("<<Copy>>"))
        self.ai_output.bind("<Button-3>", lambda e: self.chat_menu.post(e.x_root, e.y_root))

        # Input Area
        input_frame = tk.Frame(self.main_area, bg="white", padx=20, pady=20, highlightbackground="#dcdde1", highlightthickness=1)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.ai_input = tk.Text(input_frame, height=3, font=("Segoe UI", 11), bg="#f8f9fa", borderwidth=0)
        self.ai_input.pack(fill=tk.X, pady=(0, 10))
        self.ai_input.bind("<Control-Return>", lambda e: self.call_ai_provider())
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="Send Message", command=self.call_ai_provider, bg="#1abc9c", fg="white", relief="flat", pady=8, padx=20).pack(side=tk.RIGHT)
        
        # Progress and Status
        self.ai_status_frame = tk.Frame(input_frame, bg="white")
        self.ai_status_frame.pack(side=tk.LEFT, fill=tk.X)
        
        self.ai_status_label = tk.Label(self.ai_status_frame, text="Ctrl+Enter to send", font=("Segoe UI", 9), bg="white", fg="#7f8c8d")
        self.ai_status_label.pack(side=tk.LEFT)
        
        self.ai_progress = ttk.Progressbar(self.ai_status_frame, mode='indeterminate', length=150)
        
        self.ai_retry_btn = tk.Button(self.ai_status_frame, text="🔄 Retry", command=self.call_ai_provider, bg="#3498db", fg="white", relief="flat", font=("Segoe UI", 8))
        self.ai_auto_retry_btn = tk.Button(self.ai_status_frame, text="⏱️ Auto", command=lambda: self.start_auto_retry(int(self.retry_time_var.get())), bg="#e67e22", fg="white", relief="flat", font=("Segoe UI", 8))
        
        tk.Label(self.ai_status_frame, text="Interval (s):", font=("Segoe UI", 8), bg="white", fg="#7f8c8d").pack(side=tk.LEFT, padx=(10, 0))
        self.retry_time_var = tk.StringVar(value="35")
        self.retry_time_spin = ttk.Spinbox(self.ai_status_frame, from_=5, to=300, textvariable=self.retry_time_var, width=4)
        self.retry_time_spin.pack(side=tk.LEFT, padx=5)
        
        self.auto_retry_timer_id = None
        
        # Render existing history if any
        self.render_chat_history()

    def clear_chat(self):
        self.chat_history = []
        self.render_chat_history()

    def render_chat_history(self):
        self.ai_output.delete("1.0", tk.END)
        for msg in self.chat_history:
            role = "👤 You" if msg['role'] == 'user' else f"🤖 {msg.get('provider', 'AI')}"
            content = msg['parts'][0]['text']
            self.append_to_chat(role, content)

    def append_to_chat(self, role, content):
        is_user = "You" in role
        
        # Header for the message
        tag = "msg_header_user" if is_user else "msg_header_ai"
        self.ai_output.insert(tk.END, f"\n {role} \n", tag)
        
        self.render_markdown_in_chat(content)
        
        # Separator
        self.ai_output.insert(tk.END, "\n" + "─"*60 + "\n", "separator")
        self.ai_output.see(tk.END)

    def render_markdown_in_chat(self, text):
        import re
        # Configure advanced tags
        self.ai_output.tag_configure("msg_header_user", font=("Segoe UI", 11, "bold"), foreground="#1a73e8", spacing1=15)
        self.ai_output.tag_configure("msg_header_ai", font=("Segoe UI", 11, "bold"), foreground="#202124", spacing1=15)
        self.ai_output.tag_configure("header", font=self.ai_font_header, foreground="#1a73e8", spacing1=15, spacing3=5)
        self.ai_output.tag_configure("bold", font=self.ai_font_bold, foreground="#202124")
        self.ai_output.tag_configure("codeblock", font=self.ai_font_code, background="#202124", foreground="#f8f8f2", lmargin1=30, lmargin2=30, spacing1=10, spacing3=10)
        self.ai_output.tag_configure("inline_code", font=self.ai_font_code, background="#f1f3f4", foreground="#d93025")
        self.ai_output.tag_configure("normal", font=self.ai_font_normal, foreground="#3c4043", spacing1=4)
        self.ai_output.tag_configure("bullet", font=self.ai_font_normal, lmargin1=25, lmargin2=45)
        self.ai_output.tag_configure("separator", foreground="#dcdde1", font=("Segoe UI", 8))

        lines = text.split('\n')
        in_code_block = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if in_code_block:
                self.ai_output.insert(tk.END, line + '\n', "codeblock")
                continue

            if not line.strip():
                self.ai_output.insert(tk.END, '\n', "normal")
                continue

            # Headers
            if line.strip().startswith('###') or line.strip().startswith('##'):
                self.ai_output.insert(tk.END, line.lstrip('#').strip() + '\n', "header")
                continue
            
            # Bullets
            if line.strip().startswith('* ') or line.strip().startswith('- ') or (line.strip() and line.strip()[0].isdigit() and line.strip()[1:3] == '. '):
                self.ai_output.insert(tk.END, "  • ", "bold")
                content = line.strip().split(' ', 1)[1] if ' ' in line.strip() else ""
                self.render_line_with_tags(content, "bullet")
                self.ai_output.insert(tk.END, '\n')
                continue

            self.render_line_with_tags(line, "normal")
            self.ai_output.insert(tk.END, '\n')

    def render_line_with_tags(self, line, base_tag):
        import re
        # Process bold **text** and `code` in the line
        parts = re.split(r'(\*\*.*?\*\*|`.*?`)', line)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                self.ai_output.insert(tk.END, part[2:-2], "bold")
            elif part.startswith('`') and part.endswith('`'):
                self.ai_output.insert(tk.END, part[1:-1], "inline_code")
            else:
                self.ai_output.insert(tk.END, part, base_tag)

    def ai_explain(self, command):
        self.show_ai_section()
        self.ai_input.insert("1.0", f"Explain this command: {command}")
        self.call_ai_provider()

    def call_ai_provider(self):
        active_providers = self.db.get_active_providers()
        
        if not active_providers:
            messagebox.showwarning("No Active APIs", "Please enable at least one API in the API Locker and provide a key.")
            self.show_api_locker()
            return
            
        prompt = self.ai_input.get("1.0", tk.END).strip()
        if not prompt: return
        
        # Stop any existing auto-retry timers
        if self.auto_retry_timer_id:
            self.root.after_cancel(self.auto_retry_timer_id)
            self.auto_retry_timer_id = None

        # Reset UI
        self.ai_retry_btn.pack_forget()
        self.ai_auto_retry_btn.pack_forget()
        self.ai_progress.pack(side=tk.RIGHT)
        self.ai_progress.start(15)
        
        # Add User Message to UI immediately
        self.append_to_chat("👤 You", prompt)
        self.ai_input.delete("1.0", tk.END)
        
        # Update History for API
        self.chat_history.append({"role": "user", "parts": [{"text": prompt}]})
        
        mode = self.db.get_setting("response_mode", "single")
        
        if mode == "multiple":
            self.try_all_providers(active_providers, prompt)
        else:
            self.try_next_provider(active_providers, 0, prompt)

    def try_all_providers(self, providers, prompt):
        import threading
        self.ai_status_label.config(text=f"🔄 Consulting {len(providers)} APIs...")

        finished_count = 0
        def on_complete_parallel(success, provider, err_msg=None):
            nonlocal finished_count
            finished_count += 1
            if not success and err_msg:
                self.root.after(0, lambda: self.append_to_chat(f"❌ {provider} Error", f"⚠️ {err_msg}"))

            if finished_count >= len(providers):
                self.root.after(0, lambda: self.finish_ai_call("✅ Done"))

        for provider in providers:
            p_key = self.db.get_api_key(provider)
            if provider == "Google Gemini":
                threading.Thread(target=lambda p=provider, k=p_key: self.execute_gemini_request(k, lambda s, e=None: on_complete_parallel(s, p, e)), daemon=True).start()
            elif provider == "Ollama (Local)":
                threading.Thread(target=lambda p=provider, k=p_key: self.execute_ollama_request(k, lambda s, e=None: on_complete_parallel(s, p, e)), daemon=True).start()
            else:
                threading.Thread(target=lambda p=provider, k=p_key: self.execute_openai_compatible_request(p, k, prompt, lambda s, e=None: on_complete_parallel(s, p, e)), daemon=True).start()

    def try_next_provider(self, providers, index, prompt, errors=None):
        if errors is None: errors = []

        if index >= len(providers):
            self.finish_ai_call("❌ All Failed")
            self.ai_status_label.config(text="❌ All available providers failed")

            # Show summary in chat
            report = "**The following errors occurred:**\n\n"
            for p, err in errors:
                report += f"* **{p}**: {err}\n"
            self.append_to_chat("🤖 System Error", report)

            self.ai_retry_btn.pack(side=tk.RIGHT, padx=5)
            return

        provider = providers[index]
        api_key = self.db.get_api_key(provider)

        self.ai_status_label.config(text=f"🔄 Trying {provider}...")
        self.ai_progress.start(15) 
        self.root.update_idletasks()

        def on_complete(success, err_msg=None):
            if success:
                self.finish_ai_call("✅ Success")
            else:
                msg = err_msg if err_msg else "Unknown failure"
                errors.append((provider, msg))
                self.root.after(0, lambda: self.ai_status_label.config(text=f"⚠️ {provider} failed"))
                self.root.after(400, lambda: self.try_next_provider(providers, index + 1, prompt, errors))

        import threading
        if provider == "Google Gemini":
            threading.Thread(target=lambda: self.execute_gemini_request(api_key, on_complete), daemon=True).start()
        elif provider == "Ollama (Local)":
            threading.Thread(target=lambda: self.execute_ollama_request(api_key, on_complete), daemon=True).start()
        else:
            threading.Thread(target=lambda: self.execute_openai_compatible_request(provider, api_key, prompt, on_complete), daemon=True).start()
    def execute_ollama_request(self, api_key, callback):
        base_url = api_key if api_key else "http://localhost:11434"
        try:
            tags_resp = requests.get(f"{base_url}/api/tags", timeout=3)
            if tags_resp.status_code == 200:
                available = [m['name'] for m in tags_resp.json().get('models', [])]
                if available:
                    model = available[0]
                else:
                    callback(False, "No local models found")
                    return
            else:
                callback(False, f"Ollama error {tags_resp.status_code}")
                return
        except Exception as e:
            callback(False, "Ollama not reachable")
            return

        self.root.after(0, lambda: self.ai_status_label.config(text=f"🔄 Ollama thinking ({model})..."))
        messages = [{"role": "user" if m["role"] == "user" else "assistant", "content": m["parts"][0]["text"]} for m in self.chat_history]

        try:
            payload = {"model": model, "messages": messages, "stream": False, "options": {"num_predict": 400}}
            response = requests.post(f"{base_url}/api/chat", json=payload, timeout=60)
            if response.status_code == 200:
                text = response.json()['message']['content']
                self.chat_history.append({"role": "model", "provider": f"Ollama ({model})", "parts": [{"text": text}]})
                self.root.after(0, lambda: self.append_to_chat(f"🤖 Ollama ({model})", text))
                callback(True)
            else:
                callback(False, f"Ollama API error {response.status_code}")
        except Exception as e:
            callback(False, str(e))

    def execute_gemini_request(self, api_key, callback):
        # Attempt combinations of API version and model names
        # v1 is the production stable endpoint, v1beta has experimental/latest models
        attempts = [
            ("v1", "gemini-1.5-flash"),
            ("v1", "gemini-1.5-pro"),
            ("v1beta", "gemini-1.5-flash"),
            ("v1beta", "gemini-1.5-pro"),
            ("v1beta", "gemini-2.0-flash-exp"),
            ("v1beta", "gemini-pro"),
        ]
        
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
        # Deep copy and clean history for API compatibility
        clean_history = []
        for m in self.chat_history:
            if "role" in m and "parts" in m:
                clean_history.append({"role": m["role"], "parts": m["parts"]})
        
        last_err = "Initialization failure"
        
        for version, model in attempts:
            self.root.after(0, lambda v=version, m=model: self.ai_status_label.config(text=f"🔄 Gemini: trying {m} ({v})..."))
            try:
                url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent"
                response = requests.post(url, headers=headers, json={"contents": clean_history}, timeout=30)
                data = response.json()
                
                if response.status_code == 200:
                    if "candidates" in data and data["candidates"]:
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        self.chat_history.append({"role": "model", "provider": "Google Gemini", "parts": [{"text": text}]})
                        self.root.after(0, lambda: self.append_to_chat("🤖 Google Gemini", text))
                        callback(True)
                        return
                    else:
                        last_err = f"{model} ({version}): Empty response (Safety blocked)"
                else:
                    msg = data.get("error", {}).get("message", f"Status {response.status_code}")
                    last_err = f"{model} ({version}): {msg}"
                    
                    # If it's a clear Auth error, don't keep trying other combinations
                    if response.status_code in [401, 403]:
                        callback(False, f"Invalid API Key: {msg}")
                        return
                    
                    # Otherwise, continue to next combination (e.g., if 404 Model Not Found)
                    continue
            except Exception as e:
                last_err = f"{model} ({version}): {str(e)}"
        
        # If all combinations fail
        callback(False, last_err)

    def execute_openai_compatible_request(self, provider, api_key, prompt, callback):
        endpoints = {
            "OpenAI": ("https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
            "DeepSeek": ("https://api.deepseek.com/chat/completions", "deepseek-chat"),
            "Groq": ("https://api.groq.com/openai/v1/chat/completions", "llama3-8b-8192"),
            "Mistral AI": ("https://api.mistral.ai/v1/chat/completions", "mistral-large-latest"),
            "Together AI": ("https://api.together.xyz/v1/chat/completions", "meta-llama/Llama-3-70b-chat-hf"),
            "OpenRouter": ("https://openrouter.ai/api/v1/chat/completions", "google/gemini-pro"),
        }
        if provider not in endpoints:
            callback(False, "Endpoint not configured")
            return

        url, model = endpoints[provider]
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        messages = [{"role": "user" if m["role"] == "user" else "assistant", "content": m["parts"][0]["text"]} for m in self.chat_history]

        try:
            response = requests.post(url, headers=headers, json={"model": model, "messages": messages}, timeout=30)
            if response.status_code == 200:
                text = response.json()["choices"][0]["message"]["content"]
                self.chat_history.append({"role": "model", "provider": provider, "parts": [{"text": text}]})
                self.root.after(0, lambda: self.append_to_chat(f"🤖 {provider}", text))
                callback(True)
            else:
                data = response.json()
                err = data.get("error", {}).get("message", f"API Error {response.status_code}")
                callback(False, err)
        except Exception as e:
            callback(False, str(e))


    def start_auto_retry(self, seconds):
        if seconds > 0:
            self.ai_auto_retry_btn.config(text=f"⏱️ {seconds}s", state=tk.DISABLED)
            self.auto_retry_timer_id = self.root.after(1000, lambda: self.start_auto_retry(seconds - 1))
        else:
            self.ai_auto_retry_btn.config(text="⏱️ Auto", state=tk.NORMAL)
            self.call_ai_provider()

    def finish_ai_call(self, status):
        self.ai_progress.stop()
        self.ai_progress.pack_forget()
        self.ai_status_label.config(text=status)

    def update_ai_output(self, text):
        import re
        self.ai_output.config(state=tk.NORMAL)
        self.ai_output.delete("1.0", tk.END)
        
        # Configure Tags
        self.ai_output.tag_configure("header", font=self.ai_font_header, foreground="#2c3e50", spacing1=10, spacing3=5)
        self.ai_output.tag_configure("bold", font=self.ai_font_bold)
        self.ai_output.tag_configure("codeblock", font=self.ai_font_code, background="#282c34", foreground="#abb2bf", lmargin1=20, lmargin2=20, spacing1=5, spacing3=5)
        self.ai_output.tag_configure("inline_code", font=self.ai_font_code, background="#f1f2f6", foreground="#e74c3c")
        self.ai_output.tag_configure("normal", font=self.ai_font_normal, spacing1=2)

        # Basic Markdown Parsing
        lines = text.split('\n')
        in_code_block = False
        
        for line in lines:
            # Code Block Start/End
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if in_code_block:
                self.ai_output.insert(tk.END, line + '\n', "codeblock")
                continue

            # Headers
            if line.strip().startswith('###'):
                self.ai_output.insert(tk.END, line.replace('###', '').strip() + '\n', "header")
                continue
            if line.strip().startswith('##'):
                self.ai_output.insert(tk.END, line.replace('##', '').strip() + '\n', "header")
                continue

            # Bold and Inline Code
            # We process bold **text** and `code` in the line
            parts = re.split(r'(\*\*.*?\*\*|`.*?`)', line)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    self.ai_output.insert(tk.END, part[2:-2], "bold")
                elif part.startswith('`') and part.endswith('`'):
                    self.ai_output.insert(tk.END, part[1:-1], "inline_code")
                else:
                    self.ai_output.insert(tk.END, part, "normal")
            self.ai_output.insert(tk.END, '\n', "normal")

    # --- API Locker ---
    def show_api_locker(self):
        self.clear_main()
        header = ttk.Frame(self.main_area)
        header.pack(fill=tk.X, pady=(0, 20))
        ttk.Label(header, text="🔐 API Locker", style="Header.TLabel").pack(side=tk.LEFT)
        
        # Global Settings Card
        settings_card = tk.Frame(self.main_area, bg="white", padx=20, pady=15, highlightbackground="#dcdde1", highlightthickness=1)
        settings_card.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(settings_card, text="Response Mode:", font=("Segoe UI", 10, "bold"), bg="white").pack(side=tk.LEFT)
        self.resp_mode_var = tk.StringVar(value=self.db.get_setting("response_mode", "single"))
        
        def on_mode_change(*args):
            self.db.save_setting("response_mode", self.resp_mode_var.get())
            
        tk.Radiobutton(settings_card, text="Single (Fallback)", variable=self.resp_mode_var, value="single", bg="white", command=on_mode_change).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(settings_card, text="Multiple (Parallel)", variable=self.resp_mode_var, value="multiple", bg="white", command=on_mode_change).pack(side=tk.LEFT, padx=10)

        # Provider Selection Card
        card = tk.Frame(self.main_area, bg="white", padx=30, pady=30, highlightbackground="#dcdde1", highlightthickness=1)
        card.pack(fill=tk.X, pady=10)
        
        sel_row = tk.Frame(card, bg="white")
        sel_row.pack(fill=tk.X)
        tk.Label(sel_row, text="Select AI Provider:", font=("Segoe UI", 11, "bold"), bg="white").pack(side=tk.LEFT)
        tk.Button(sel_row, text="+ Add Custom", command=self.open_add_custom_provider_dialog, bg="#3498db", fg="white", relief="flat", font=("Segoe UI", 8)).pack(side=tk.RIGHT)
        
        self.locker_provider_var = tk.StringVar()
        self.provider_combo = ttk.Combobox(card, textvariable=self.locker_provider_var, values=self.db.get_all_providers(), state="readonly", font=("Segoe UI", 10))
        self.provider_combo.pack(fill=tk.X, pady=(10, 20))
        
        # Detail Area (Dynamic)
        self.locker_detail_frame = tk.Frame(self.main_area, bg="#f5f7f9")
        self.locker_detail_frame.pack(fill=tk.BOTH, expand=True)
        
        self.locker_provider_var.trace_add("write", lambda *a: self.refresh_locker_detail())
        
        # Select first provider by default
        all_p = self.db.get_all_providers()
        if all_p:
            self.provider_combo.set(all_p[0])

    def open_add_custom_provider_dialog(self):
        name = simpledialog.askstring("Add Provider", "Enter name for custom AI provider (must be OpenAI compatible):")
        if name:
            if self.db.add_custom_provider(name):
                self.provider_combo['values'] = self.db.get_all_providers()
                self.provider_combo.set(name)
                messagebox.showinfo("Success", f"Provider {name} added!")
            else:
                messagebox.showerror("Error", "Provider already exists.")

    def refresh_locker_detail(self):
        for widget in self.locker_detail_frame.winfo_children():
            widget.destroy()
            
        provider = self.locker_provider_var.get()
        if not provider: return
        
        stored_keys = self.db.get_all_api_keys()
        p_data = stored_keys.get(provider, {'key': '', 'active': 0})
        
        # Check if custom
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT is_custom FROM api_keys WHERE provider = ?', (provider,))
        res = cursor.fetchone()
        is_custom = res[0] if res else 0
        
        detail_card = tk.Frame(self.locker_detail_frame, bg="white", padx=30, pady=30, highlightbackground="#dcdde1", highlightthickness=1)
        detail_card.pack(fill=tk.X, pady=10)
        
        # Status and Toggle
        status_row = tk.Frame(detail_card, bg="white")
        status_row.pack(fill=tk.X, pady=(0, 20))
        
        active_var = tk.IntVar(value=p_data['active'])
        check = tk.Checkbutton(status_row, text=f" Enable {provider} for Chat", 
                               variable=active_var, font=("Segoe UI", 10, "bold"),
                               bg="white", activebackground="white")
        check.pack(side=tk.LEFT)
        
        if is_custom:
            tk.Button(status_row, text="🗑️ Delete Provider", command=lambda: self.delete_provider(provider), 
                      bg="#e74c3c", fg="white", relief="flat", font=("Segoe UI", 8)).pack(side=tk.RIGHT)
        
        # Key/URL Input
        tk.Label(detail_card, text="API Key / Connection URL:", font=("Segoe UI", 10, "bold"), bg="white").pack(anchor="w")
        
        key_var = tk.StringVar(value=p_data['key'])
        is_ollama = provider == "Ollama (Local)"
        
        entry = tk.Entry(detail_card, textvariable=key_var, font=("Segoe UI", 11), bg="#f8f9fa", 
                         show="" if is_ollama else "*", borderwidth=1, relief="solid")
        entry.pack(fill=tk.X, pady=(5, 10))
        
        if is_ollama:
            tk.Label(detail_card, text="Tip: Default Ollama URL is http://localhost:11434", font=("Segoe UI", 9, "italic"), bg="white", fg="#7f8c8d").pack(anchor="w")
        
        # Actions
        btn_frame = tk.Frame(detail_card, bg="white")
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        
        def save():
            key = key_var.get().strip()
            # If saving, we default to enabled if it was already checked or if user wants it active
            is_active = bool(active_var.get())
            # Force enable if they are saving a new key and it's not checked? 
            # Let's just respect the checkbox and the key presence.
            if key and not is_active:
                if messagebox.askyesno("Enable?", f"Do you want to enable {provider} now?"):
                    is_active = True
                    active_var.set(1)

            self.db.save_api_key(provider, key, is_active)
            messagebox.showinfo("Saved", f"Settings for {provider} are now permanent.")
            
        def clear():
            if messagebox.askyesno("Confirm", f"Clear API key for {provider}?"):
                self.db.clear_api_key(provider)
                key_var.set("")
                active_var.set(0)
                messagebox.showinfo("Cleared", f"API key for {provider} removed.")

        def test():
            self.test_api_connection(provider, key_var.get().strip())

        tk.Button(btn_frame, text="🗑️ Clear API", command=clear, bg="#e74c3c", fg="white", relief="flat", padx=20, pady=8).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="🔍 Test Connection", command=test, bg="#95a5a6", fg="white", relief="flat", padx=20, pady=8).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="💾 Save Settings", command=save, bg="#1abc9c", fg="white", relief="flat", padx=30, pady=8).pack(side=tk.RIGHT)

    def delete_provider(self, provider):
        if messagebox.askyesno("Confirm", f"Permanently delete custom provider '{provider}'?"):
            self.db.delete_custom_provider(provider)
            self.provider_combo['values'] = self.db.get_all_providers()
            all_p = self.db.get_all_providers()
            self.provider_combo.set(all_p[0] if all_p else "")
            messagebox.showinfo("Deleted", "Provider removed.")

    def test_api_connection(self, provider, api_key):
        if not api_key and provider != "Ollama (Local)":
            messagebox.showwarning("Missing Key", f"Please enter a key for {provider} first.")
            return
            
        self.show_ai_section()
        self.ai_output.config(state=tk.NORMAL)
        self.ai_output.delete("1.0", tk.END)
        self.append_to_chat("🤖 System", f"🔍 Testing connection to **{provider}**...\n")
        
        if provider == "Google Gemini":
            try:
                url = "https://generativelanguage.googleapis.com/v1beta/models"
                headers = {"x-goog-api-key": api_key}
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m["name"] for m in models if "generateContent" in m.get("supportedGenerationMethods", [])]
                    output = f"✅ Connection to **{provider}** Successful!\n\n**Models found:**\n"
                    for name in model_names: output += f"- {name}\n"
                    self.append_to_chat("🤖 System", output)
                else:
                    self.append_to_chat("🤖 System", f"❌ Connection Failed (Status {response.status_code})\n\nResponse: {response.text}")
            except Exception as e:
                self.append_to_chat("🤖 System", f"❌ Error: {str(e)}")
        elif provider == "Ollama (Local)":
            base_url = api_key if api_key else "http://localhost:11434"
            try:
                response = requests.get(f"{base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    output = f"✅ Connection to **Ollama** Successful!\n\n**Local Models found:**\n"
                    for m in models: output += f"- {m['name']}\n"
                    self.append_to_chat("🤖 System", output)
                else:
                    self.append_to_chat("🤖 System", f"❌ Ollama connection failed. Status: {response.status_code}")
            except Exception as e:
                self.append_to_chat("🤖 System", f"❌ Could not reach Ollama at {base_url}. Is it running?\nError: {str(e)}")
        elif provider in ["OpenAI", "DeepSeek", "Groq", "Mistral AI", "Together AI", "OpenRouter"]:
            # Basic test for OpenAI compatible (try to list models)
            endpoints = {
                "OpenAI": "https://api.openai.com/v1/models",
                "DeepSeek": "https://api.deepseek.com/models",
                "Groq": "https://api.groq.com/openai/v1/models",
                "Mistral AI": "https://api.mistral.ai/v1/models",
                "Together AI": "https://api.together.xyz/v1/models",
                "OpenRouter": "https://openrouter.ai/api/v1/models",
            }
            url = endpoints[provider]
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    self.append_to_chat("🤖 System", f"✅ Connection to **{provider}** Successful!")
                else:
                    self.append_to_chat("🤖 System", f"❌ Connection Failed (Status {response.status_code})\n\nResponse: {response.text}")
            except Exception as e:
                self.append_to_chat("🤖 System", f"❌ Error: {str(e)}")
        else:
            self.append_to_chat("🤖 System", f"⚠️ Direct validation for **{provider}** is not yet implemented, but you can try using it in the chat.")

    # --- Export ---
    def show_export_options(self):
        self.clear_main()
        ttk.Label(self.main_area, text="⚙️ Data Management", style="Header.TLabel").pack(anchor="w", pady=(0, 20))
        
        # Consistent Padding
        PAD_X, PAD_Y = 25, 25
        
        # --- Import Section ---
        import_frame = tk.Frame(self.main_area, bg="white", padx=PAD_X, pady=PAD_Y, highlightbackground="#dcdde1", highlightthickness=1)
        import_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(import_frame, text="📥 Import Data", font=("Segoe UI", 12, "bold"), bg="white", width=15, anchor="w").pack(side=tk.LEFT)
        
        # Buttons on the right
        tk.Button(import_frame, text="Show Template", command=self.show_json_template, bg="#95a5a6", fg="white", relief="flat", padx=15).pack(side=tk.RIGHT)
        tk.Button(import_frame, text="Import Categories", command=self.import_categories_json, bg="#3498db", fg="white", relief="flat", padx=15).pack(side=tk.RIGHT, padx=10)
        tk.Button(import_frame, text="Import Commands", command=self.import_json, bg="#1abc9c", fg="white", relief="flat", padx=15).pack(side=tk.RIGHT)

        # --- Export Section ---
        export_frame = tk.Frame(self.main_area, bg="white", padx=PAD_X, pady=PAD_Y, highlightbackground="#dcdde1", highlightthickness=1)
        export_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(export_frame, text="📤 Export Data", font=("Segoe UI", 12, "bold"), bg="white", width=15, anchor="w").pack(side=tk.LEFT)
        
        # Scope Selection (Center-Left)
        scope_box = tk.Frame(export_frame, bg="white")
        scope_box.pack(side=tk.LEFT, padx=20)
        tk.Label(scope_box, text="Scope:", font=("Segoe UI", 10), bg="white").pack(side=tk.LEFT, padx=(0, 5))
        cat_options = ["All Categories"] + [c[1] for c in self.categories]
        scope_combo = ttk.Combobox(scope_box, textvariable=self.export_cat_var, values=cat_options, state="readonly", width=25)
        scope_combo.pack(side=tk.LEFT)

        # Buttons on the right
        tk.Button(export_frame, text="PDF Export", command=lambda: self.export_pdf(self.get_export_cid()), bg="#e74c3c", fg="white", relief="flat", padx=15).pack(side=tk.RIGHT)
        tk.Button(export_frame, text="Text", command=lambda: self.export_text(self.get_export_cid()), bg="#7f8c8d", fg="white", relief="flat", padx=15).pack(side=tk.RIGHT, padx=5)
        tk.Button(export_frame, text="CSV", command=lambda: self.export_csv(self.get_export_cid()), bg="#27ae60", fg="white", relief="flat", padx=15).pack(side=tk.RIGHT, padx=5)
        tk.Button(export_frame, text="JSON", command=lambda: self.export_json(self.get_export_cid()), bg="#9b59b6", fg="white", relief="flat", padx=15).pack(side=tk.RIGHT, padx=5)

        # --- WhatsApp Section ---
        tk.Label(self.main_area, text="📱 WhatsApp Integration", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 10))
        wa_frame = tk.Frame(self.main_area, bg="white", padx=PAD_X, pady=PAD_Y, highlightbackground="#dcdde1", highlightthickness=1)
        wa_frame.pack(fill=tk.X)

        tk.Label(wa_frame, text="WhatsApp Number", font=("Segoe UI", 12, "bold"), bg="white", width=15, anchor="w").pack(side=tk.LEFT)
        
        # Input Box (Center-Left)
        self.wa_num_var = tk.StringVar(value=self.db.get_setting("whatsapp_number", ""))
        wa_entry = tk.Entry(wa_frame, textvariable=self.wa_num_var, font=("Segoe UI", 11), borderwidth=1, relief="solid")
        wa_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=20)
        
        def save_wa(event=None):
            num = self.wa_num_var.get().strip()
            self.db.save_setting("whatsapp_number", num)
            messagebox.showinfo("Saved", "WhatsApp number saved!")

        wa_entry.bind("<Return>", save_wa)

        # Buttons on the right
        share_btn = tk.Button(wa_frame, text="Share via WhatsApp", command=self.share_to_whatsapp, bg="#25D366", fg="white", relief="flat", padx=20, font=("Segoe UI", 10, "bold"))
        share_btn.pack(side=tk.RIGHT)
        
        save_btn = tk.Button(wa_frame, text="Save Number", command=save_wa, bg="#3498db", fg="white", relief="flat", padx=15)
        save_btn.pack(side=tk.RIGHT, padx=10)

        # Hover Effects
        def on_enter(btn, color): btn.config(bg=color)
        def on_leave(btn, color): btn.config(bg=color)

        share_btn.bind("<Enter>", lambda e: on_enter(share_btn, "#1eb954"))
        share_btn.bind("<Leave>", lambda e: on_leave(share_btn, "#25D366"))
        save_btn.bind("<Enter>", lambda e: on_enter(save_btn, "#2980b9"))
        save_btn.bind("<Leave>", lambda e: on_leave(save_btn, "#3498db"))

    def import_categories_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not path: return
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            categories_list = []
            if isinstance(data, dict) and "categories" in data:
                categories_list = data["categories"]
            elif isinstance(data, list):
                categories_list = data
            else:
                messagebox.showerror("Error", "Invalid JSON format for categories.")
                return
            
            count = 0
            for cat_data in categories_list:
                cat_name = cat_data.get("name")
                if not cat_name: continue
                
                parent_id = self.db.get_or_create_category(cat_name)
                count += 1
                
                subcategories = cat_data.get("subcategories", [])
                for sub_name in subcategories:
                    if isinstance(sub_name, str):
                        self.db.add_category(sub_name, parent_id)
                        count += 1
                    elif isinstance(sub_name, dict):
                        s_name = sub_name.get("name")
                        if s_name:
                            self.db.add_category(s_name, parent_id)
                            count += 1
            
            self.load_categories()
            messagebox.showinfo("Success", f"Imported {count} categories/subcategories.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import categories: {str(e)}")

    def share_to_whatsapp(self):
        number = self.wa_num_var.get().strip()
        if not number:
            messagebox.showwarning("Missing Number", "Please enter and save your WhatsApp number first.")
            return
        
        # We'll share a summary of the selected category
        cid = self.get_export_cid()
        data = self.db.get_commands(category_id=cid)
        if not data:
            messagebox.showwarning("Empty", "No data to share.")
            return
            
        text = f"🚀 My Command Vault - {self.export_cat_var.get()}\n\n"
        for r in data[:5]: # Share first 5 commands as preview
            text += f"🔹 {r[2]}: {r[3]}\n"
        
        if len(data) > 5:
            text += f"\n... and {len(data)-5} more commands."
            
        import urllib.parse
        import webbrowser
        encoded_text = urllib.parse.quote(text)
        url = f"https://wa.me/{number}?text={encoded_text}"
        webbrowser.open(url)
        messagebox.showinfo("WhatsApp", "Opening WhatsApp Web. You can attach your exported PDF manually from there.")

    def export_pdf(self, category_id=None):
        data = self.db.get_commands(category_id=category_id)
        if not data:
            messagebox.showwarning("Empty", "No data to export.")
            return
            
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not path: return
        
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            
            # Increased margins for a spacious feel
            doc = SimpleDocTemplate(path, pagesize=letter, topMargin=50, bottomMargin=50, leftMargin=50, rightMargin=50)
            styles = getSampleStyleSheet()
            elements = []
            
            # Custom Modern Colors
            PRIMARY_COLOR = colors.HexColor("#2c3e50")
            ACCENT_COLOR = colors.HexColor("#1abc9c")
            BG_COLOR = colors.HexColor("#f8f9fa")
            CODE_BG = colors.HexColor("#282c34")
            CODE_TEXT = colors.HexColor("#abb2bf")
            
            # Custom Styles with proper spacing (leading/spaceBefore/spaceAfter)
            title_style = ParagraphStyle('ModernTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=26, textColor=PRIMARY_COLOR, spaceAfter=15, alignment=TA_CENTER)
            subtitle_style = ParagraphStyle('ModernSubtitle', parent=styles['Normal'], fontName='Helvetica', fontSize=11, textColor=colors.gray, spaceAfter=40, alignment=TA_CENTER)
            cat_header_style = ParagraphStyle('CatHeader', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=16, textColor=ACCENT_COLOR, spaceBefore=30, spaceAfter=20)
            
            # Internal Alignment Styles
            INDENT = 20
            cmd_title_style = ParagraphStyle('CmdTitle', parent=styles['Heading3'], fontName='Helvetica-Bold', fontSize=13, textColor=PRIMARY_COLOR, spaceBefore=0, spaceAfter=10, leftIndent=0)
            code_style = ParagraphStyle('ModernCode', fontName='Courier', fontSize=10, textColor=CODE_TEXT, backColor=CODE_BG, borderPadding=12, leftIndent=INDENT, rightIndent=0, spaceBefore=5, spaceAfter=12, leading=14)
            desc_style = ParagraphStyle('ModernDesc', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.darkgrey, leading=16, leftIndent=INDENT, spaceAfter=8)
            usage_style = ParagraphStyle('ModernUsage', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=9, textColor=ACCENT_COLOR, leading=14, leftIndent=INDENT, spaceAfter=10)

            # Header Section
            elements.append(Paragraph("🛡️ Developer Command Vault", title_style))
            
            # Determine correct category name for title
            if category_id:
                target_cat = next((c[1] for c in self.categories if c[0] == category_id), "Unknown Category")
                display_name = target_cat
            else:
                display_name = "All Categories"
                
            elements.append(Paragraph(f"PROFESSIONAL REPORT: {display_name.upper()}<br/>GENERATED ON {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
            elements.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT_COLOR, spaceAfter=30))
            
            # Group by category if exporting all
            current_cat = None
            
            for r in data:
                # r: id, cat_name, title, cmd_text, desc, usage, tags, fav
                cid, cat, title, text, desc, usage, tags, fav = r
                
                # Category Header
                if category_id is None and cat != current_cat:
                    current_cat = cat
                    elements.append(Spacer(1, 10))
                    elements.append(Paragraph(f"📁 {cat.upper()}", cat_header_style))
                    elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey, hAlign=TA_LEFT, spaceAfter=20))

                # Build Command "Card" using KeepTogether to prevent element collapse/splitting
                cmd_elements = []
                
                # Command Title
                cmd_elements.append(Paragraph(f"<b>• {title}</b>", cmd_title_style))
                
                # Explicit space between title and black code section
                cmd_elements.append(Spacer(1, 10))
                
                # Code Block
                cmd_elements.append(Paragraph(f"{text}", code_style))
                
                # Description
                if desc:
                    cmd_elements.append(Paragraph(desc, desc_style))
                
                # Usage
                if usage:
                    cmd_elements.append(Paragraph(f"<b>Usage Example:</b> {usage}", usage_style))
                
                # Use KeepTogether to ensure title, code, desc, and usage stay as one unit
                elements.append(KeepTogether(cmd_elements))
                
                # Generous spacing between command units
                elements.append(Spacer(1, 25))
                # subtle modern separator
                elements.append(HRFlowable(width="100%", thickness=0.2, color=colors.HexColor("#e0e0e0"), spaceAfter=15))
            
            doc.build(elements)
            messagebox.showinfo("Exported", f"Beautiful PDF report saved to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF: {str(e)}")

    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not path: return
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                messagebox.showerror("Error", "JSON must be a list of commands.")
                return
                
            count = 0
            for item in data:
                cat_name = item.get("category", "General")
                title = item.get("title", "Untitled")
                cmd = item.get("command", "")
                desc = item.get("description", "")
                usage = item.get("usage", "")
                tags = item.get("tags", "")
                
                if cmd:
                    cat_id = self.db.get_or_create_category(cat_name)
                    self.db.add_command(cat_id, title, cmd, desc, usage, tags)
                    count += 1
            
            self.load_categories()
            self.show_dashboard()
            messagebox.showinfo("Import Success", f"Successfully imported {count} commands.")
            
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to parse JSON: {str(e)}")

    def show_json_template(self):
        template = [
            {
                "category": "Backend > Python",
                "title": "Example Subcategory Command",
                "command": "python --version",
                "description": "Show python version.",
                "usage": "python --version",
                "tags": "python, version"
            },
            {
                "category": "Git",
                "title": "Example Command",
                "command": "git status",
                "description": "Show the working tree status.",
                "usage": "Run this to see changed files.",
                "tags": "git, status, cli"
            }
        ]
        
        dialog = tk.Toplevel(self.root)
        dialog.title("JSON Import Template")
        dialog.geometry("600x450")
        
        text_area = tk.Text(dialog, font=("Consolas", 10), padx=10, pady=10)
        text_area.pack(fill=tk.BOTH, expand=True)
        text_area.insert("1.0", json.dumps(template, indent=4))
        text_area.config(state=tk.DISABLED)
        
        tk.Button(dialog, text="Close", command=dialog.destroy, pady=5).pack(fill=tk.X)

    def get_export_cid(self):
        sel = self.export_cat_var.get()
        if sel == "All Categories": return None
        return next((c[0] for c in self.categories if c[1] == sel), None)

    def export_json(self, category_id=None):
        data = self.db.get_commands(category_id=category_id)
        if not data:
            messagebox.showwarning("Empty", "No data to export for this selection.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if path:
            with open(path, 'w') as f:
                json.dump([{"title": d[2], "command": d[3], "category": d[1], "usage": d[5]} for d in data], f, indent=4)
            messagebox.showinfo("Exported", f"Saved to {path}")

    def export_csv(self, category_id=None):
        data = self.db.get_commands(category_id=category_id)
        if not data:
            messagebox.showwarning("Empty", "No data to export for this selection.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if path:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Category", "Title", "Command", "Description", "Usage Example"])
                for r in data: writer.writerow(r[:6])
            messagebox.showinfo("Exported", f"Saved to {path}")

    def export_text(self, category_id=None):
        data = self.db.get_commands(category_id=category_id)
        if not data:
            messagebox.showwarning("Empty", "No data to export for this selection.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if path:
            with open(path, 'w') as f:
                for r in data:
                    f.write(f"--- {r[2]} ({r[1]}) ---\nCommand: {r[3]}\nDescription: {r[4]}\nExample: {r[5]}\n\n")
            messagebox.showinfo("Exported", f"Saved to {path}")

    def open_add_dialog_from_ai(self, ai_text):
        # We try to parse the command from the AI text (look for the first code block)
        import re
        code_match = re.search(r'```(?:bash|text|linux)?\n(.*?)\n```', ai_text, re.DOTALL)
        extracted_cmd = code_match.group(1) if code_match else ""
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Save AI Result to Vault")
        dialog.geometry("500x650")
        
        main_frame = ttk.Frame(dialog, padding=25)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="Category:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        cat_var = tk.StringVar()
        cat_combo = ttk.Combobox(main_frame, textvariable=cat_var, values=[c[1] for c in self.categories], state="readonly")
        cat_combo.pack(fill=tk.X, pady=(5, 15))
        if self.categories: cat_combo.current(0)
            
        tk.Label(main_frame, text="Title:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        title_entry = ttk.Entry(main_frame)
        title_entry.pack(fill=tk.X, pady=(5, 15))
        
        tk.Label(main_frame, text="Command:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        cmd_text = tk.Text(main_frame, height=5, font=("Consolas", 10))
        cmd_text.insert("1.0", extracted_cmd)
        cmd_text.pack(fill=tk.X, pady=(5, 15))
        
        tk.Label(main_frame, text="Description/Notes (from AI):", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        desc_text = tk.Text(main_frame, height=6)
        # Clean up AI text for description (remove markdown)
        clean_desc = re.sub(r'#+\s*|\*\*|```.*?```', '', ai_text, flags=re.DOTALL).strip()
        desc_text.insert("1.0", clean_desc[:300] + "...")
        desc_text.pack(fill=tk.X, pady=(5, 15))
        
        def save():
            cat_name = cat_var.get()
            cat_id = next((c[0] for c in self.categories if c[1] == cat_name), None)
            title = title_entry.get().strip()
            cmd = cmd_text.get("1.0", tk.END).strip()
            desc = desc_text.get("1.0", tk.END).strip()
            
            if title and cmd:
                self.db.add_command(cat_id, title, cmd, desc, "Generated by AI", "")
                self.show_dashboard()
                dialog.destroy()
                messagebox.showinfo("Saved", "Command added to your vault!")
                
        tk.Button(main_frame, text="✅ Save to Vault", command=save, bg="#1abc9c", fg="white", relief="flat", pady=10).pack(fill=tk.X)

    def delete_selected_categories(self):
        selection = self.cat_tree.selection()
        if not selection:
            messagebox.showwarning("Selection", "Please select one or more categories to delete.")
            return
            
        if not messagebox.askyesno("Confirm", f"Are you sure you want to delete {len(selection)} selected categories?\nThis will ALSO delete all commands inside them!"):
            return
            
        results = []
        for item_id in selection:
            item = self.cat_tree.item(item_id)
            cid = item['values'][0]
            name = item['text']
            ok, msg = self.db.delete_category(cid)
            if not ok:
                results.append(f"• {name}: {msg}")
        
        self.load_categories()
        self.show_dashboard()
        
        if results:
            error_report = "Some categories could not be deleted:\n\n" + "\n".join(results)
            messagebox.showwarning("Batch Deletion Results", error_report)
        else:
            messagebox.showinfo("Success", "All selected categories and their commands deleted.")

    def clear_all_categories(self):
        if not messagebox.askyesno("Confirm", "Are you sure you want to delete ALL categories and ALL commands?\n\nThis will reset the vault to defaults."):
            return
            
        ok, msg = self.db.delete_all_categories()
        if ok:
            self.load_categories()
            self.show_dashboard()
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showerror("Error", msg)

    def open_add_category_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Category")
        dialog.geometry("400x300")
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="Category Name:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        name_entry = ttk.Entry(main_frame)
        name_entry.pack(fill=tk.X, pady=(5, 15))
        
        tk.Label(main_frame, text="Parent Category (Optional):", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        parent_var = tk.StringVar(value="None (Root)")
        parent_options = ["None (Root)"] + [c[1] for c in self.categories]
        parent_combo = ttk.Combobox(main_frame, textvariable=parent_var, values=parent_options, state="readonly")
        parent_combo.pack(fill=tk.X, pady=(5, 15))
        
        def save():
            name = name_entry.get().strip()
            parent_name = parent_var.get()
            parent_id = None
            if parent_name != "None (Root)":
                parent_id = next((c[0] for c in self.categories if c[1] == parent_name), None)
            
            if name:
                ok, msg = self.db.add_category(name, parent_id)
                if ok:
                    self.load_categories()
                    dialog.destroy()
                    messagebox.showinfo("Success", f"Category '{name}' added.")
                else:
                    messagebox.showerror("Error", msg)
        
        tk.Button(main_frame, text="Add Category", command=save, bg="#1abc9c", fg="white", relief="flat", pady=10).pack(fill=tk.X)

    # --- Add Command ---
    def open_add_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Command")
        dialog.geometry("500x600")
        
        main_frame = ttk.Frame(dialog, padding=25)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="Category:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        cat_var = tk.StringVar()
        cat_combo = ttk.Combobox(main_frame, textvariable=cat_var, values=[c[1] for c in self.categories], state="readonly")
        cat_combo.pack(fill=tk.X, pady=(5, 15))
        if self.categories: cat_combo.current(0)
            
        tk.Label(main_frame, text="Title:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        title_entry = ttk.Entry(main_frame)
        title_entry.pack(fill=tk.X, pady=(5, 15))
        
        tk.Label(main_frame, text="Command:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        cmd_text = tk.Text(main_frame, height=5, font=("Consolas", 10))
        cmd_text.pack(fill=tk.X, pady=(5, 15))
        
        tk.Label(main_frame, text="Description:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        desc_text = tk.Text(main_frame, height=3)
        desc_text.pack(fill=tk.X, pady=(5, 15))

        tk.Label(main_frame, text="Usage Example:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        usage_text = tk.Text(main_frame, height=2)
        usage_text.pack(fill=tk.X, pady=(5, 15))
        
        def save():
            cat_name = cat_var.get()
            cat_id = next((c[0] for c in self.categories if c[1] == cat_name), None)
            title = title_entry.get().strip()
            cmd = cmd_text.get("1.0", tk.END).strip()
            desc = desc_text.get("1.0", tk.END).strip()
            usage = usage_text.get("1.0", tk.END).strip()
            
            if title and cmd:
                self.db.add_command(cat_id, title, cmd, desc, usage, "")
                self.show_dashboard()
                dialog.destroy()
                
        tk.Button(main_frame, text="Save Command", command=save, bg="#1abc9c", fg="white", relief="flat", pady=10).pack(fill=tk.X)

if __name__ == "__main__":
    root = tk.Tk()
    app = CommandVaultApp(root)
    root.mainloop()
