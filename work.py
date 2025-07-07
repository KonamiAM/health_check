import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import mysql.connector
from datetime import datetime, timedelta
import csv
import os
from calendar import monthrange

class HealthCheckApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Health Monitor")
        self.root.geometry("1000x800")
        self.root.configure(bg='#f0f8ff')
        
        # Custom style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()
        
        # Database configuration
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '123456',
            'database': 'health_checks_db'
        }
        
        # Default export directory
        self.export_dir = r"C:\Users\ROG\Documents\dates"
        os.makedirs(self.export_dir, exist_ok=True)
        
        # Current day table name
        self.current_day_table = None
        self.initialize_database()
        self.check_for_existing_day_table()
        self.create_widgets()
        self.update_clock()
    
    def configure_styles(self):
        """Configure custom styles for widgets"""
        self.style.configure('TFrame', background='#f0f8ff')
        self.style.configure('TLabel', background='#f0f8ff', font=('Segoe UI', 10))
        self.style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'), foreground='#2c3e50')
        self.style.configure('Check.TCheckbutton', font=('Segoe UI', 10), background='#f0f8ff')
        self.style.configure('Submit.TButton', font=('Segoe UI', 12), background='#3498db', foreground='white')
        self.style.configure('Clear.TButton', font=('Segoe UI', 12), background='#e74c3c', foreground='white')
        self.style.configure('Export.TButton', font=('Segoe UI', 12), background='#2ecc71', foreground='white')
        self.style.configure('Report.TButton', font=('Segoe UI', 12), background='#9b59b6', foreground='white')
        self.style.map('Submit.TButton',
                      background=[('active', '#2980b9'), ('pressed', '#1c6ca8')])
        self.style.map('Clear.TButton',
                      background=[('active', '#c0392b'), ('pressed', '#a93226')])
        self.style.map('Export.TButton',
                      background=[('active', '#27ae60'), ('pressed', '#219653')])
        self.style.map('Report.TButton',
                      background=[('active', '#8e44ad'), ('pressed', '#7d3c98')])
    
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
        """Check if there's already a table for today's date"""
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
        # Create notebook (tab system)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Health Check Form
        self.create_check_form_tab()
        
        # Tab 2: View Tables
        self.create_view_tables_tab()
        
        # Tab 3: Reports
        self.create_reports_tab()
    
    def create_check_form_tab(self):
        tab1 = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(tab1, text="Health Check")
        
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
        
        # Clear database button
        clear_btn = ttk.Button(
            button_frame, 
            text="Clear All Data", 
            style='Clear.TButton',
            command=self.clear_database
        )
        clear_btn.pack(side=tk.LEFT, padx=10, ipadx=20, ipady=5)
    
    def create_view_tables_tab(self):
        tab2 = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(tab2, text="View Tables")
        
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
        
        # Load tables initially
        self.refresh_tables_list()
    
    def create_reports_tab(self):
        """Create the reports tab"""
        tab3 = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(tab3, text="Reports")
        
        # Header frame
        header_frame = ttk.Frame(tab3, style='TFrame')
        header_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Title
        title_label = ttk.Label(header_frame, text="Generate Reports", style='Title.TLabel')
        title_label.pack(side=tk.LEFT)
        
        # Main content frame
        content_frame = ttk.Frame(tab3, style='TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Report type selection
        report_frame = ttk.LabelFrame(content_frame, text="Select Report Type", style='TFrame')
        report_frame.pack(fill=tk.X, pady=10)
        
        # Daily report button
        daily_btn = ttk.Button(
            report_frame,
            text="Generate Daily Report",
            style='Report.TButton',
            command=lambda: self.generate_report('daily')
        )
        daily_btn.pack(side=tk.LEFT, padx=10, pady=10, ipadx=10, ipady=5)
        
        # Weekly report button
        weekly_btn = ttk.Button(
            report_frame,
            text="Generate Weekly Report",
            style='Report.TButton',
            command=lambda: self.generate_report('weekly')
        )
        weekly_btn.pack(side=tk.LEFT, padx=10, pady=10, ipadx=10, ipady=5)
        
        # Monthly report button
        monthly_btn = ttk.Button(
            report_frame,
            text="Generate Monthly Report",
            style='Report.TButton',
            command=lambda: self.generate_report('monthly')
        )
        monthly_btn.pack(side=tk.LEFT, padx=10, pady=10, ipadx=10, ipady=5)
        
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
        
        # Export report button
        export_report_btn = ttk.Button(
            content_frame,
            text="Export Report to File",
            style='Export.TButton',
            command=self.export_report
        )
        export_report_btn.pack(pady=10, ipadx=10, ipady=3)
    
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
            
            # Write to CSV
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
        """Update the clock label with current date and time"""
        now = datetime.now()
        date_time = now.strftime("%a, %b %d %Y\n%I:%M:%S %p")
        self.clock_label.config(text=date_time)
        self.root.after(1000, self.update_clock)
    
    def generate_table_name(self):
        """Generate a table name based on current date (YYYYMMDD)"""
        now = datetime.now()
        return f"health_check_{now.strftime('%Y%m%d')}"
    
    def create_new_table(self, table_name):
        """Create a new table with the given name"""
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
        """Handle form submission - save to current day's table"""
        if not self.current_day_table:
            self.current_day_table = self.generate_table_name()
            if not self.create_new_table(self.current_day_table):
                return
        
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # First check if we have existing records for today
            cursor.execute(f"SELECT COUNT(*) FROM {self.current_day_table}")
            count = cursor.fetchone()[0]
            
            if count > 0:
                # Update existing records
                for i, (check_var, label, reason_entry, notes_entry) in enumerate(zip(
                    self.check_vars, self.check_labels, self.reason_entries, self.notes_entries
                )):
                    status = "OK" if check_var.get() == 1 else "NOT OK"
                    reason = reason_entry.get("1.0", "end-1c").strip() if status == "NOT OK" else None
                    notes = notes_entry.get("1.0", "end-1c").strip()
                    
                    if status == "NOT OK" and not reason:
                        messagebox.showwarning("Missing Explanation", 
                                             f"Please explain why '{label}' is not functioning")
                        conn.rollback()
                        cursor.close()
                        conn.close()
                        return
                    
                    cursor.execute(
                        f"""UPDATE {self.current_day_table} 
                        SET status = %s, reason = %s, notes = %s, timestamp = CURRENT_TIMESTAMP
                        WHERE check_name = %s""",
                        (status, reason, notes, label))
            else:
                # Insert new records
                for check_var, label, reason_entry, notes_entry in zip(
                    self.check_vars, self.check_labels, self.reason_entries, self.notes_entries
                ):
                    status = "OK" if check_var.get() == 1 else "NOT OK"
                    reason = reason_entry.get("1.0", "end-1c").strip() if status == "NOT OK" else None
                    notes = notes_entry.get("1.0", "end-1c").strip()
                    
                    if status == "NOT OK" and not reason:
                        messagebox.showwarning("Missing Explanation", 
                                             f"Please explain why '{label}' is not functioning")
                        conn.rollback()
                        cursor.close()
                        conn.close()
                        return
                    
                    cursor.execute(
                        f"""INSERT INTO {self.current_day_table} 
                        (check_name, status, reason, notes) 
                        VALUES (%s, %s, %s, %s)""",
                        (label, status, reason, notes)
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
            
            # Switch to view tab and refresh list
            self.notebook.select(1)
            self.refresh_tables_list()
            
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
    
    def generate_report(self, report_type):
        """Generate a report of the specified type (daily, weekly, monthly)"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            
            today = datetime.now().date()
            report_data = []
            report_title = ""
            
            if report_type == 'daily':
                # Daily report - just use today's table
                table_name = f"health_check_{today.strftime('%Y%m%d')}"
                cursor.execute(f"SELECT * FROM {table_name}")
                report_data = cursor.fetchall()
                report_title = f"Daily Health Check Report - {today.strftime('%Y-%m-%d')}"
                
            elif report_type == 'weekly':
                # Weekly report - get data for the past 7 days
                start_date = today - timedelta(days=6)  # 7 days including today
                report_title = f"Weekly Health Check Report - {start_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}"
                
                # Get all tables for the date range
                for single_date in (start_date + timedelta(n) for n in range(7)):
                    table_name = f"health_check_{single_date.strftime('%Y%m%d')}"
                    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                    if cursor.fetchone():
                        cursor.execute(f"SELECT * FROM {table_name}")
                        day_data = cursor.fetchall()
                        for record in day_data:
                            record['date'] = single_date.strftime('%Y-%m-%d')
                            report_data.append(record)
                
            elif report_type == 'monthly':
                # Monthly report - get data for the current month
                year, month = today.year, today.month
                first_day = today.replace(day=1)
                last_day = today.replace(day=monthrange(year, month)[1])
                report_title = f"Monthly Health Check Report - {first_day.strftime('%Y-%m')}"
                
                # Get all tables for the month
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
            
            # Generate the report text
            self.display_report(report_title, report_data, report_type)
            
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error generating report: {err}")
    
    def display_report(self, title, data, report_type):
        """Display the generated report in the text widget"""
        self.report_text.delete(1.0, tk.END)
        
        # Add title
        self.report_text.insert(tk.END, f"{title}\n", 'title')
        self.report_text.insert(tk.END, "=" * len(title) + "\n\n", 'title')
        
        if not data:
            self.report_text.insert(tk.END, "No data available for this report period.\n")
            return
        
        if report_type == 'daily':
            # Daily report format
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
            
            # Add summary
            total_checks = len(data)
            ok_checks = sum(1 for r in data if r['status'] == "OK")
            not_ok_checks = total_checks - ok_checks
            
            self.report_text.insert(tk.END, "\nSUMMARY:\n", 'header')
            self.report_text.insert(tk.END, f"Total checks: {total_checks}\n")
            self.report_text.insert(tk.END, f"Passed: {ok_checks}\n", 'ok')
            self.report_text.insert(tk.END, f"Failed: {not_ok_checks}\n", 'not_ok')
            self.report_text.insert(tk.END, f"Success rate: {ok_checks/total_checks:.1%}\n")
            
        else:
            # Weekly or monthly report format
            # Group by check name and calculate statistics
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
                    check_stats[check_name]['last_reason'] = record['reason']
                    check_stats[check_name]['last_date'] = record['date']
            
            # Display the statistics
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
                    self.report_text.insert(tk.END, stats['last_date'].center(20))
                    self.report_text.insert(tk.END, stats['last_reason'] + "\n", 'reason')
                else:
                    self.report_text.insert(tk.END, "N/A".center(20))
                    self.report_text.insert(tk.END, "N/A\n")
            
            # Add summary
            total_days = len({r['date'] for r in data}) if data else 0
            total_checks = sum(stats['total'] for stats in check_stats.values())
            ok_checks = sum(stats['ok'] for stats in check_stats.values())
            not_ok_checks = total_checks - ok_checks
            
            self.report_text.insert(tk.END, "\nSUMMARY:\n", 'header')
            self.report_text.insert(tk.END, f"Report period covers {total_days} days\n")
            self.report_text.insert(tk.END, f"Total checks performed: {total_checks}\n")
            self.report_text.insert(tk.END, f"Total passed: {ok_checks}\n", 'ok')
            self.report_text.insert(tk.END, f"Total failed: {not_ok_checks}\n", 'not_ok')
            self.report_text.insert(tk.END, f"Overall success rate: {ok_checks/total_checks:.1%}\n")
        
        # Configure text tags for formatting
        self.report_text.tag_config('title', font=('Segoe UI', 14, 'bold'), justify='center')
        self.report_text.tag_config('header', font=('Segoe UI', 10, 'bold'))
        self.report_text.tag_config('ok', foreground='green')
        self.report_text.tag_config('not_ok', foreground='red')
        self.report_text.tag_config('reason', foreground='orange')
    
    def export_report(self):
        """Export the current report to a text file"""
        report_text = self.report_text.get(1.0, tk.END)
        if not report_text.strip():
            messagebox.showwarning("Empty Report", "There is no report to export.")
            return
        
        # Get the first line as default filename
        first_line = report_text.split('\n')[0]
        safe_filename = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in first_line)
        default_filename = os.path.join(self.export_dir, f"{safe_filename}.txt")
        
        # Let user choose location
        file_path = filedialog.asksaveasfilename(
            initialdir=self.export_dir,
            initialfile=f"{safe_filename}.txt",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return  # User cancelled
        
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

if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconbitmap('health_icon.ico')
    except:
        pass
    
    # Configure text widget tags before creating the app
    text = tk.Text()
    text.tag_config('title', font=('Segoe UI', 14, 'bold'), justify='center')
    text.tag_config('header', font=('Segoe UI', 10, 'bold'))
    text.tag_config('ok', foreground='green')
    text.tag_config('not_ok', foreground='red')
    text.tag_config('reason', foreground='orange')
    text.destroy()
    
    app = HealthCheckApp(root)
    root.mainloop()
