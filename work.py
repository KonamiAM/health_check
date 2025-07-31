import hashlib

# --- Login Window for authentication ---
class LoginWindow:
    def __init__(self, root, db_config, on_success):
        self.root = root
        self.db_config = db_config
        self.on_success = on_success
        self.root.title("Login - System Health Monitor")
        self.root.geometry("400x300")
        self.frame = ttk.Frame(self.root, padding=30)
        self.frame.pack(expand=True)
        ttk.Label(self.frame, text="Login", style='Title.TLabel').pack(pady=(0, 20))
        ttk.Label(self.frame, text="Username:").pack(anchor=tk.W)
        self.username_entry = ttk.Entry(self.frame, width=30)
        self.username_entry.pack(pady=5)
        ttk.Label(self.frame, text="Password:").pack(anchor=tk.W)
        self.password_entry = ttk.Entry(self.frame, show="*", width=30)
        self.password_entry.pack(pady=5)
        ttk.Label(self.frame, text="Gmail Address:").pack(anchor=tk.W)
        self.email_entry = ttk.Entry(self.frame, width=30)
        self.email_entry.pack(pady=5)
        self.message_label = ttk.Label(self.frame, text="", foreground="red")
        self.message_label.pack(pady=5)
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Login", style='Submit.TButton', command=self.login).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Register", style='Export.TButton', command=self.register).pack(side=tk.LEFT, padx=5)
        self.username_entry.focus()

    def hash_password(self, password):
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            self.message_label.config(text="Please enter username and password.")
            return
        try:
            import mysql.connector
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username=%s", (username,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row and row[0] == self.hash_password(password):
                self.on_success(username)
            else:
                self.message_label.config(text="Invalid username or password.")
        except Exception as e:
            self.message_label.config(text=f"Login error: {e}")

    def register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        email = self.email_entry.get().strip()
        if not username or not password or not email:
            self.message_label.config(text="Please enter username, password, and email address.")
            return
        # Basic email validation
        import re
        email_regex = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        if not re.match(email_regex, email):
            self.message_label.config(text="Please enter a valid email address.")
            return
        try:
            import mysql.connector
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            if cursor.fetchone():
                self.message_label.config(text="Username already exists.")
                cursor.close()
                conn.close()
                return
            # Check if email already exists
            try:
                cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
                if cursor.fetchone():
                    self.message_label.config(text="Gmail address already registered.")
                    cursor.close()
                    conn.close()
                    return
            except Exception:
                pass  # If column doesn't exist, will error below
            hashed = self.hash_password(password)
            # Try to insert with email, fallback if column missing
            try:
                cursor.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (username, hashed, email))
            except Exception as e:
                # If error due to missing email column, add it
                if "Unknown column 'email'" in str(e):
                    cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(128)")
                    conn.commit()
                    cursor.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (username, hashed, email))
                else:
                    raise
            conn.commit()
            cursor.close()
            conn.close()
            self.message_label.config(text="Registration successful! Please login.", foreground="green")
        except Exception as e:
            self.message_label.config(text=f"Register error: {e}")
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import mysql.connector
from datetime import datetime, timedelta
import csv
import os
from fpdf import FPDF
from calendar import monthrange
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import requests
from tkcalendar import DateEntry
import json

class ToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0,0,0,0)
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class HealthCheckApp:
    def ensure_maintenance_table(self):
        """Ensure the maintenance_interventions table exists."""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_interventions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    date DATE NOT NULL,
                    description TEXT NOT NULL,
                    performed_by VARCHAR(64) NOT NULL
                )
            """)
            conn.commit()
            cursor.close()
            conn.close()
        except Exception:
            pass

    def create_maintenance_tab(self, parent=None):
        """Create the Maintenance Interventions tab UI."""
        tab = parent or ttk.Frame(self.content_frame, style='TFrame')
        main_frame = ttk.Frame(tab, style='TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Top: Add new intervention
        add_frame = ttk.LabelFrame(main_frame, text="Add Maintenance Intervention", style='Card.TLabelframe')
        add_frame.pack(fill=tk.X, pady=(0, 16))
        ttk.Label(add_frame, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky='e', padx=4, pady=4)
        date_entry = ttk.Entry(add_frame, width=12)
        date_entry.grid(row=0, column=1, padx=4, pady=4)
        date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        ttk.Label(add_frame, text="Description:").grid(row=0, column=2, sticky='e', padx=4, pady=4)
        desc_entry = ttk.Entry(add_frame, width=40)
        desc_entry.grid(row=0, column=3, padx=4, pady=4)
        ttk.Label(add_frame, text="Performed by:").grid(row=0, column=4, sticky='e', padx=4, pady=4)
        by_entry = ttk.Entry(add_frame, width=18)
        by_entry.grid(row=0, column=5, padx=4, pady=4)
        def add_intervention():
            date_val = date_entry.get().strip()
            desc_val = desc_entry.get().strip()
            by_val = by_entry.get().strip()
            if not (date_val and desc_val and by_val):
                messagebox.showwarning("Missing Data", "Please fill all fields.", parent=self.root)
                return
            try:
                conn = mysql.connector.connect(**self.db_config)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO maintenance_interventions (date, description, performed_by)
                    VALUES (%s, %s, %s)
                """, (date_val, desc_val, by_val))
                conn.commit()
                cursor.close()
                conn.close()
                messagebox.showinfo("Success", "Intervention added.", parent=self.root)
                date_entry.delete(0, tk.END)
                date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
                desc_entry.delete(0, tk.END)
                by_entry.delete(0, tk.END)
                refresh_table()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add intervention: {e}", parent=self.root)
        add_btn = ttk.Button(add_frame, text="Add", style='Submit.TButton', command=add_intervention)
        add_btn.grid(row=0, column=6, padx=8, pady=4)

        # Middle: Table of interventions
        table_frame = ttk.LabelFrame(main_frame, text="Maintenance Interventions Log", style='Card.TLabelframe')
        table_frame.pack(fill=tk.BOTH, expand=True)
        columns = ("id", "date", "description", "performed_by")
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
        for col, w in zip(columns, (40, 100, 350, 120)):
            tree.heading(col, text=col.replace('_', ' ').title())
            tree.column(col, width=w, anchor='w')
        tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Bottom: Delete button
        def delete_selected():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("No Selection", "Select a row to delete.", parent=self.root)
                return
            iid = tree.item(sel[0])['values'][0]
            if not messagebox.askyesno("Confirm", "Delete selected intervention?", parent=self.root):
                return
            try:
                conn = mysql.connector.connect(**self.db_config)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM maintenance_interventions WHERE id=%s", (iid,))
                conn.commit()
                cursor.close()
                conn.close()
                refresh_table()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete: {e}", parent=self.root)
        del_btn = ttk.Button(main_frame, text="Delete Selected", style='Clear.TButton', command=delete_selected)
        del_btn.pack(pady=8, anchor='e')

        def refresh_table():
            for row in tree.get_children():
                tree.delete(row)
            try:
                conn = mysql.connector.connect(**self.db_config)
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM maintenance_interventions ORDER BY date DESC, id DESC")
                for row in cursor.fetchall():
                    tree.insert('', tk.END, values=(row['id'], row['date'], row['description'], row['performed_by']))
                cursor.close()
                conn.close()
            except Exception as e:
                pass
        refresh_table()
        return tab
    def get_email_sender_info_path(self):
        base_dir = getattr(self, 'export_dir', os.getcwd())
        return os.path.join(base_dir, 'email_sender_info.json')

    def save_email_sender_info(self, info):
        try:
            with open(self.get_email_sender_info_path(), 'w', encoding='utf-8') as f:
                json.dump(info, f)
        except Exception as e:
            print(f"[WARN] Could not save sender info: {e}")

    def load_email_sender_info(self):
        try:
            with open(self.get_email_sender_info_path(), 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    def delete_selected_table(self):
        """Delete the selected health check table from the database."""
        selected_item = self.tables_tree.selection()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a table to delete", parent=self.root)
            return
        table_name = self.tables_tree.item(selected_item)['values'][0]
        if not table_name.startswith('health_check_'):
            messagebox.showwarning("Invalid Table", "You can only delete health check tables.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete table '{table_name}'? This cannot be undone.",
            parent=self.root
        ):
            return
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()
            cursor.close()
            conn.close()
            messagebox.showinfo("Delete Successful", f"Table '{table_name}' has been deleted.", parent=self.root)
            self.refresh_tables_list()
            if hasattr(self, 'update_dashboard'):
                self.update_dashboard()
        except Exception as e:
            messagebox.showerror("Delete Failed", f"Error deleting table: {e}", parent=self.root)
    def copy_yesterday_to_today(self):
        """Copy yesterday's health check table to today's table (structure and data), and fill the form with yesterday's values."""
        from datetime import datetime, timedelta
        try:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            today_table = f"health_check_{today.strftime('%Y%m%d')}"
            yesterday_table = f"health_check_{yesterday.strftime('%Y%m%d')}"
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            # Check if yesterday's table exists
            cursor.execute(f"SHOW TABLES LIKE '{yesterday_table}'")
            if not cursor.fetchone():
                messagebox.showwarning("Table Not Found", f"Yesterday's table ({yesterday_table}) does not exist.", parent=self.root)
                cursor.close()
                conn.close()
                return
            # Check if today's table already exists
            cursor.execute(f"SHOW TABLES LIKE '{today_table}'")
            if cursor.fetchone():
                messagebox.showwarning("Table Exists", f"Today's table ({today_table}) already exists.", parent=self.root)
                cursor.close()
                conn.close()
                return
            # Copy structure
            cursor.execute(f"CREATE TABLE {today_table} LIKE {yesterday_table}")
            # Copy data
            cursor.execute(f"INSERT INTO {today_table} SELECT * FROM {yesterday_table}")
            conn.commit()
            # Now fetch yesterday's data to fill the form
            cursor.close()
            conn.close()
            # Fetch yesterday's data for the form
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"SELECT * FROM {yesterday_table}")
            yesterday_data = {row['check_name']: row for row in cursor.fetchall()}
            cursor.close()
            conn.close()
            # Fill the form fields
            for i, label in enumerate(self.check_labels):
                row = yesterday_data.get(label)
                if row:
                    status = row.get('status', 'OK')
                    self.check_vars[i].set(1 if status == 'OK' else 0)
                    # Show/hide reason box as needed
                    self.toggle_reason(self.check_vars[i], i)
                    if status == 'NOT OK':
                        self.reason_entries[i].delete('1.0', tk.END)
                        self.reason_entries[i].insert('1.0', row.get('reason', ''))
                    else:
                        self.reason_entries[i].delete('1.0', tk.END)
                    self.notes_entries[i].delete('1.0', tk.END)
                    self.notes_entries[i].insert('1.0', row.get('notes', ''))
                else:
                    self.check_vars[i].set(1)
                    self.toggle_reason(self.check_vars[i], i)
                    self.reason_entries[i].delete('1.0', tk.END)
                    self.notes_entries[i].delete('1.0', tk.END)
            messagebox.showinfo("Copy Successful", f"Copied {yesterday_table} to {today_table} and filled the form with yesterday's data.", parent=self.root)
            # Refresh tables list and dashboard
            self.refresh_tables_list()
            if hasattr(self, 'update_dashboard'):
                self.update_dashboard()
        except Exception as e:
            messagebox.showerror("Copy Failed", f"Error copying table: {e}", parent=self.root)
    def export_report_pdf(self):
        report_text = self.report_text.get(1.0, tk.END)
        if not report_text.strip():
            messagebox.showwarning("Empty Report", "There is no report to export.")
            return
        first_line = report_text.split('\n')[0]
        safe_filename = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in first_line)
        file_path = filedialog.asksaveasfilename(
            initialdir=self.export_dir,
            initialfile=f"{safe_filename}.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)

            # Modern Title
            lines = report_text.splitlines()
            if lines:
                pdf.set_font("Arial", 'B', 18)
                pdf.set_text_color(33, 150, 243)  # Blue
                pdf.cell(0, 14, lines[0], ln=1, align='C')
                pdf.set_draw_color(33, 150, 243)
                pdf.set_line_width(1)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(6)
                start_idx = 1
            else:
                start_idx = 0

            pdf.set_font("Arial", size=12)
            pdf.set_text_color(44, 62, 80)  # Dark text

            # Section headers and content
            for idx, line in enumerate(lines[start_idx:]):
                # Section headers
                if line.strip().endswith(":"):
                    pdf.ln(2)
                    pdf.set_font("Arial", 'B', 13)
                    pdf.set_text_color(33, 150, 243)
                    pdf.cell(0, 10, line.strip(), ln=1)
                    pdf.set_font("Arial", size=12)
                    pdf.set_text_color(44, 62, 80)
                # Summary or separator
                elif line.strip().startswith("SUMMARY") or (set(line.strip()) == {'-'} and len(line.strip()) > 5):
                    pdf.ln(2)
                    pdf.set_font("Arial", 'B', 12)
                    pdf.set_text_color(76, 175, 80)  # Green
                    pdf.cell(0, 8, line.strip(), ln=1)
                    pdf.set_font("Arial", size=12)
                    pdf.set_text_color(44, 62, 80)
                # Highlight OK/Failed
                elif "Passed:" in line or "Failed:" in line or "Success rate:" in line:
                    if "Passed:" in line:
                        pdf.set_text_color(76, 175, 80)  # Green
                    elif "Failed:" in line:
                        pdf.set_text_color(244, 67, 54)  # Red
                    elif "Success rate:" in line:
                        pdf.set_text_color(33, 150, 243)  # Blue
                    pdf.cell(0, 8, line.strip(), ln=1)
                    pdf.set_text_color(44, 62, 80)
                # Table header
                elif ("Check Name" in line and "Status" in line) or ("Check Name" in line and "Passed" in line):
                    pdf.ln(2)
                    pdf.set_font("Arial", 'B', 12)
                    pdf.set_fill_color(224, 247, 250)
                    pdf.cell(0, 8, line.strip(), ln=1, fill=True)
                    pdf.set_font("Arial", size=12)
                # Table row
                elif line.strip() and not line.strip().startswith("="):
                    pdf.cell(0, 8, line, ln=1)
                else:
                    pdf.ln(2)

            pdf.output(file_path)
            messagebox.showinfo(
                "Export Successful",
                f"PDF report exported to:\n{file_path}",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "Export Failed",
                f"Error exporting PDF report:\n{str(e)}",
                parent=self.root
            )
    def ensure_username_column(self):
        """Add username column to all health_check tables if missing."""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall() if row[0].startswith('health_check_')]
            for table in tables:
                cursor.execute(f"SHOW COLUMNS FROM {table} LIKE 'username'")
                if not cursor.fetchone():
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN username VARCHAR(50) AFTER notes")
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[ERROR] Could not ensure username column: {e}")
    def __init__(self, root, username=None):
        self.root = root
        self.root.title("System Health Monitor")
        self.root.geometry("1280x960")
        # Modern light blue/white theme
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_modern_styles()
        # Database configuration
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '123456',
            'database': 'health_checks_db'
        }

        # Store logged-in username (if any)
        self.username = username

        # Default export directory
        self.export_dir = r"C:\Users\ROG\Documents\dates"
        os.makedirs(self.export_dir, exist_ok=True)

        # Zabbix config file path
        self.zabbix_config_path = os.path.join(self.export_dir, 'zabbix_config.json')

        # Load Zabbix configuration
        self.zabbix_config = self.load_zabbix_config()
        self.zabbix_data = None

        # Current day table name
        self.current_day_table = None

        self.initialize_database()
        self.ensure_username_column()
        self.ensure_maintenance_table()
        self.check_for_existing_day_table()
        self.create_widgets()
        self.update_zabbix_data()
        self.update_clock()

    def configure_styles(self):
        # Use modern ttk style for a clean look
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TLabel', font=('Segoe UI', 11))
        self.style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'))
        self.style.configure('Card.TLabelframe', font=('Segoe UI', 12, 'bold'))
        self.style.configure('TButton', font=('Segoe UI', 11), padding=6)
        self.style.configure('Submit.TButton', font=('Segoe UI', 11, 'bold'), background='#27ae60', foreground='white')
        self.style.configure('Clear.TButton', font=('Segoe UI', 11, 'bold'), background='#e74c3c', foreground='white')
        self.style.configure('Export.TButton', font=('Segoe UI', 11, 'bold'), background='#2980b9', foreground='white')
        self.style.configure('Report.TButton', font=('Segoe UI', 11, 'bold'), background='#4f8cff', foreground='white')
        self.style.configure('Check.TCheckbutton', font=('Segoe UI', 11))
        self.style.configure('TFrame', background='#f4f6fb')
        self.style.configure('TLabelframe', background='#f4f6fb')
        self.style.configure('TEntry', font=('Segoe UI', 11))
        self.style.configure('Treeview', font=('Segoe UI', 11))
        self.style.configure('TScrollbar', gripcount=0)

    def configure_modern_styles(self):
        style = self.style
        # Light blue and white theme
        primary_bg = '#f6fbff'  # very light blue
        card_bg = '#ffffff'     # white
        accent = '#2196f3'      # blue
        border = '#bbdefb'      # light blue border
        text = '#222e3a'        # dark text
        ok = '#4CAF50'          # green
        not_ok = '#F44336'      # red
        # General
        style.configure('.', font=('Segoe UI', 11), background=primary_bg, foreground=text)
        style.configure('TFrame', background=primary_bg)
        style.configure('Card.TLabelframe', background=card_bg, foreground=accent, borderwidth=2, relief='groove')
        style.configure('TLabelFrame', background=primary_bg, foreground=accent)
        style.configure('TLabel', background=primary_bg, foreground=text, font=('Segoe UI', 10))
        style.configure('Title.TLabel', background=primary_bg, foreground=accent, font=('Segoe UI', 14, 'bold'))
        style.configure('Header.TLabel', background=primary_bg, foreground=accent, font=('Segoe UI', 11, 'bold'))
        style.configure('TButton', font=('Segoe UI', 11), padding=6)
        style.configure('Submit.TButton', font=('Segoe UI', 11, 'bold'), background=accent, foreground='white')
        style.map('Submit.TButton', background=[('active', '#1976d2')])
        style.configure('Clear.TButton', font=('Segoe UI', 11, 'bold'), background='#e3e3e3', foreground=accent)
        style.map('Clear.TButton', background=[('active', '#bbdefb')])
        style.configure('Export.TButton', font=('Segoe UI', 11, 'bold'), background='#b3e5fc', foreground=accent)
        style.map('Export.TButton', background=[('active', '#81d4fa')])
        style.configure('Report.TButton', font=('Segoe UI', 11, 'bold'), background='#e3f2fd', foreground=accent)
        style.map('Report.TButton', background=[('active', '#bbdefb')])
        style.configure('Check.TCheckbutton', font=('Segoe UI', 11))
        style.configure('TEntry', font=('Segoe UI', 11))
        style.configure('Treeview', font=('Segoe UI', 10), background=card_bg, fieldbackground=card_bg, foreground=text, rowheight=28)
        style.configure('Treeview.Heading', background=accent, foreground='white', font=('Segoe UI', 10, 'bold'))
        style.configure('TScrollbar', gripcount=0)
        style.configure('TNotebook', background=primary_bg, borderwidth=0)
        style.configure('TNotebook.Tab', background='#e3f2fd', foreground=accent, font=('Segoe UI', 10, 'bold'), padding=[12, 6])
        style.map('TNotebook.Tab', background=[('selected', card_bg)], foreground=[('selected', accent)])
        # Set root bg
        if hasattr(self, 'root'):
            self.root.configure(bg=primary_bg)
        # Set highlight color for OK/NOT OK labels if present
        if hasattr(self, 'dash_ok_label'):
            self.dash_ok_label.configure(foreground=ok)
        if hasattr(self, 'dash_notok_label'):
            self.dash_notok_label.configure(foreground=not_ok)
        # Set background for all main frames if already created
        for attr in ['content_frame', 'dash_check_status_frame']:
            if hasattr(self, attr):
                getattr(self, attr).configure(style='TFrame')
        style.configure('TLabel', background=primary_bg, foreground=text, font=('Segoe UI', 11))
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'), background=primary_bg, foreground=accent)
        style.configure('TEntry', fieldbackground=card_bg, background=card_bg, foreground=text, bordercolor=border, relief='flat')
        style.configure('TButton', background=accent, foreground='white', borderwidth=0, focusthickness=2, focuscolor=accent, font=('Segoe UI', 11, 'bold'), padding=8)
        style.map('TButton', background=[('active', '#28a428'), ('pressed', '#1e7a1e')])
        style.configure('Submit.TButton', background=ok, foreground='white', borderwidth=0, font=('Segoe UI', 11, 'bold'), padding=8)
        style.map('Submit.TButton', background=[('active', '#28a428'), ('pressed', '#1e7a1e')])
        style.configure('Clear.TButton', background=not_ok, foreground='white', borderwidth=0, font=('Segoe UI', 11, 'bold'), padding=8)
        style.map('Clear.TButton', background=[('active', '#c0392b'), ('pressed', '#922b21')])
        style.configure('Export.TButton', background=accent, foreground='white', borderwidth=0, font=('Segoe UI', 11, 'bold'), padding=8)
        style.map('Export.TButton', background=[('active', '#28a428'), ('pressed', '#1e7a1e')])
        style.configure('Report.TButton', background=accent, foreground='white', borderwidth=0, font=('Segoe UI', 11, 'bold'), padding=8)
        style.map('Report.TButton', background=[('active', '#28a428'), ('pressed', '#1e7a1e')])
        style.configure('Check.TCheckbutton', background=primary_bg, foreground=text, font=('Segoe UI', 11))
        style.configure('TScrollbar', background=card_bg, troughcolor=primary_bg, bordercolor=border)
        style.configure('Treeview', background=card_bg, fieldbackground=card_bg, foreground=text, bordercolor=border, font=('Segoe UI', 11))
        style.configure('Treeview.Heading', background=accent, foreground='white', font=('Segoe UI', 11, 'bold'))
        style.configure('TLabelframe', background=card_bg, foreground=text, borderwidth=0, relief='flat')
        style.configure('TLabelframe.Label', background=card_bg, foreground=accent, font=('Segoe UI', 12, 'bold'))
        # Text widget (manual, since not ttk)
        self.root.option_add('*TCombobox*Listbox.font', 'Segoe UI 11')
        self.root.option_add('*TCombobox*Listbox.background', card_bg)
        self.root.option_add('*TCombobox*Listbox.foreground', text)
        self.root.option_add('*Text.background', card_bg)
        self.root.option_add('*Text.foreground', text)
        self.root.option_add('*Text.font', 'Consolas 11')
        self.root.option_add('*Entry.background', card_bg)
        self.root.option_add('*Entry.foreground', text)
        self.root.option_add('*Entry.font', 'Segoe UI 11')
        self.root.option_add('*Label.background', primary_bg)
        self.root.option_add('*Label.foreground', text)
        self.root.option_add('*Button.background', accent)
        self.root.option_add('*Button.foreground', 'white')
        self.root.option_add('*Button.font', 'Segoe UI 11 bold')
        # Add styles for vertical tab buttons
        style.configure('Tab.TButton', background=card_bg, foreground=accent, font=('Segoe UI', 12, 'bold'), borderwidth=0, relief='flat', padding=10)
        style.map('Tab.TButton', background=[('active', '#b2f2b2'), ('pressed', accent)], foreground=[('active', accent), ('pressed', 'white')])
        style.configure('TabSelected.TButton', background=accent, foreground='white', font=('Segoe UI', 12, 'bold'), borderwidth=0, relief='flat', padding=10)

    def initialize_database(self):
        try:
            conn = mysql.connector.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_config['database']}")
            conn.commit()
            conn.database = self.db_config['database']
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error initializing database: {err}")

    def check_for_existing_day_table(self):
        """Check if there's already a table for today's date and set current_day_table"""
        today = datetime.now().strftime("%Y%m%d")
        self.current_day_table = f"health_check_{today}"

        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute(f"SHOW TABLES LIKE '{self.current_day_table}'")
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                return True
            return False
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error checking for existing table: {err}")
            return False

    def create_widgets(self):
        # Main layout: sidebar + content
        main_frame = ttk.Frame(self.root, style='TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Sidebar for vertical tabs
        sidebar = ttk.Frame(main_frame, style='Card.TLabelframe', padding=(0, 24, 0, 24))
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.configure(width=120)

        # Content area
        self.content_frame = ttk.Frame(main_frame, style='TFrame')
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Tab buttons and frames
        self.tab_frames = {}
        self.tab_buttons = {}
        tab_defs = [
            ("🏥 Health Check", self.create_check_form_tab),
            ("📋 View Tables", self.create_view_tables_tab),
            ("📊 Reports", self.create_reports_tab),
            ("🛠 Maintains", self.create_maintenance_tab),
            ("📈 Dashboard", self.create_dashboard_tab)
        ]
        for i, (label, create_func) in enumerate(tab_defs):
            btn = ttk.Button(
                sidebar,
                text=label,
                style='Tab.TButton',
                command=lambda idx=i: self.select_tab(idx)
            )
            btn.pack(fill=tk.X, pady=6, padx=12, ipadx=8, ipady=8)
            self.tab_buttons[i] = btn
            # Create tab frame but don't pack yet
            frame = ttk.Frame(self.content_frame, style='TFrame')
            self.tab_frames[i] = frame
            # Call the tab creation function with the frame as parent
            create_func(parent=frame)
        # Select the dashboard tab (index 4) by default
        self.select_tab(4)

    def select_tab(self, idx):
        # Hide all frames
        for frame in self.tab_frames.values():
            frame.pack_forget()
        # Show selected frame
        self.tab_frames[idx].pack(fill=tk.BOTH, expand=True)
        # Update button styles
        for i, btn in self.tab_buttons.items():
            if i == idx:
                btn.state(['pressed'])
                btn.configure(style='TabSelected.TButton')
            else:
                btn.state(['!pressed'])
                btn.configure(style='Tab.TButton')

    def create_check_form_tab(self, parent=None):
        tab1 = parent or ttk.Frame(self.notebook, style='TFrame')

        # Header frame with title and clock
        header_frame = ttk.Frame(tab1, style='TFrame')
        header_frame.pack(fill=tk.X, padx=20, pady=10)

        # Application title
        title_label = ttk.Label(header_frame, text="System Health Monitor", style='Title.TLabel')
        title_label.pack(side=tk.LEFT)

        # Clock label (right-aligned)
        self.clock_label = ttk.Label(header_frame, style='TLabel')
        self.clock_label.pack(side=tk.RIGHT)

        # Current day table indicator
        self.day_table_label = ttk.Label(
            header_frame,
            text=f"Today's table: {self.current_day_table if self.current_day_table else 'Not created yet'}",
            style='TLabel'
        )
        self.day_table_label.pack(side=tk.RIGHT, padx=20)

        # Main content frame
        main_frame = ttk.Frame(tab1, style='TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Checkboxes frame with canvas and scrollbar
        canvas = tk.Canvas(main_frame, bg='#f0f8ff', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas, style='TFrame')

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Checkbox labels
        self.check_labels = [
            "Verify Server Health",
            "Assess Critical Application Performance",
            "Validate Daily Backup",
            "Check Data Center Temperature and Humidity",
            "Check Data Center Air Conditioning",
            "Verify UPS and Power Supply"
        ]

        self.check_vars = []
        self.reason_entries = []
        self.notes_entries = []

        # Create checkboxes and reason text areas
        for i, label_text in enumerate(self.check_labels):
            # Item frame
            item_frame = ttk.Frame(self.scrollable_frame, style='TFrame')
            item_frame.pack(fill=tk.X, pady=8)

            # Checkbox with custom style
            var = tk.IntVar(value=1)
            self.check_vars.append(var)
            check = ttk.Checkbutton(
                item_frame,
                text=label_text,
                variable=var,
                style='Check.TCheckbutton',
                command=lambda v=var, i=i: self.toggle_reason(v, i)
            )
            check.pack(anchor=tk.W)

            # Reason frame (hidden by default)
            reason_frame = ttk.Frame(item_frame, style='TFrame')
            reason_label = ttk.Label(reason_frame, text="Reason for issue:", style='TLabel')
            reason_label.pack(anchor=tk.W)
            reason_text = tk.Text(
                reason_frame,
                height=3,
                width=60,
                bg='white',
                fg='#2c3e50',
                font=('Segoe UI', 9),
                padx=5,
                pady=5,
                highlightbackground='#bdc3c7',
                highlightthickness=1
            )
            reason_text.pack(fill=tk.X)
            self.reason_entries.append(reason_text)

            # Notes frame (always visible)
            notes_frame = ttk.Frame(item_frame, style='TFrame')
            notes_label = ttk.Label(notes_frame, text="Additional notes:", style='TLabel')
            notes_label.pack(anchor=tk.W)
            notes_text = tk.Text(
                notes_frame,
                height=2,
                width=60,
                bg='white',
                fg='#2c3e50',
                font=('Segoe UI', 9),
                padx=5,
                pady=5,
                highlightbackground='#bdc3c7',
                highlightthickness=1
            )
            notes_text.pack(fill=tk.X)
            self.notes_entries.append(notes_text)

            notes_frame.pack(fill=tk.X, pady=(5, 0))
            reason_frame.pack_forget()  # Initially hidden

            # Separator
            if i < len(self.check_labels) - 1:
                ttk.Separator(item_frame, orient='horizontal').pack(fill=tk.X, pady=5)

        # Button frame at bottom
        button_frame = ttk.Frame(tab1, style='TFrame')
        button_frame.pack(side=tk.BOTTOM, pady=20)

        # Submit button
        submit_btn = ttk.Button(
            button_frame,
            text="Submit Health Check",
            style='Submit.TButton',
            command=self.on_submit
        )
        submit_btn.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=5)
        ToolTip(submit_btn, "Submit the health check data for today.")

        # Clear database button
        clear_btn = ttk.Button(
            button_frame,
            text="Clear All Data",
            style='Clear.TButton',
            command=self.clear_database
        )
        clear_btn.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=5)
        ToolTip(clear_btn, "Delete all health check data from the database.")

        # Zabbix data display
        zabbix_frame = ttk.LabelFrame(tab1, text="Zabbix Data (Temperature & Humidity)", style='TFrame')
        zabbix_frame.pack(fill=tk.X, pady=10)

        # Temperature label
        self.zabbix_temp_label = ttk.Label(zabbix_frame, text="Temperature: ...", style='TLabel')
        self.zabbix_temp_label.pack(side=tk.LEFT, padx=10)

        # Humidity label
        self.zabbix_humidity_label = ttk.Label(zabbix_frame, text="Humidity: ...", style='TLabel')
        self.zabbix_humidity_label.pack(side=tk.LEFT, padx=10)

        # Error message label
        self.zabbix_error_label = ttk.Label(zabbix_frame, text="", style='TLabel')
        self.zabbix_error_label.pack(side=tk.LEFT, padx=10)

        # Always-visible Refresh button (moved outside zabbix_frame)
        self.refresh_btn = ttk.Button(tab1, text="Refresh Zabbix Data", style='Report.TButton', command=self.update_zabbix_data)
        self.refresh_btn.pack(fill=tk.X, padx=20, pady=(0, 10))
        ToolTip(self.refresh_btn, "Fetch the latest temperature and humidity from Zabbix.")

        # Add Zabbix config editor button to Health Check tab
        self.zabbix_config_btn = ttk.Button(
            tab1,
            text="Edit Zabbix Config",
            style='Report.TButton',
            command=self.open_zabbix_config_dialog
        )
        self.zabbix_config_btn.pack(side=tk.TOP, anchor=tk.NE, padx=20, pady=5)
        ToolTip(self.zabbix_config_btn, "Edit the Zabbix server connection and item keys.")

        # Loading indicator for Zabbix fetch
        self.zabbix_loading_label = ttk.Label(tab1, text="", style='TLabel', foreground='blue')
        self.zabbix_loading_label.pack(fill=tk.X, padx=20, pady=(0, 5))

    def create_view_tables_tab(self, parent=None):
        tab2 = parent or ttk.Frame(self.notebook, style='TFrame')

        # Header frame
        header_frame = ttk.Frame(tab2, style='TFrame')
        header_frame.pack(fill=tk.X, padx=20, pady=10)

        # Title
        title_label = ttk.Label(header_frame, text="Saved Health Checks", style='Title.TLabel')
        title_label.pack(side=tk.LEFT)

        # Refresh button
        refresh_btn = ttk.Button(
            header_frame,
            text="Refresh List",
            command=self.refresh_tables_list,
            style='Submit.TButton'
        )
        refresh_btn.pack(side=tk.RIGHT)
        ToolTip(refresh_btn, "Refresh the list of saved health check tables.")

        # Main content frame
        content_frame = ttk.Frame(tab2, style='TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Treeview to display tables
        self.tables_tree = ttk.Treeview(content_frame, columns=('name', 'records', 'date'), show='headings')
        self.tables_tree.heading('name', text='Table Name')
        self.tables_tree.heading('records', text='Records Count')
        self.tables_tree.heading('date', text='Date')
        self.tables_tree.column('name', width=200)
        self.tables_tree.column('records', width=100, anchor='center')
        self.tables_tree.column('date', width=150, anchor='center')

        # Scrollbar
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=self.tables_tree.yview)
        self.tables_tree.configure(yscrollcommand=scrollbar.set)

        # Pack widgets
        self.tables_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button frame
        btn_frame = ttk.Frame(content_frame, style='TFrame')
        btn_frame.pack(fill=tk.X, pady=10)

        # Export button
        export_btn = ttk.Button(
            btn_frame,
            text="Export Selected to CSV",
            style='Export.TButton',
            command=self.export_to_csv
        )
        export_btn.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)
        ToolTip(export_btn, "Export the selected table data to a CSV file.")

        # Copy yesterday to today button
        copy_btn = ttk.Button(
            btn_frame,
            text="Copy Yesterday as Today",
            style='Export.TButton',
            command=self.copy_yesterday_to_today
        )
        copy_btn.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)
        ToolTip(copy_btn, "Copy yesterday's health check table as today's table (structure and data). Useful if checks are the same.")

        # Delete selected table button
        delete_btn = ttk.Button(
            btn_frame,
            text="Delete Selected Table",
            style='Clear.TButton',
            command=self.delete_selected_table
        )
        delete_btn.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)
        ToolTip(delete_btn, "Delete the selected health check table from the database.")

        # Load tables initially
        self.refresh_tables_list()

    def create_reports_tab(self, parent=None):
        """Create the reports tab with date selection options"""
        tab3 = parent or ttk.Frame(self.notebook, style='TFrame')

        # Header frame
        header_frame = ttk.Frame(tab3, style='TFrame')
        header_frame.pack(fill=tk.X, padx=20, pady=10)

        # Title
        title_label = ttk.Label(header_frame, text="Generate Reports", style='Title.TLabel')
        title_label.pack(side=tk.LEFT)

        # Main content frame
        content_frame = ttk.Frame(tab3, style='TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Date selection frame
        date_frame = ttk.LabelFrame(content_frame, text="Date Selection", style='TFrame')
        date_frame.pack(fill=tk.X, pady=10)

        # Report type selection
        self.report_type = tk.StringVar(value='daily')

        # Daily report option
        daily_opt = ttk.Radiobutton(
            date_frame,
            text="Daily",
            variable=self.report_type,
            value='daily',
            command=self.toggle_date_selection
        )
        daily_opt.grid(row=0, column=0, padx=10, pady=5, sticky='w')

        # Weekly report option
        weekly_opt = ttk.Radiobutton(
            date_frame,
            text="Weekly",
            variable=self.report_type,
            value='weekly',
            command=self.toggle_date_selection
        )
        weekly_opt.grid(row=1, column=0, padx=10, pady=5, sticky='w')

        # Monthly report option
        monthly_opt = ttk.Radiobutton(
            date_frame,
            text="Monthly",
            variable=self.report_type,
            value='monthly',
            command=self.toggle_date_selection
        )
        monthly_opt.grid(row=2, column=0, padx=10, pady=5, sticky='w')

        # Yearly report option
        yearly_opt = ttk.Radiobutton(
            date_frame,
            text="Yearly",
            variable=self.report_type,
            value='yearly',
            command=self.toggle_date_selection
        )
        yearly_opt.grid(row=3, column=0, padx=10, pady=5, sticky='w')

        # Custom range option
        custom_opt = ttk.Radiobutton(
            date_frame,
            text="Custom Range",
            variable=self.report_type,
            value='custom',
            command=self.toggle_date_selection
        )
        custom_opt.grid(row=4, column=0, padx=10, pady=5, sticky='w')

        # Date selection widgets
        self.date_selection_frame = ttk.Frame(date_frame, style='TFrame')
        self.date_selection_frame.grid(row=0, column=1, rowspan=5, padx=10, pady=5, sticky='ew')

        # Single date selection (for daily)
        self.single_date_frame = ttk.Frame(self.date_selection_frame, style='TFrame')
        ttk.Label(self.single_date_frame, text="Date:").pack(side=tk.LEFT)
        self.single_date_entry = DateEntry(self.single_date_frame, width=10, date_pattern='yyyy-mm-dd')
        self.single_date_entry.set_date(datetime.now())
        self.single_date_entry.pack(side=tk.LEFT, padx=5)
        ToolTip(self.single_date_entry, "Select the date for the daily report.")

        # Week selection (for weekly)
        self.week_frame = ttk.Frame(self.date_selection_frame, style='TFrame')
        ttk.Label(self.week_frame, text="Week of:").pack(side=tk.LEFT)
        self.week_entry = DateEntry(self.week_frame, width=10, date_pattern='yyyy-mm-dd')
        self.week_entry.set_date(datetime.now())
        self.week_entry.pack(side=tk.LEFT, padx=5)
        ToolTip(self.week_entry, "Select the starting date of the week for the weekly report.")

        # Month selection (for monthly)
        self.month_frame = ttk.Frame(self.date_selection_frame, style='TFrame')
        ttk.Label(self.month_frame, text="Month:").pack(side=tk.LEFT)
        self.month_entry = ttk.Entry(self.month_frame, width=7)
        self.month_entry.pack(side=tk.LEFT, padx=5)
        self.month_entry.insert(0, datetime.now().strftime('%Y-%m'))
        ToolTip(self.month_entry, "Enter the month in YYYY-MM format.")

        # Year selection (for yearly)
        self.year_frame = ttk.Frame(self.date_selection_frame, style='TFrame')
        ttk.Label(self.year_frame, text="Year:").pack(side=tk.LEFT)
        self.year_entry = ttk.Entry(self.year_frame, width=4)
        self.year_entry.pack(side=tk.LEFT, padx=5)
        self.year_entry.insert(0, datetime.now().strftime('%Y'))
        ToolTip(self.year_entry, "Enter the year in YYYY format.")

        # Custom range selection
        self.custom_range_frame = ttk.Frame(self.date_selection_frame, style='TFrame')
        ttk.Label(self.custom_range_frame, text="From:").pack(side=tk.LEFT)
        self.start_date_entry = DateEntry(self.custom_range_frame, width=10, date_pattern='yyyy-mm-dd')
        self.start_date_entry.set_date(datetime.now() - timedelta(days=7))
        self.start_date_entry.pack(side=tk.LEFT, padx=5)
        ToolTip(self.start_date_entry, "Select the start date for the custom report range.")
        ttk.Label(self.custom_range_frame, text="To:").pack(side=tk.LEFT, padx=(10, 0))
        self.end_date_entry = DateEntry(self.custom_range_frame, width=10, date_pattern='yyyy-mm-dd')
        self.end_date_entry.set_date(datetime.now())
        self.end_date_entry.pack(side=tk.LEFT, padx=5)
        ToolTip(self.end_date_entry, "Select the end date for the custom report range.")

        # Show the appropriate date selection based on report type
        self.toggle_date_selection()

        # Generate report button
        generate_btn = ttk.Button(
            date_frame,
            text="Generate Report",
            style='Report.TButton',
            command=self.generate_report
        )
        generate_btn.grid(row=5, column=0, columnspan=2, pady=10, ipadx=10, ipady=5)
        ToolTip(generate_btn, "Generate a report for the selected period.")

        # Report display area
        self.report_text = tk.Text(
            content_frame,
            height=20,
            width=80,
            bg='white',
            fg='#2c3e50',
            font=('Consolas', 10),
            padx=10,
            pady=10,
            wrap=tk.WORD,
            highlightbackground='#bdc3c7',
            highlightthickness=1
        )
        self.report_text.pack(fill=tk.BOTH, expand=True, pady=10)

        # Export report buttons
        btn_frame = ttk.Frame(content_frame)
        btn_frame.pack(pady=10)

        export_report_btn = ttk.Button(
            btn_frame,
            text="Export Report to File",
            style='Export.TButton',
            command=self.export_report
        )
        export_report_btn.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)
        ToolTip(export_report_btn, "Export the displayed report to a text file.")

        export_pdf_btn = ttk.Button(
            btn_frame,
            text="Export Report as PDF",
            style='Export.TButton',
            command=self.export_report_pdf
        )
        export_pdf_btn.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)
        ToolTip(export_pdf_btn, "Export the displayed report to a PDF file.")

        # Send report via email button
        send_email_btn = ttk.Button(
            btn_frame,
            text="Send Report via Email",
            style='Export.TButton',
            command=self.open_send_email_dialog
        )
        send_email_btn.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)
        ToolTip(send_email_btn, "Send the displayed report to an email address via SMTP.")

        # Button to send report to all users
        send_all_btn = ttk.Button(
            btn_frame,
            text="Send to All Users",
            style='Export.TButton',
            command=self.send_report_to_all_users
        )
        send_all_btn.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=3)
        ToolTip(send_all_btn, "Send the displayed report to all registered users' emails.")
    def send_report_to_all_users(self):
        """Send the current report to all users' emails from the users table."""
        if not self.report_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Empty Report", "There is no report to send.", parent=self.root)
            return
        # Ask for sender SMTP info
        dialog = tk.Toplevel(self.root)
        dialog.title("Send Report to All Users")
        dialog.geometry("520x320")
        dialog.grab_set()
        dialog.resizable(False, False)
        fields = [
            ("From Email", "from_email"),
            ("SMTP Server", "smtp_server"),
            ("SMTP Port", "smtp_port"),
            ("SMTP Username", "smtp_user"),
            ("SMTP Password", "smtp_pass")
        ]
        entries = {}
        sender_info = self.load_email_sender_info()
        for i, (label, key) in enumerate(fields):
            lbl = ttk.Label(dialog, text=label+":")
            lbl.grid(row=i, column=0, sticky='e', padx=10, pady=8)
            ent = ttk.Entry(dialog, width=32, show='*' if 'pass' in key else None)
            ent.grid(row=i, column=1, padx=10, pady=8)
            if key in sender_info:
                ent.insert(0, sender_info[key])
            if key == 'smtp_port' and not ent.get():
                ent.insert(0, '587')
            entries[key] = ent
        status_label = ttk.Label(dialog, text="", foreground='red')
        status_label.grid(row=len(fields), column=0, columnspan=2, pady=4)
        def send_all():
            from_email = entries['from_email'].get().strip()
            smtp_server = entries['smtp_server'].get().strip()
            smtp_port = entries['smtp_port'].get().strip()
            smtp_user = entries['smtp_user'].get().strip()
            smtp_pass = entries['smtp_pass'].get().strip()
            if not (from_email and smtp_server and smtp_port and smtp_user and smtp_pass):
                status_label.config(text="All fields are required.")
                return
            try:
                smtp_port_int = int(smtp_port)
            except ValueError:
                status_label.config(text="SMTP port must be a number.")
                return
            # Save sender info (except password)
            self.save_email_sender_info({
                'from_email': from_email,
                'smtp_server': smtp_server,
                'smtp_port': smtp_port,
                'smtp_user': smtp_user,
                'smtp_pass': smtp_pass
            })
            # Fetch all user emails from DB
            try:
                import mysql.connector
                conn = mysql.connector.connect(**self.db_config)
                cursor = conn.cursor()
                cursor.execute("SELECT email FROM users WHERE email IS NOT NULL AND email != ''")
                emails = [row[0] for row in cursor.fetchall() if row[0]]
                cursor.close()
                conn.close()
            except Exception as e:
                status_label.config(text=f"DB error: {e}")
                return
            if not emails:
                status_label.config(text="No user emails found.")
                return
            try:
                self.send_report_via_email(
                    emails, from_email, smtp_server, smtp_port_int, smtp_user, smtp_pass
                )
                dialog.destroy()
                messagebox.showinfo("Email Sent", f"Report sent to {len(emails)} users.", parent=self.root)
            except Exception as e:
                status_label.config(text=f"Failed: {e}")
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=10)
        send_btn = ttk.Button(btn_frame, text="Send", style='Submit.TButton', command=send_all)
        send_btn.pack(side=tk.LEFT, padx=8, ipadx=16, ipady=6)
        cancel_btn = ttk.Button(btn_frame, text="Cancel", style='Clear.TButton', command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=8, ipadx=16, ipady=6)
        dialog.focus_force()
    def open_send_email_dialog(self):
        """Open a dialog to enter email and SMTP details, then send the report."""
        import tkinter as tk
        from tkinter import simpledialog
        if not self.report_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Empty Report", "There is no report to send.")
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Send Report via Email")
        dialog.geometry("520x420")
        dialog.grab_set()
        dialog.resizable(False, False)
        fields = [
            ("To Email (comma-separated for multiple)", "to_email"),
            ("From Email", "from_email"),
            ("SMTP Server", "smtp_server"),
            ("SMTP Port", "smtp_port"),
            ("SMTP Username", "smtp_user"),
            ("SMTP Password", "smtp_pass")
        ]
        entries = {}
        sender_info = self.load_email_sender_info()
        for i, (label, key) in enumerate(fields):
            lbl = ttk.Label(dialog, text=label+":")
            lbl.grid(row=i, column=0, sticky='e', padx=10, pady=8)
            ent = ttk.Entry(dialog, width=32, show='*' if 'pass' in key else None)
            ent.grid(row=i, column=1, padx=10, pady=8)
            # Prefill from saved info if available (except password)
            if key in sender_info and key != 'smtp_pass':
                ent.insert(0, sender_info[key])
            if key == 'smtp_port' and not ent.get():
                ent.insert(0, '587')
            entries[key] = ent
        status_label = ttk.Label(dialog, text="", foreground='red')
        status_label.grid(row=len(fields), column=0, columnspan=2, pady=4)
        def send():
            to_email = entries['to_email'].get().strip()
            from_email = entries['from_email'].get().strip()
            smtp_server = entries['smtp_server'].get().strip()
            smtp_port = entries['smtp_port'].get().strip()
            smtp_user = entries['smtp_user'].get().strip()
            smtp_pass = entries['smtp_pass'].get().strip()
            if not (to_email and from_email and smtp_server and smtp_port and smtp_user and smtp_pass):
                status_label.config(text="All fields are required.")
                return
            try:
                smtp_port_int = int(smtp_port)
            except ValueError:
                status_label.config(text="SMTP port must be a number.")
                return
            # Save sender info (including password)
            self.save_email_sender_info({
                'from_email': from_email,
                'smtp_server': smtp_server,
                'smtp_port': smtp_port,
                'smtp_user': smtp_user,
                'smtp_pass': smtp_pass
            })
            try:
                # Split multiple emails by comma
                to_emails = [email.strip() for email in to_email.split(',') if email.strip()]
                self.send_report_via_email(
                    to_emails, from_email, smtp_server, smtp_port_int, smtp_user, smtp_pass
                )
                dialog.destroy()
                messagebox.showinfo("Email Sent", f"Report sent to: {', '.join(to_emails)}", parent=self.root)
            except Exception as e:
                status_label.config(text=f"Failed: {e}")
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=10)
        send_btn = ttk.Button(btn_frame, text="Send", style='Submit.TButton', command=send)
        send_btn.pack(side=tk.LEFT, padx=8, ipadx=16, ipady=6)
        cancel_btn = ttk.Button(btn_frame, text="Cancel", style='Clear.TButton', command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=8, ipadx=16, ipady=6)
        dialog.focus_force()

    def send_report_via_email(self, to_emails, from_email, smtp_server, smtp_port, smtp_user, smtp_pass):
        """Send the current report as a PDF via SMTP email. to_emails can be a list of addresses."""

        from email.mime.multipart import MIMEMultipart
        from email.mime.application import MIMEApplication
        from email.mime.text import MIMEText
        import tempfile
        import smtplib
        import os

        # Generate PDF with only check name, no column names or colors
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        report_text = self.report_text.get(1.0, tk.END)
        lines = report_text.splitlines()
        subject = lines[0] if lines and lines[0].strip() else "Health Check Report"
        # Add title (bold, larger)
        if lines:
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 12, lines[0], ln=1, align='C')
            pdf.set_font("Arial", '', 12)
            pdf.ln(2)
            if len(lines) > 1 and lines[1].strip().startswith('='):
                pdf.set_draw_color(100, 100, 100)
                pdf.set_line_width(0.5)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(4)
                start_idx = 2
            else:
                start_idx = 1
        else:
            start_idx = 0

        in_table = False
        for idx, line in enumerate(lines[start_idx:]):
            stripped = line.strip()
            # Section headers
            if stripped.endswith(":") or stripped.endswith("SUMMARY:"):
                pdf.ln(2)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 9, line, ln=1)
                pdf.set_font("Arial", '', 12)
                pdf.ln(1)
                in_table = False
            # Table header (skip column names)
            elif (stripped.startswith("Check Name") and "Status" in line and "Notes" in line) or (stripped.startswith("Check Name") and "Passed" in line):
                in_table = True
                continue
            # Table row: just print the check name (first column)
            elif in_table and stripped and not stripped.startswith("-") and not stripped.startswith("SUMMARY") and not stripped.startswith("Reason:") and not stripped.startswith("Last Failure"):
                check_name_raw = line[:20].rstrip()
                pdf.set_font("Arial", '', 12)
                pdf.cell(0, 8, check_name_raw, ln=1)
            # Reason line (skip)
            elif in_table and stripped.startswith("Reason:"):
                continue
            # End of table
            elif in_table and (stripped.startswith("-") or stripped == ""):
                pdf.ln(2)
                in_table = False
            # Skip table header lines outside table (for extra safety)
            elif (stripped.startswith("Check Name") and ("Status" in line or "Passed" in line)):
                continue
            # Other lines
            elif stripped == "":
                pdf.ln(2)
            else:
                pdf.set_font("Arial", '', 12)
                pdf.multi_cell(0, 8, line, align='L')
                pdf.ln(1)
        # (Old unreachable code removed)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
            pdf.output(tmp_pdf.name)
            pdf_path = tmp_pdf.name

        # Compose email with PDF attachment
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = ', '.join(to_emails) if isinstance(to_emails, list) else to_emails
        msg['Subject'] = subject
        msg.attach(MIMEText("Please find the attached health check report as a PDF.", 'plain', 'utf-8'))

        with open(pdf_path, 'rb') as f:
            part = MIMEApplication(f.read(), _subtype='pdf')
            part.add_header('Content-Disposition', 'attachment', filename=f"{subject}.pdf")
            msg.attach(part)

        try:
            with smtplib.SMTP(smtp_server, int(smtp_port), timeout=15) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                # If to_emails is a string, convert to list
                if isinstance(to_emails, str):
                    to_emails = [to_emails]
                server.sendmail(from_email, to_emails, msg.as_string())
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    def toggle_date_selection(self):
        """Show/hide date selection widgets based on report type"""
        # Hide all frames first
        for frame in [
            self.single_date_frame,
            self.week_frame,
            self.month_frame,
            self.year_frame,
            self.custom_range_frame
        ]:
            frame.pack_forget()

        # Show the appropriate frame
        report_type = self.report_type.get()
        if report_type == 'daily':
            self.single_date_frame.pack(fill=tk.X)
        elif report_type == 'weekly':
            self.week_frame.pack(fill=tk.X)
        elif report_type == 'monthly':
            self.month_frame.pack(fill=tk.X)
        elif report_type == 'yearly':
            self.year_frame.pack(fill=tk.X)
        elif report_type == 'custom':
            self.custom_range_frame.pack(fill=tk.X)

    def refresh_tables_list(self):
        """Refresh the list of tables in the database"""
        self.tables_tree.delete(*self.tables_tree.get_children())

        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall() if table[0].startswith('health_check_')]

            # Get record count for each table and extract date
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]

                # Extract date from table name
                try:
                    date_str = table.split('_')[-1]
                    date_obj = datetime.strptime(date_str, "%Y%m%d").date()
                    formatted_date = date_obj.strftime("%Y-%m-%d")
                except:
                    formatted_date = "Unknown"

                self.tables_tree.insert('', 'end', values=(table, count, formatted_date))

            cursor.close()
            conn.close()

        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error fetching tables: {err}")

    def export_to_csv(self):
        """Export selected table to CSV"""
        selected_item = self.tables_tree.selection()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a table to export")
            return

        table_name = self.tables_tree.item(selected_item)['values'][0]

        # Default filename
        default_filename = os.path.join(self.export_dir, f"{table_name}.csv")

        # Let user choose location
        file_path = filedialog.asksaveasfilename(
            initialdir=self.export_dir,
            initialfile=f"{table_name}.csv",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )

        if not file_path:
            return  # User cancelled

        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)

            # Get data from table
            cursor.execute(f"SELECT * FROM {table_name}")
            data = cursor.fetchall()

            # Write to CSV (with header row)
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                if data:
                    fieldnames = data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)

            cursor.close()
            conn.close()

            messagebox.showinfo(
                "Export Successful",
                f"Table '{table_name}' exported to:\n{file_path}",
                parent=self.root
            )

        except Exception as e:
            messagebox.showerror(
                "Export Failed",
                f"Error exporting table:\n{str(e)}",
                parent=self.root
            )

    def toggle_reason(self, var, index):
        """Show/hide reason text based on checkbox state"""
        if var.get() == 0:  # Unchecked
            self.reason_entries[index].master.pack(fill=tk.X, pady=5)
        else:
            self.reason_entries[index].master.pack_forget()

    def update_clock(self):
        try:
            now = datetime.now()
            date_time = now.strftime("%a, %b %d %Y\n%I:%M:%S %p")
            self.clock_label.config(text=date_time)

            # Check if the day has changed
            today_table_name = self.generate_table_name()
            if self.current_day_table and self.current_day_table != today_table_name:
                self.current_day_table = today_table_name
                self.create_new_table(self.current_day_table)
                self.day_table_label.config(text=f"Today's table: {self.current_day_table}")
                # Clear the form for the new day
                for var in self.check_vars:
                    var.set(1)
                for reason_entry in self.reason_entries:
                    reason_entry.delete("1.0", tk.END)
                for notes_entry in self.notes_entries:
                    notes_entry.delete("1.0", tk.END)
                messagebox.showinfo("New Day", "A new day has begun. A new table has been created.", parent=self.root)


            self.root.after(1000, self.update_clock)  # Schedule next update
        except Exception as e:
            print(f"[ERROR] Clock update failed: {e}")

    def generate_table_name(self):
        """Generate a table name based on current date (YYYYMMDD)"""
        now = datetime.now()
        return f"health_check_{now.strftime('%Y%m%d')}"

    def create_new_table(self, table_name):
        """Create a new table with the given name, including username column"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    check_name VARCHAR(100) NOT NULL,
                    status VARCHAR(10) NOT NULL,
                    reason TEXT,
                    notes TEXT,
                    username VARCHAR(50),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error creating table: {err}")
            return False

    def on_submit(self):
        """Handle form submission - save to current day's table. Keep form filled after submit."""
        today_table_name = self.generate_table_name()
        self.current_day_table = today_table_name # Ensure current_day_table is always up-to-date

        # Explicitly check and create table if it doesn't exist
        if not self.check_for_existing_day_table():
            if not self.create_new_table(self.current_day_table):
                return # Stop if table creation fails

        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)

            # First check if we have existing records for today
            cursor.execute(f"SELECT * FROM {self.current_day_table}")
            existing_rows = {row['check_name']: row for row in cursor.fetchall()}

            for check_var, label, reason_entry, notes_entry in zip(
                self.check_vars, self.check_labels, self.reason_entries, self.notes_entries
            ):
                status = "OK" if check_var.get() == 1 else "NOT OK"
                reason = reason_entry.get("1.0", "end-1c").strip() if status == "NOT OK" else None
                notes = notes_entry.get("1.0", "end-1c").strip()
                username = self.username if hasattr(self, 'username') else None

                if status == "NOT OK" and not reason:
                    messagebox.showwarning("Missing Explanation",
                                         f"Please explain why '{label}' is not functioning")
                    conn.rollback()
                    cursor.close()
                    conn.close()
                    return

                if label in existing_rows:
                    row = existing_rows[label]
                    # Only update if something changed
                    if (
                        row['status'] != status or
                        (row['reason'] or '') != (reason or '') or
                        (row['notes'] or '') != (notes or '')
                    ):
                        cursor.execute(
                            f"""UPDATE {self.current_day_table}
                            SET status = %s, reason = %s, notes = %s, username = %s, timestamp = CURRENT_TIMESTAMP
                            WHERE check_name = %s""",
                            (status, reason, notes, username, label))
                else:
                    # Insert new record
                    cursor.execute(
                        f"""INSERT INTO {self.current_day_table}
                        (check_name, status, reason, notes, username)
                        VALUES (%s, %s, %s, %s, %s)""",
                        (label, status, reason, notes, username)
                    )

            conn.commit()
            cursor.close()
            conn.close()

            self.day_table_label.config(text=f"Today's table: {self.current_day_table}")

            messagebox.showinfo(
                "Success",
                f"Health check saved to table: {self.current_day_table}",
                parent=self.root
            )

            # Do NOT clear the form after submit; keep values as is
            # Only clear on day change (see update_clock)

            # Switch to view tab and refresh list
            self.select_tab(1)
            self.refresh_tables_list()
            # Also update dashboard so per-check status updates immediately
            self.update_dashboard()
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error saving to database: {err}")

    def clear_database(self):
        """Delete all health check tables from the database"""
        if not messagebox.askyesno(
            "Confirm Clear",
            "This will delete ALL health check data!\nAre you sure?",
            parent=self.root
        ):
            return

        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()

            # Get all tables in the database
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]

            # Delete all health check tables
            deleted_count = 0
            for table in tables:
                if table.startswith('health_check_'):
                    cursor.execute(f"DROP TABLE {table}")
                    deleted_count += 1

            conn.commit()
            cursor.close()
            conn.close()

            # Reset current day table
            self.current_day_table = None
            self.day_table_label.config(text="Today's table: Not created yet")

            messagebox.showinfo(
                "Success",
                f"Deleted {deleted_count} health check tables",
                parent=self.root
            )

            # Refresh tables list
            self.refresh_tables_list()

        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error clearing database: {err}")

    def generate_report(self):
        """Generate a report based on the selected type and date range"""
        report_type = self.report_type.get()

        try:
            if report_type == 'daily':
                date_str = self.single_date_entry.get()
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    messagebox.showerror("Invalid Date", "Please enter a valid date in YYYY-MM-DD format")
                    return

                table_name = f"health_check_{date_obj.strftime('%Y%m%d')}"
                report_title = f"Daily Health Check Report - {date_obj.strftime('%Y-%m-%d')}"

                conn = mysql.connector.connect(**self.db_config)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(f"SELECT * FROM {table_name}")
                report_data = cursor.fetchall()
                cursor.close()
                conn.close()

                self.display_report(report_title, report_data, report_type)

            elif report_type == 'weekly':
                date_str = self.week_entry.get()
                try:
                    start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    messagebox.showerror("Invalid Date", "Please enter a valid date in YYYY-MM-DD format")
                    return

                end_date = start_date + timedelta(days=6)
                report_title = f"Weekly Health Check Report - {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                report_data = []

                conn = mysql.connector.connect(**self.db_config)
                cursor = conn.cursor(dictionary=True)

                for single_date in (start_date + timedelta(n) for n in range(7)):
                    table_name = f"health_check_{single_date.strftime('%Y%m%d')}"
                    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                    if cursor.fetchone():
                        cursor.execute(f"SELECT * FROM {table_name}")
                        day_data = cursor.fetchall()
                        for record in day_data:
                            record['date'] = single_date.strftime('%Y-%m-%d')
                            report_data.append(record)

                cursor.close()
                conn.close()

                self.display_report(report_title, report_data, report_type)

            elif report_type == 'monthly':
                month_str = self.month_entry.get()
                try:
                    year, month = map(int, month_str.split('-'))
                    first_day = datetime(year, month, 1).date()
                    last_day = datetime(year, month, monthrange(year, month)[1]).date()
                except ValueError:
                    messagebox.showerror("Invalid Month", "Please enter a valid month in YYYY-MM format")
                    return

                report_title = f"Monthly Health Check Report - {first_day.strftime('%Y-%m')}"
                report_data = []

                conn = mysql.connector.connect(**self.db_config)
                cursor = conn.cursor(dictionary=True)

                current_date = first_day
                while current_date <= last_day:
                    table_name = f"health_check_{current_date.strftime('%Y%m%d')}"
                    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                    if cursor.fetchone():
                        cursor.execute(f"SELECT * FROM {table_name}")
                        day_data = cursor.fetchall()
                        for record in day_data:
                            record['date'] = current_date.strftime('%Y-%m-%d')
                            report_data.append(record)
                    current_date += timedelta(days=1)

                cursor.close()
                conn.close()

                self.display_report(report_title, report_data, report_type)

            elif report_type == 'yearly':
                year_str = self.year_entry.get()
                try:
                    year = int(year_str)
                    first_day = datetime(year, 1, 1).date()
                    last_day = datetime(year, 12, 31).date()
                except ValueError:
                    messagebox.showerror("Invalid Year", "Please enter a valid 4-digit year")
                    return

                report_title = f"Yearly Health Check Report - {year}"
                report_data = []

                conn = mysql.connector.connect(**self.db_config)
                cursor = conn.cursor(dictionary=True)

                current_date = first_day
                while current_date <= last_day:
                    table_name = f"health_check_{current_date.strftime('%Y%m%d')}"
                    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                    if cursor.fetchone():
                        cursor.execute(f"SELECT * FROM {table_name}")
                        day_data = cursor.fetchall()
                        for record in day_data:
                            record['date'] = current_date.strftime('%Y-%m-%d')
                            report_data.append(record)
                    current_date += timedelta(days=1)

                cursor.close()
                conn.close()

                self.display_report(report_title, report_data, 'yearly')

            elif report_type == 'custom':
                try:
                    start_date = datetime.strptime(self.start_date_entry.get(), '%Y-%m-%d').date()
                    end_date = datetime.strptime(self.end_date_entry.get(), '%Y-%m-%d').date()
                except ValueError:
                    messagebox.showerror("Invalid Date", "Please enter valid dates in YYYY-MM-DD format")
                    return

                if start_date > end_date:
                    messagebox.showerror("Invalid Range", "Start date must be before end date")
                    return

                report_title = f"Custom Health Check Report - {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                report_data = []

                conn = mysql.connector.connect(**self.db_config)
                cursor = conn.cursor(dictionary=True)

                current_date = start_date
                while current_date <= end_date:
                    table_name = f"health_check_{current_date.strftime('%Y%m%d')}"
                    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                    if cursor.fetchone():
                        cursor.execute(f"SELECT * FROM {table_name}")
                        day_data = cursor.fetchall()
                        for record in day_data:
                            record['date'] = current_date.strftime('%Y-%m-%d')
                            report_data.append(record)
                    current_date += timedelta(days=1)

                cursor.close()
                conn.close()

                self.display_report(report_title, report_data, 'custom')

        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error generating report: {err}")

    def display_report(self, title, data, report_type):
        self.report_text.delete(1.0, tk.END)
        # Add title
        self.report_text.insert(tk.END, f"{title}\n", 'title')
        self.report_text.insert(tk.END, "=" * len(title) + "\n\n", 'title')
        # Add Zabbix data to report
        zabbix = self.zabbix_data or {}
        temp = zabbix.get('temp')
        temp_status = zabbix.get('temp_status')
        humidity = zabbix.get('humidity')
        humidity_status = zabbix.get('humidity_status')
        zabbix_error = zabbix.get('error')
        self.report_text.insert(tk.END, "Zabbix Data (Temperature & Humidity):\n", 'header')
        if zabbix_error:
            self.report_text.insert(tk.END, f"  Error: {zabbix_error}\n", 'not_ok')
        else:
            self.report_text.insert(tk.END, f"  Temperature: {temp if temp is not None else 'N/A'} °C ({temp_status})\n", 'ok' if temp_status=='OK' else 'not_ok')
            self.report_text.insert(tk.END, f"  Humidity: {humidity if humidity is not None else 'N/A'} % ({humidity_status})\n", 'ok' if humidity_status=='OK' else 'not_ok')
        self.report_text.insert(tk.END, "\n")
        if not data:
            self.report_text.insert(tk.END, "No data available for this report period.\n")
            return
        # Find last submitter
        last_submit = None
        if data:
            # Sort by timestamp if available
            try:
                last_submit = max(data, key=lambda r: r.get('timestamp', ''))
            except Exception:
                last_submit = data[-1]
        last_user = last_submit.get('username') if last_submit and 'username' in last_submit else None
        if last_user:
            self.report_text.insert(tk.END, f"Last submitted by: {last_user}\n\n", 'header')
        if report_type == 'daily':
            self.report_text.insert(tk.END, "Check Name".ljust(40), 'header')
            self.report_text.insert(tk.END, "Status".ljust(10), 'header')
            self.report_text.insert(tk.END, "Notes\n", 'header')
            self.report_text.insert(tk.END, "-" * 80 + "\n", 'header')
            for record in data:
                self.report_text.insert(tk.END, record['check_name'].ljust(40))
                status = "OK" if record['status'] == "OK" else "NOT OK"
                status_tag = 'ok' if status == "OK" else 'not_ok'
                self.report_text.insert(tk.END, status.ljust(10), status_tag)
                self.report_text.insert(tk.END, f"{record['notes'] or ''}\n")
                if record['status'] == "NOT OK":
                    self.report_text.insert(tk.END, f"  Reason: {record['reason']}\n\n", 'reason')
                else:
                    self.report_text.insert(tk.END, "\n")
            total_checks = len(data)
            ok_checks = sum(1 for r in data if r['status'] == "OK")
            not_ok_checks = total_checks - ok_checks
            self.report_text.insert(tk.END, "\nSUMMARY:\n", 'header')
            self.report_text.insert(tk.END, f"Total checks: {total_checks}\n")
            self.report_text.insert(tk.END, f"Passed: {ok_checks}\n", 'ok')
            self.report_text.insert(tk.END, f"Failed: {not_ok_checks}\n", 'not_ok')
            self.report_text.insert(tk.END, f"Success rate: {ok_checks/total_checks:.1%}\n")
        else:
            check_stats = {}
            for record in data:
                check_name = record['check_name']
                if check_name not in check_stats:
                    check_stats[check_name] = {
                        'total': 0,
                        'ok': 0,
                        'not_ok': 0,
                        'last_reason': None,
                        'last_date': None
                    }
                check_stats[check_name]['total'] += 1
                if record['status'] == "OK":
                    check_stats[check_name]['ok'] += 1
                else:
                    check_stats[check_name]['not_ok'] += 1
                    check_stats[check_name]['last_reason'] = record.get('reason')
                    check_stats[check_name]['last_date'] = record.get('date')
            self.report_text.insert(tk.END, "Check Name".ljust(40), 'header')
            self.report_text.insert(tk.END, "Passed".center(10), 'header')
            self.report_text.insert(tk.END, "Failed".center(10), 'header')
            self.report_text.insert(tk.END, "Last Failure Date".center(20), 'header')
            self.report_text.insert(tk.END, "Last Failure Reason\n", 'header')
            self.report_text.insert(tk.END, "-" * 100 + "\n", 'header')
            for check_name, stats in check_stats.items():
                self.report_text.insert(tk.END, check_name.ljust(40))
                self.report_text.insert(tk.END, str(stats['ok']).center(10), 'ok')
                self.report_text.insert(tk.END, str(stats['not_ok']).center(10), 'not_ok')
                if stats['last_reason']:
                    self.report_text.insert(tk.END, (stats['last_date'] or 'N/A').center(20))
                    self.report_text.insert(tk.END, stats['last_reason'] + "\n", 'reason')
                else:
                    self.report_text.insert(tk.END, "N/A".center(20))
                    self.report_text.insert(tk.END, "N/A\n")
            total_days = len({r['date'] for r in data if 'date' in r}) if data else 0
            total_checks = sum(stats['total'] for stats in check_stats.values())
            ok_checks = sum(stats['ok'] for stats in check_stats.values())
            not_ok_checks = total_checks - ok_checks
            self.report_text.insert(tk.END, "\nSUMMARY:\n", 'header')
            self.report_text.insert(tk.END, f"Report period covers {total_days} days\n")
            self.report_text.insert(tk.END, f"Total checks performed: {total_checks}\n")
            self.report_text.insert(tk.END, f"Total passed: {ok_checks}\n", 'ok')
            self.report_text.insert(tk.END, f"Total failed: {not_ok_checks}\n", 'not_ok')
            self.report_text.insert(tk.END, f"Overall success rate: {ok_checks/total_checks:.1%}\n")
        self.report_text.tag_config('title', font=('Segoe UI', 14, 'bold'), justify='center')
       
        self.report_text.tag_config('header', font=('Segoe UI', 10, 'bold'))
        self.report_text.tag_config('ok', foreground='green')
        self.report_text.tag_config('not_ok', foreground='red')
        self.report_text.tag_config('reason', foreground='orange')

    def export_report(self):
        report_text = self.report_text.get(1.0, tk.END)
        if not report_text.strip():
            messagebox.showwarning("Empty Report", "There is no report to export.")
            return
        first_line = report_text.split('\n')[0]
        safe_filename = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in first_line)
        default_filename = os.path.join(self.export_dir, f"{safe_filename}.txt")
        file_path = filedialog.asksaveasfilename(
            initialdir=self.export_dir,
            initialfile=f"{safe_filename}.txt",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            messagebox.showinfo(
                "Export Successful",
                f"Report exported to:\n{file_path}",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "Export Failed",
                f"Error exporting report:\n{str(e)}",
                parent=self.root
                       )

    def get_zabbix_temp_humidity(self, zabbix_url, username, password, host, temp_key, humidity_key):
        """
        Retrieve temperature and humidity from Zabbix API.
        Returns: (temp_value, temp_status, humidity_value, humidity_status, error_message)
        """
        try:
            # Authenticate
            payload = {
                "jsonrpc": "2.0",
                "method": "user.login",
                "params": {
                    "user": username,
                    "password": password
                },
                "id": 1
            }
            r = requests.post(zabbix_url, json=payload, timeout=10)
            r.raise_for_status()
            auth = r.json().get('result')
            if not auth:
                return (None, 'NOT OK', None, 'NOT OK', 'Zabbix authentication failed')

            # Get temperature
            payload = {
                "jsonrpc": "2.0",
                "method": "item.get",
                "params": {
                    "output": ["lastvalue"],
                    "host": host,
                    "search": {"key_": temp_key},
                    "sortfield": "name"
                },
                "auth": auth,
                "id": 2
            }
            r = requests.post(zabbix_url, json=payload, timeout=10)
            r.raise_for_status()
            temp_items = r.json().get('result', [])
            temp_value = float(temp_items[0]['lastvalue']) if temp_items else None

            # Get humidity
            payload['params']['search']['key_'] = humidity_key
            r = requests.post(zabbix_url, json=payload, timeout=10)
            r.raise_for_status()
            humidity_items = r.json().get('result', [])
            humidity_value = float(humidity_items[0]['lastvalue']) if humidity_items else None

            # Logout
            requests.post(zabbix_url, json={
                "jsonrpc": "2.0",
                "method": "user.logout",
                "params": [],
                "auth": auth,
                "id": 3
            }, timeout=5)

            # Status logic
            temp_status = 'OK' if temp_value is not None and temp_value < 28 else 'NOT OK'
            humidity_status = 'OK' if humidity_value is not None and 40 <= humidity_value <= 60 else 'NOT OK'
            return (temp_value, temp_status, humidity_value, humidity_status, None)
        except Exception as e:
            return (None, 'NOT OK', None, 'NOT OK', str(e))

    def update_zabbix_data(self):
        """Fetch latest Zabbix temp/humidity and update UI fields"""
        from threading import Thread
        def fetch():
            self.zabbix_loading_label.config(text="Loading Zabbix data...")
            self.refresh_btn.state(["disabled"])
            self.zabbix_config_btn.state(["disabled"])
            temp, temp_status, humidity, humidity_status, error = self.get_zabbix_temp_humidity(
                self.zabbix_config['url'],
                self.zabbix_config['username'],
                self.zabbix_config['password'],
                self.zabbix_config['host'],
                self.zabbix_config['temp_key'],
                self.zabbix_config['humidity_key']
            )
            self.zabbix_data = {
                'temp': temp,
                'temp_status': temp_status,
                'humidity': humidity,
                'humidity_status': humidity_status,
                'error': error
            }
            # Update UI if fields exist
            if hasattr(self, 'zabbix_temp_label'):
                self.zabbix_temp_label.config(text=f"Temperature: {temp if temp is not None else 'N/A'} °C ({temp_status})")
            if hasattr(self, 'zabbix_humidity_label'):
                self.zabbix_humidity_label.config(text=f"Humidity: {humidity if humidity is not None else 'N/A'} % ({humidity_status})")
            if hasattr(self, 'zabbix_error_label'):
                self.zabbix_error_label.config(text=error or "")
            self.zabbix_loading_label.config(text="")
            self.refresh_btn.state(["!disabled"])
            self.zabbix_config_btn.state(["!disabled"])
            # Update dashboard if present, on main thread
            if hasattr(self, 'update_dashboard'):
                self.root.after(0, self.update_dashboard)
        Thread(target=fetch, daemon=True).start()

    def load_zabbix_config(self):
        default = {
            'url': 'http://your-zabbix-server/zabbix/api_jsonrpc.php',
            'username': 'api_user',
            'password': 'api_password',
            'host': 'YourHostName',
            'temp_key': 'sensor.temp',
            'humidity_key': 'sensor.humidity'
        }
        try:
            if os.path.exists(self.zabbix_config_path):
                with open(self.zabbix_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def save_zabbix_config(self):
        try:
            with open(self.zabbix_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.zabbix_config, f, indent=2)
        except Exception as e:
            messagebox.showerror("Config Error", f"Failed to save Zabbix config: {e}")

    def open_zabbix_config_dialog(self):
        """Open a dialog to edit Zabbix config (URL, username, password, host, keys)"""
        config_win = tk.Toplevel(self.root)
        config_win.title("Edit Zabbix Configuration")
        config_win.geometry("440x440")  # Increased height for full button visibility
        # Use the modern theme background
        primary_bg = '#f6fbff'
        card_bg = '#ffffff'
        accent = '#2196f3'
        config_win.configure(bg=primary_bg)
        config_win.grab_set()
        config_win.resizable(False, False)
        # Card frame for modern look
        card = ttk.Frame(config_win, style='Card.TLabelframe', padding=(24, 16))  # Reduced vertical padding
        card.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)
        card.configure(style='Card.TLabelframe')
        fields = [
            ("Zabbix URL", 'url'),
            ("Username", 'username'),
            ("Password", 'password'),
            ("Host", 'host'),
            ("Temperature Key", 'temp_key'),
            ("Humidity Key", 'humidity_key')
        ]
        entries = {}
        for i, (label, key) in enumerate(fields):
            lbl = ttk.Label(card, text=label+":", style='TLabel')
            lbl.grid(row=i, column=0, sticky='e', padx=(0,12), pady=8)
            ent = ttk.Entry(card, width=32, show='*' if key=='password' else None, font=('Segoe UI', 11))
            ent.grid(row=i, column=1, padx=(0,0), pady=8)
            ent.insert(0, str(self.zabbix_config.get(key, '')))
            ent.configure(background=card_bg, foreground='#222e3a')
            entries[key] = ent
        def save():
            for key, ent in entries.items():
                self.zabbix_config[key] = ent.get()
            self.save_zabbix_config()
            config_win.destroy()
            self.update_zabbix_data()
        btn_frame = ttk.Frame(card, style='TFrame')
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=(24,0))
        save_btn = ttk.Button(btn_frame, text="💾 Save", style='Submit.TButton', command=save)
        save_btn.pack(side=tk.LEFT, padx=8, ipadx=16, ipady=6)
        def cancel():
            config_win.destroy()
        cancel_btn = ttk.Button(btn_frame, text="Cancel", style='Clear.TButton', command=cancel)
        cancel_btn.pack(side=tk.LEFT, padx=8, ipadx=16, ipady=6)
        # Remove black bars by setting bg for all direct children
        for widget in config_win.winfo_children():
            try:
                widget.configure(bg=primary_bg)
            except Exception:
                pass
        config_win.update_idletasks()
        x = (self.root.winfo_width() - config_win.winfo_width()) // 2
        y = (self.root.winfo_height() - config_win.winfo_height()) // 2
        config_win.geometry(f"+{self.root.winfo_x() + x}+{self.root.winfo_y() + y}")
        config_win.deiconify()
        config_win.lift()
        config_win.focus_force()

    def create_dashboard_tab(self, parent=None):
        tab = parent or ttk.Frame(self.content_frame, style='TFrame')
        # --- Modern Dashboard Layout ---
        dash_main = ttk.Frame(tab, style='TFrame')
        dash_main.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)

        # Left: Zabbix summary and health summary
        left = ttk.Frame(dash_main, style='TFrame')
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20))

        # Zabbix summary
        zabbix_card = ttk.LabelFrame(left, text='Zabbix Data', style='Card.TLabelframe')
        zabbix_card.pack(fill=tk.X, pady=(0, 16))
        self.dash_zabbix_temp = ttk.Label(zabbix_card, text="Temperature: ...", style='TLabel')
        self.dash_zabbix_temp.pack(side=tk.LEFT, padx=10, pady=8)
        self.dash_zabbix_humidity = ttk.Label(zabbix_card, text="Humidity: ...", style='TLabel')
        self.dash_zabbix_humidity.pack(side=tk.LEFT, padx=10, pady=8)
        self.dash_zabbix_status = ttk.Label(zabbix_card, text="", style='TLabel')
        self.dash_zabbix_status.pack(side=tk.LEFT, padx=10, pady=8)

        # Health check summary
        summary_card = ttk.LabelFrame(left, text="Today's Health Check Summary", style='Card.TLabelframe')
        summary_card.pack(fill=tk.X, pady=(0, 16))
        self.dash_ok_label = ttk.Label(summary_card, text="OK: ...", style='TLabel')
        self.dash_ok_label.pack(side=tk.LEFT, padx=10, pady=8)
        self.dash_notok_label = ttk.Label(summary_card, text="NOT OK: ...", style='TLabel')
        self.dash_notok_label.pack(side=tk.LEFT, padx=10, pady=8)
        self.dash_total_label = ttk.Label(summary_card, text="Total: ...", style='TLabel')
        self.dash_total_label.pack(side=tk.LEFT, padx=10, pady=8)

        # Pie chart frame
        from tkinter import Frame
        self.dash_pie_frame = Frame(summary_card, bg='white', width=180, height=180)
        self.dash_pie_frame.pack(side=tk.LEFT, padx=20, pady=8)
        self.dash_pie_canvas = None  # Will hold the matplotlib canvas

        # --- Calendar for month overview ---
        from tkcalendar import Calendar
        self.dash_calendar = Calendar(left, selectmode='none', date_pattern='yyyy-mm-dd')
        self.dash_calendar.pack(fill=tk.X, pady=(0, 16))
        self.update_dashboard_calendar()  # Populate calendar colors

        # Right: Per-check status
        right = ttk.LabelFrame(dash_main, text="Per-Check Status", style='Card.TLabelframe')
        right.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 0), ipadx=10, ipady=10)
        self.dash_check_status_frame = ttk.Frame(right, style='TFrame')
        self.dash_check_status_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Refresh button
        dash_refresh_btn = ttk.Button(left, text="⟳ Refresh Dashboard", style='Report.TButton', command=self.update_dashboard)
        dash_refresh_btn.pack(pady=(10, 0), anchor='w')
        ToolTip(dash_refresh_btn, "Refresh all dashboard data (Zabbix and health checks)")

        # --- Username display at bottom left ---
        # Place a label at the bottom left of the main window showing the username
        if hasattr(self, 'username') and self.username:
            self.username_label = ttk.Label(self.root, text=f"Logged in as: {self.username}", style='TLabel', anchor='w', foreground='#555')
            self.username_label.place(relx=0.0, rely=1.0, anchor='sw', x=10, y=-5)

        # Initial update
        self.update_dashboard()

    def update_dashboard(self):
        """Update the dashboard widgets with latest data"""
        try:
            # --- Update Zabbix Data ---
            temp, temp_status, humidity, humidity_status, error = self.get_zabbix_temp_humidity(
                self.zabbix_config['url'],
                self.zabbix_config['username'],
                self.zabbix_config['password'],
                self.zabbix_config['host'],
                self.zabbix_config['temp_key'],
                self.zabbix_config['humidity_key']
            )
            self.zabbix_data = {
                'temp': temp,
                'temp_status': temp_status,
                'humidity': humidity,
                'humidity_status': humidity_status,
                'error': error
            }

            # Update Zabbix summary labels
            if hasattr(self, 'dash_zabbix_temp'):
                self.dash_zabbix_temp.config(text=f"Temperature: {temp if temp is not None else 'N/A'} °C")
            if hasattr(self, 'dash_zabbix_humidity'):
                self.dash_zabbix_humidity.config(text=f"Humidity: {humidity if humidity is not None else 'N/A'} %")
            if hasattr(self, 'dash_zabbix_status'):
                if error:
                    self.dash_zabbix_status.config(text="Error fetching data", foreground='red')
                else:
                    self.dash_zabbix_status.config(text="Data OK", foreground='green')

            # --- Update Health Check Summary ---
            today_table_name = self.generate_table_name()
            self.current_day_table = today_table_name  # Ensure current_day_table is always up-to-date

            # Check if today's table exists
            table_exists = self.check_for_existing_day_table()
            if not table_exists:
                # If no table for today, reset summary labels
                self.dash_ok_label.config(text="OK: 0")
                self.dash_notok_label.config(text="NOT OK: 0")
                self.dash_total_label.config(text="Total: 0")
                # Clear pie chart if present
                if hasattr(self, 'dash_pie_canvas') and self.dash_pie_canvas:
                    self.dash_pie_canvas.get_tk_widget().destroy()
                    self.dash_pie_canvas = None
                return  # No data to display yet

            # Fetch today's health check data
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"SELECT * FROM {today_table_name}")
            health_data = cursor.fetchall()
            cursor.close()
            conn.close()

            # Update health check summary labels
            total_checks = len(health_data)
            ok_checks = sum(1 for r in health_data if r['status'] == "OK")
            not_ok_checks = total_checks - ok_checks
            self.dash_ok_label.config(text=f"OK: {ok_checks}")
            self.dash_notok_label.config(text=f"NOT OK: {not_ok_checks}")
            self.dash_total_label.config(text=f"Total: {total_checks}")

            # --- Update Pie Chart ---
            try:
                import matplotlib
                matplotlib.use('Agg')  # Use non-interactive backend
                import matplotlib.pyplot as plt
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                # Remove previous pie chart if exists
                if hasattr(self, 'dash_pie_canvas') and self.dash_pie_canvas:
                    self.dash_pie_canvas.get_tk_widget().destroy()
                    self.dash_pie_canvas = Non e
                # Only show if there are checks
                if total_checks > 0:
                    fig, ax = plt.subplots(figsize=(2.2, 2.2), dpi=80)
                    labels = ['OK', 'NOT OK']
                    sizes = [ok_checks, not_ok_checks]
                    colors = ['#4CAF50', '#F44336']
                    explode = (0.05, 0.05) if not_ok_checks > 0 else (0.05, 0)
                    ax.pie(sizes, labels=labels, autopct='%1.0f%%', startangle=90, colors=colors, explode=explode, textprops={'fontsize': 10})
                    ax.axis('equal')
                    fig.tight_layout(pad=0.5)
                    self.dash_pie_canvas = FigureCanvasTkAgg(fig, master=self.dash_pie_frame)
                    self.dash_pie_canvas.draw()
                    self.dash_pie_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                    plt.close(fig)
            except ImportError:
                # matplotlib not installed
                if hasattr(self, 'dash_pie_canvas') and self.dash_pie_canvas:
                    self.dash_pie_canvas.get_tk_widget().destroy()
                    self.dash_pie_canvas = None

            # --- Update Calendar ---
            if hasattr(self, 'dash_calendar'):
                self.update_dashboard_calendar()

            # --- Update Per-Check Status ---
            for widget in self.dash_check_status_frame.winfo_children():
                widget.destroy()  # Clear existing widgets

            # Group by check name
            check_groups = {}
            for record in health_data:
                check_name = record['check_name']
                if check_name not in check_groups:
                    check_groups[check_name] = []
                check_groups[check_name].append(record)

            # Create a frame for each check
            for check_name, records in check_groups.items():
                group_frame = ttk.Frame(self.dash_check_status_frame, style='TFrame')
                group_frame.pack(fill=tk.X, pady=8)

                # Determine if all OK or any NOT OK
                all_ok = all(r['status'] == 'OK' for r in records)
                label_fg = '#4CAF50' if all_ok else '#F44336'
                # Check name label in green if all OK, red if any NOT OK
                check_label = ttk.Label(group_frame, text=check_name, style='TLabel', foreground=label_fg)
                check_label.pack(side=tk.TOP, anchor='w')

                # Do not show reason and notes for NOT OK in dashboard per-check status
                # (Intentionally left blank as per user request)

        except Exception as e:
            print(f"[ERROR] Updating dashboard failed: {e}")
            messagebox.showerror("Update Error", f"Error updating dashboard: {e}", parent=self.root)

    def update_dashboard_calendar(self):
        """Update the dashboard calendar to highlight days with problems in red."""
        import calendar as pycalendar
        from datetime import datetime
        try:
            # Clear all previous tags
            self.dash_calendar.calevent_remove('all')
            # Get current month/year
            year = self.dash_calendar.selection_get().year if self.dash_calendar.selection_get() else datetime.now().year
            month = self.dash_calendar.selection_get().month if self.dash_calendar.selection_get() else datetime.now().month
            # For each day in month, check for NOT OK
            for day in range(1, pycalendar.monthrange(year, month)[1] + 1):
                table_name = f"health_check_{year}{month:02d}{day:02d}"
                try:
                    conn = mysql.connector.connect(**self.db_config)
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                    if cursor.fetchone():
                        cursor.execute(f"SELECT status FROM {table_name}")
                        statuses = [row['status'] for row in cursor.fetchall()]
                        if any(s != 'OK' for s in statuses):
                            # Mark this day as red
                            date_str = f"{year}-{month:02d}-{day:02d}"
                            self.dash_calendar.calevent_create(datetime(year, month, day), 'Problem', 'problem')
                    cursor.close()
                    conn.close()
                except Exception:
                    pass
            self.dash_calendar.tag_config('problem', background='red', foreground='white')
        except Exception as e:
            print(f"[ERROR] Calendar update failed: {e}")
if __name__ == "__main__":
    def start_main_app(username):
        login_root.destroy()
        main_root = tk.Tk()
        app = HealthCheckApp(main_root, username=username)
        main_root.mainloop()

    # Show login window first
    login_root = tk.Tk()
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '123456',
        'database': 'health_checks_db'
    }
    # Ensure users table exists before login
    try:
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config['database']}")
        conn.commit()
        conn.database = db_config['database']
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(128) NOT NULL
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as err:
        messagebox.showerror("Database Error", f"Error initializing database: {err}")

    login_app = LoginWindow(login_root, db_config, on_success=start_main_app)
    login_root.mainloop()
