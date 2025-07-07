import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import mysql.connector
from datetime import datetime
import csv
import os

class HealthCheckApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Health Monitor")
        self.root.geometry("1000x800")
        self.root.configure(bg="#99ff00")
        
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
        
        self.initialize_database()
        self.create_widgets()
        self.update_clock()
    
    def configure_styles(self):
        """Configure custom styles for widgets"""
        self.style.configure('TFrame', background="#6d6d6d")
        self.style.configure('TLabel', background="#bebebe", font=('Segoe UI', 10))
        self.style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'), foreground="#818181")
        self.style.configure('Check.TCheckbutton', font=('Segoe UI', 10), background='#f0f8ff')
        self.style.configure('Submit.TButton', font=('Segoe UI', 12), background='#3498db', foreground='white')
        self.style.configure('Clear.TButton', font=('Segoe UI', 12), background='#e74c3c', foreground='white')
        self.style.configure('Export.TButton', font=('Segoe UI', 12), background='#2ecc71', foreground='white')
        self.style.map('Submit.TButton',
                      background=[('active', '#2980b9'), ('pressed', '#1c6ca8')])
        self.style.map('Clear.TButton',
                      background=[('active', '#c0392b'), ('pressed', '#a93226')])
        self.style.map('Export.TButton',
                      background=[('active', '#27ae60'), ('pressed', '#219653')])
    
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
    
    def create_widgets(self):
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
       
        self.create_check_form_tab()
        
        
        self.create_view_tables_tab()
    
    def create_check_form_tab(self):
        tab1 = ttk.Frame(self.notebook, style='TFrame')
        self.notebook.add(tab1, text="Health Check")
        
        
        header_frame = ttk.Frame(tab1, style='TFrame')
        header_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Application title
        title_label = ttk.Label(header_frame, text="System Health Monitor", style='Title.TLabel')
        title_label.pack(side=tk.LEFT)
        
        # Clock label (right-aligned)
        self.clock_label = ttk.Label(header_frame, style='TLabel')
        self.clock_label.pack(side=tk.RIGHT)
        
        # Main content frame
        main_frame = ttk.Frame(tab1, style='TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Checkboxes frame with canvas and scrollbar
        canvas = tk.Canvas(main_frame, bg="#6e6e6e", highlightthickness=0)
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
                highlightbackground="#FF0000",
                highlightthickness=1
            )
            reason_text.pack(fill=tk.X)
            self.reason_entries.append(reason_text)
            
            
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
                highlightbackground="#c4c4c4",
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
        self.tables_tree = ttk.Treeview(content_frame, columns=('name'), show='headings')
        self.tables_tree.heading('name', text='Table Name')
        
        self.tables_tree.column('name', width=300)
        
        
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
        export_btn.pack(pady=5, ipadx=10, ipady=3)
        
        # Load tables initially
        self.refresh_tables_list()
    
    def refresh_tables_list(self):
        """Refresh the list of tables in the database"""
        self.tables_tree.delete(*self.tables_tree.get_children())
        
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall() if table[0].startswith('health_check_')]
            
            # Get record count for each table
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                self.tables_tree.insert('', 'end', values=(table, count))
            
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
        """Generate a unique table name based on current timestamp"""
        now = datetime.now()
        return f"health_check_{now.strftime('%Y%m%d_%H%M%S')}"
    
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
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        table_name = self.generate_table_name()
        if not self.create_new_table(table_name):
            return
        
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
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
                    f"""INSERT INTO {table_name} 
                    (check_name, status, reason, notes) 
                    VALUES (%s, %s, %s, %s)""",
                    (label, status, reason, notes)
                )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            messagebox.showinfo(
                "Success", 
                f"Health check saved to new table: {table_name}",
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
            
            
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            
            
            deleted_count = 0
            for table in tables:
                if table.startswith('health_check_'):
                    cursor.execute(f"DROP TABLE {table}")
                    deleted_count += 1
            
            conn.commit()
            cursor.close()
            conn.close()
            
            messagebox.showinfo(
                "Success", 
                f"Deleted {deleted_count} health check tables",
                parent=self.root
            )
            
            
            self.refresh_tables_list()
            
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Error clearing database: {err}")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.iconbitmap('health_icon.ico')
    except:
        pass
    app = HealthCheckApp(root)
    root.mainloop()
