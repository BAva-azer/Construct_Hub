from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

# ===== DATABASE HELPERS =====
def get_db():
    """Connect to database"""
    return sqlite3.connect("database.db")

def query(sql, params=()):
    """Execute query and return results"""
    conn = get_db()
    c = conn.cursor()
    c.execute(sql, params)
    result = c.fetchall()
    conn.close()
    return result

def execute(sql, params=()):
    """Execute command and save to database"""
    conn = get_db()
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    conn.close()

def init_db():
    """Create tables and add initial data"""
    # Create users table
    execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT, password TEXT,
        role TEXT DEFAULT 'user')""")

    # Add admin if not exists
    if not query("SELECT 1 FROM users WHERE email=?", ("constructhub@gmail.com",)):
        execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                ("Admin", "constructhub@gmail.com", "construct@hub", "admin"))

    # Create products table
    execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, price INTEGER)""")

    # Add sample products if empty
    if not query("SELECT 1 FROM products"):
        products = [
            ("High-Quality Cement", 500), ("Steel Rebars", 1200),
            ("Concrete Blocks", 300), ("Sand (per ton)", 800),
            ("Bricks (per 1000)", 2500), ("Paint (5L)", 1500)
        ]
        for name, price in products:
            execute("INSERT INTO products(name, price) VALUES(?, ?)", (name, price))

    # Create orders table
    execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, address TEXT, payment TEXT,
        status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id))""")

    # Create order_items table for individual product assignments
    execute("""CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER, product_id INTEGER, quantity INTEGER,
        supplier_id INTEGER, supplier_status TEXT DEFAULT 'not_assigned',
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (product_id) REFERENCES products (id),
        FOREIGN KEY (supplier_id) REFERENCES users (id))""")

init_db()

# ===== USER ROUTES =====
@app.route("/signup", methods=["POST"])
def signup():
    """Create new user account"""
    data = request.json
    role = data.get("role", "user")  # Default role is 'user'
    execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
            (data["name"], data["email"], data["password"], role))
    return "Signup successful"

@app.route("/supplier/signup", methods=["POST"])
def supplier_signup():
    """Create new supplier account"""
    data = request.json
    execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
            (data["name"], data["email"], data["password"], "supplier"))
    return "Supplier signup successful"

@app.route("/login", methods=["POST"])
def login():
    """Login user and return user info"""
    data = request.json
    user = query("SELECT * FROM users WHERE email=? AND password=?",
                 (data["email"], data["password"]))

    if user:
        u = user[0]
        return jsonify({"success": True, "user": {"id": u[0], "name": u[1], "role": u[4]}})
    return jsonify({"success": False})

# ===== PRODUCT ROUTES =====
@app.route("/products")
def products():
    """Get all products"""
    data = query("SELECT * FROM products")
    return jsonify([{"id": p[0], "name": p[1], "price": p[2]} for p in data])

# ===== ORDER ROUTES =====
@app.route("/user/orders")
def user_orders():
    """Get user's orders"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "User ID required"}), 400

    orders = query("SELECT id, address, payment, status FROM orders WHERE user_id=?", (user_id,))
    
    result = []
    for order in orders:
        order_id = order[0]
        # Get items in this order
        items = query("""
            SELECT products.id, products.name, products.price, order_items.quantity, order_items.supplier_status
            FROM order_items
            JOIN products ON order_items.product_id = products.id
            WHERE order_items.order_id = ?
        """, (order_id,))
        
        result.append({
            "id": order_id,
            "items": [{"id": item[0], "name": item[1], "price": item[2], "quantity": item[3], "supplier_status": item[4]} for item in items],
            "address": order[1],
            "payment": order[2],
            "status": order[3]
        })
    
    return jsonify(result)

@app.route("/order", methods=["POST"])
def create_order():
    """Place a new order and create individual order items"""
    data = request.json
    user_id = data["user"]["id"]
    cart = data["cart"]
    address = data["address"]
    payment = str(data.get("payment", {}))

    # Create the order
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO orders(user_id, address, payment, status) VALUES(?,?,?,?)",
              (user_id, address, payment, "pending"))
    order_id = c.lastrowid
    conn.commit()

    # Create individual order items
    if isinstance(cart, list):
        for item in cart:
            c.execute("INSERT INTO order_items(order_id, product_id, quantity) VALUES(?,?,?)",
                      (order_id, item["id"], item["quantity"]))
            conn.commit()

    conn.close()
    return "Order placed successfully"

# ===== ADMIN ROUTES =====
@app.route("/admin/orders")
def admin_orders():
    """Get all orders with their items for admin"""
    try:
        orders = query("""
            SELECT orders.id, users.name, users.email, orders.address, orders.payment,
                   orders.status
            FROM orders JOIN users ON orders.user_id = users.id
            ORDER BY orders.id DESC
        """)

        result = []
        for order in orders:
            order_id = order[0]

            # Get order items with supplier info
            items = query("""
                SELECT order_items.id, products.name, products.price, order_items.quantity,
                       order_items.supplier_id, order_items.supplier_status,
                       COALESCE(suppliers.name, 'Unassigned') as supplier_name
                FROM order_items
                JOIN products ON order_items.product_id = products.id
                LEFT JOIN users as suppliers ON order_items.supplier_id = suppliers.id
                WHERE order_items.order_id = ?
            """, (order_id,))

            result.append({
                "id": order[0],
                "user": {"name": order[1], "email": order[2]},
                "address": order[3],
                "payment": order[4],
                "status": order[5],
                "items": [{
                    "id": item[0],
                    "name": item[1],
                    "price": item[2],
                    "quantity": item[3],
                    "supplier_id": item[4],
                    "supplier_status": item[5],
                    "supplier_name": item[6]
                } for item in items]
            })

        return jsonify(result)
    except Exception as e:
        print(f"Error in admin_orders: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/admin/suppliers")
def get_suppliers():
    """Get all suppliers for assignment"""
    suppliers = query("SELECT id, name, email FROM users WHERE role=?", ("supplier",))
    return jsonify([{"id": s[0], "name": s[1], "email": s[2]} for s in suppliers])

@app.route("/admin/approve/<int:order_id>", methods=["POST"])
def approve_order(order_id):
    """Approve order"""
    execute("UPDATE orders SET status=? WHERE id=?", ("approved", order_id))
    return "Order approved"

@app.route("/admin/assign-product-supplier", methods=["POST"])
def assign_product_supplier():
    """Assign a specific product in an order to a supplier"""
    data = request.json
    order_item_id = data["order_item_id"]
    supplier_id = data["supplier_id"]

    execute("UPDATE order_items SET supplier_id=?, supplier_status=? WHERE id=?",
            (supplier_id, "pending_approval", order_item_id))

    # Check if all items in the order are assigned
    order_id = query("SELECT order_id FROM order_items WHERE id=?", (order_item_id,))[0][0]
    unassigned_count = query("SELECT COUNT(*) FROM order_items WHERE order_id=? AND supplier_id IS NULL", (order_id,))[0][0]

    if unassigned_count == 0:
        execute("UPDATE orders SET status=? WHERE id=?", ("approved", order_id))

    return "Product assigned to supplier"

@app.route("/admin/reject/<int:order_id>", methods=["POST"])
def reject_order(order_id):
    """Reject order"""
    execute("UPDATE orders SET status=? WHERE id=?", ("rejected", order_id))
    return "Order rejected"

@app.route("/admin/ship/<int:order_id>", methods=["POST"])
def ship_order(order_id):
    """Ship order and send email"""
    execute("UPDATE orders SET status=? WHERE id=?", ("shipped", order_id))

    user_email = query("""SELECT users.email FROM orders
                          JOIN users ON orders.user_id = users.id
                          WHERE orders.id=?""", (order_id,))

    if user_email:
        print(f"Email: Order #{order_id} shipped to {user_email[0][0]}")
        return "Order shipped and email sent"
    return "Order shipped"

# ===== SUPPLIER ROUTES =====
@app.route("/supplier/orders")
def supplier_orders():
    """Get order items assigned to supplier"""
    supplier_id = request.args.get('supplier_id')
    if not supplier_id:
        return jsonify({"error": "Supplier ID required"}), 400

    items = query("""
        SELECT order_items.id, orders.id as order_id, products.name, products.price,
               order_items.quantity, orders.address, orders.payment,
               order_items.supplier_status, users.name as customer_name, users.email as customer_email
        FROM order_items
        JOIN orders ON order_items.order_id = orders.id
        JOIN products ON order_items.product_id = products.id
        JOIN users ON orders.user_id = users.id
        WHERE order_items.supplier_id = ? AND order_items.supplier_status != 'shipped'
        ORDER BY orders.created_at DESC
    """, (supplier_id,))

    return jsonify([{
        "item_id": item[0],
        "order_id": item[1],
        "product_name": item[2],
        "price": item[3],
        "quantity": item[4],
        "address": item[5],
        "payment": item[6],
        "supplier_status": item[7],
        "customer": {"name": item[8], "email": item[9]}
    } for item in items])

@app.route("/supplier/approve/<int:item_id>", methods=["POST"])
def supplier_approve(item_id):
    """Supplier approves order item for delivery"""
    execute("UPDATE order_items SET supplier_status=? WHERE id=?",
            ("approved", item_id))
    return "Item approved by supplier"

@app.route("/supplier/reject/<int:item_id>", methods=["POST"])
def supplier_reject(item_id):
    """Supplier rejects order item"""
    data = request.json
    reason = data.get("reason", "No reason provided")
    execute("UPDATE order_items SET supplier_status=? WHERE id=?",
            ("rejected", item_id))
    print(f"Item #{item_id} rejected by supplier. Reason: {reason}")
    return "Item rejected by supplier"

@app.route("/supplier/ship/<int:item_id>", methods=["POST"])
def supplier_ship(item_id):
    """Supplier ships order item"""
    execute("UPDATE order_items SET supplier_status=? WHERE id=?",
            ("shipped", item_id))

    # Check if all items in the order are shipped
    order_id = query("SELECT order_id FROM order_items WHERE id=?", (item_id,))[0][0]
    pending_count = query("SELECT COUNT(*) FROM order_items WHERE order_id=? AND supplier_status != 'shipped'", (order_id,))[0][0]

    if pending_count == 0:
        execute("UPDATE orders SET status=? WHERE id=?", ("shipped_by_supplier", order_id))

    user_email = query("""SELECT users.email FROM orders
                          JOIN users ON orders.user_id = users.id
                          WHERE orders.id=?""", (order_id,))

    if user_email:
        print(f"Email: Item #{item_id} shipped by supplier to {user_email[0][0]}")
        return "Item shipped by supplier and email sent"
    return "Item shipped by supplier"

if __name__ == "__main__":
    print("\n" + "="*60)
    print("✓ Construct Hub Backend Server")
    print("✓ Running on: http://localhost:5000")
    print("✓ Press Ctrl+C to stop")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)