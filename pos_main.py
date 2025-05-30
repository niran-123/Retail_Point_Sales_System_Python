import tkinter as tk
from tkinter import messagebox
import mysql.connector
from flask import Flask, request, jsonify
import threading

# ========================== DATABASE MODULE ==========================
class DatabaseManager:
    def __init__(self):
        self.conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="pos_db"
        )
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100),
                price DECIMAL(10,2),
                stock INT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_id INT,
                quantity INT,
                total_price DECIMAL(10,2),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        self.conn.commit()

        self.cursor.execute("SELECT COUNT(*) FROM products")
        count = self.cursor.fetchone()[0]
        if count == 0:
            default_products = [
                ("Notebook", 30.00, 50),
                ("Pen", 10.00, 100),
                ("Pencil", 5.00, 120),
                ("Eraser", 3.00, 80),
                ("Stapler", 45.00, 25)
            ]
            for name, price, stock in default_products:
                self.add_product(name, price, stock)

    def add_product(self, name, price, stock):
        self.cursor.execute("INSERT INTO products (name, price, stock) VALUES (%s, %s, %s)", (name, price, stock))
        self.conn.commit()

    def update_stock(self, product_id, quantity):
        self.cursor.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (quantity, product_id))
        self.conn.commit()

    def record_sale(self, product_id, quantity, total_price):
        self.cursor.execute("INSERT INTO sales (product_id, quantity, total_price) VALUES (%s, %s, %s)",
                            (product_id, quantity, total_price))
        self.conn.commit()

    def get_products(self):
        self.cursor.execute("SELECT * FROM products")
        return self.cursor.fetchall()

    def get_sales(self):
        self.cursor.execute("SELECT * FROM sales")
        return self.cursor.fetchall()

# ========================== FLASK API ==========================
app = Flask(__name__)
db = DatabaseManager()

@app.route("/products", methods=["GET"])
def get_products():
    products = db.get_products()
    return jsonify(products)

@app.route("/sales", methods=["GET"])
def get_sales():
    sales = db.get_sales()
    return jsonify(sales)

@app.route("/sale", methods=["POST"])
def make_sale():
    data = request.json
    product_id = data['product_id']
    quantity = data['quantity']
    total_price = data['total_price']
    db.update_stock(product_id, quantity)
    db.record_sale(product_id, quantity, total_price)
    return jsonify({"message": "Sale recorded."})

# ========================== TKINTER INTERFACE ==========================
class POSInterface:
    def __init__(self, root, db_manager):
        self.root = root
        self.db = db_manager
        self.root.title("🛒 Point of Sale (POS) System")
        self.root.geometry("500x700")
        self.root.configure(bg="#f0f8ff")  # light blue background

        # Title Label
        title = tk.Label(root, text="Retail POS System", font=("Arial", 20, "bold"), bg="#f0f8ff", fg="#004080")
        title.pack(pady=10)

        # Product List Frame
        list_frame = tk.Frame(root, bg="#f0f8ff")
        list_frame.pack(pady=10)

        scrollbar = tk.Scrollbar(list_frame)
        self.product_list = tk.Listbox(list_frame, width=60, height=10, yscrollcommand=scrollbar.set, font=("Arial", 10))
        scrollbar.config(command=self.product_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.product_list.pack(side=tk.LEFT)

        # Input Frame
        input_frame = tk.Frame(root, bg="#f0f8ff")
        input_frame.pack(pady=10)

        self._create_label_entry(input_frame, "Product Name:", "name_entry")
        self._create_label_entry(input_frame, "Price:", "price_entry")
        self._create_label_entry(input_frame, "Stock:", "stock_entry")
        self._create_label_entry(input_frame, "Quantity to Sell:", "quantity_entry")

        # Button Frame
        button_frame = tk.Frame(root, bg="#f0f8ff")
        button_frame.pack(pady=20)

        self._create_button(button_frame, "Sell", self.process_sale, "#28a745")
        self._create_button(button_frame, "Add New Product", self.add_product, "#007bff")
        self._create_button(button_frame, "Update Selected Product", self.update_product, "#ffc107", fg="black")
        self._create_button(button_frame, "Delete Selected Product", self.delete_product, "#dc3545")
        self._create_button(button_frame, "Show Sales History", self.show_sales, "#17a2b8")

        self.refresh_products()

    def _create_label_entry(self, frame, text, attr_name):
        label = tk.Label(frame, text=text, bg="#f0f8ff", font=("Arial", 10))
        label.pack()
        entry = tk.Entry(frame, font=("Arial", 10))
        entry.pack(pady=5)
        setattr(self, attr_name, entry)

    def _create_button(self, frame, text, command, bg_color, fg="white"):
        button = tk.Button(frame, text=text, command=command, bg=bg_color, fg=fg,
                           font=("Arial", 10, "bold"), width=25, pady=5)
        button.pack(pady=5)

    def refresh_products(self):
        self.product_list.delete(0, tk.END)
        products = self.db.get_products()
        for product in products:
            self.product_list.insert(tk.END, f"{product[0]} - {product[1]} - ${product[2]} - Stock: {product[3]}")

    def add_product(self):
        name = self.name_entry.get()
        try:
            price = float(self.price_entry.get())
            stock = int(self.stock_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Enter valid price and stock")
            return
        if not name:
            messagebox.showerror("Error", "Enter product name")
            return
        self.db.add_product(name, price, stock)
        messagebox.showinfo("Success", "Product added successfully")
        self.refresh_products()

    def update_product(self):
        selected = self.product_list.curselection()
        if not selected:
            messagebox.showwarning("Warning", "No product selected to update")
            return

        product_data = self.product_list.get(selected[0]).split(" - ")
        product_id = int(product_data[0])

        try:
            new_price = float(self.price_entry.get())
            new_stock = int(self.stock_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Enter valid price and stock to update")
            return

        self.db.cursor.execute("UPDATE products SET price = %s, stock = %s WHERE id = %s",
                               (new_price, new_stock, product_id))
        self.db.conn.commit()
        messagebox.showinfo("Updated", "Product updated successfully!")
        self.refresh_products()

    def delete_product(self):
        selected = self.product_list.curselection()
        if not selected:
            messagebox.showwarning("Warning", "No product selected to delete")
            return

        product_data = self.product_list.get(selected[0]).split(" - ")
        product_id = int(product_data[0])

        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this product?")
        if confirm:
            self.db.cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            self.db.conn.commit()
            messagebox.showinfo("Deleted", "Product deleted successfully!")
            self.refresh_products()

    def process_sale(self):
        selected = self.product_list.curselection()
        if not selected:
            messagebox.showwarning("Warning", "No product selected")
            return

        product_data = self.product_list.get(selected[0]).split(" - ")
        product_id = int(product_data[0])
        price = float(product_data[2].replace("$", ""))

        try:
            quantity = int(self.quantity_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Enter a valid quantity")
            return

        self.db.update_stock(product_id, quantity)
        self.db.record_sale(product_id, quantity, price * quantity)
        messagebox.showinfo("Success", "Sale processed")
        self.refresh_products()

    def show_sales(self):
        sales = self.db.get_sales()
        if not sales:
            messagebox.showinfo("Sales History", "No sales yet.")
            return
        sale_list = "\n".join([
            f"Sale ID: {sale[0]}, Product ID: {sale[1]}, Qty: {sale[2]}, Total: ${sale[3]}"
            for sale in sales
        ])
        messagebox.showinfo("Sales History", sale_list)

# ========================== FLASK THREAD & MAIN ==========================
def run_api():
    app.run(port=5000)

api_thread = threading.Thread(target=run_api)
api_thread.daemon = True
api_thread.start()

# Run the Tkinter UI
if __name__ == "__main__":
    root = tk.Tk()
    interface = POSInterface(root, db)
    root.mainloop()
