from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
import os
from dotenv import load_dotenv  # Ensure this is imported if using a .env file

# Load environment variables from .env file (if using .env)
load_dotenv()

app = Flask(__name__, template_folder="templates")  # Make sure this is before any @app.route()
app.secret_key = "buVJyxLGE2GRjV"

# Database connection function
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname="RAD_IT",
            user="postgres",
            password=os.getenv("DB_PASSWORD"),  # Get password from .env file
            host="localhost"
        )
        print("DEBUG: Database connected successfully")
        return conn
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to the database - {e}")
        return None


# Homepage Route with Debugging
@app.route('/')
def home():
    conn = get_db_connection()
    
    if conn is None:
        return "Database connection failed. Check your credentials and connection."

    cur = conn.cursor()

    # Debugging Message
    print("DEBUG: Fetching homepage statistics...")

    # Fetch total contracts
    cur.execute("SELECT COUNT(*) FROM contracts")
    total_contracts = cur.fetchone()[0] or 0

    # Fetch total suppliers
    cur.execute("SELECT COUNT(*) FROM suppliers")
    total_suppliers = cur.fetchone()[0] or 0

    # Fetch total purchase orders
    cur.execute("SELECT COUNT(*) FROM purchase_orders")
    total_pos = cur.fetchone()[0] or 0

    # Fetch upcoming contract renewals (expiring within the next 90 days)
    cur.execute("""
        SELECT COUNT(*) FROM contracts 
        WHERE end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '90 days'
    """)
    upcoming_renewals = cur.fetchone()[0] or 0

    print(f"DEBUG: Total Contracts: {total_contracts}")
    print(f"DEBUG: Total Suppliers: {total_suppliers}")
    print(f"DEBUG: Total Purchase Orders: {total_pos}")
    print(f"DEBUG: Upcoming Renewals: {upcoming_renewals}")

    cur.close()
    conn.close()

    return render_template('home.html', 
                           total_contracts=total_contracts, 
                           total_suppliers=total_suppliers,
                           total_pos=total_pos,
                           upcoming_renewals=upcoming_renewals)

# View Suppliers
@app.route('/suppliers')
def view_suppliers():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch all suppliers with their primary contact (if available)
    cur.execute("""
        SELECT s.supplier_id, s.name, c.contact_name 
        FROM suppliers s
        LEFT JOIN supplier_contacts c ON s.primary_contact_id = c.contact_id
        ORDER BY s.supplier_id
    """)
    suppliers = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('suppliers.html', suppliers=suppliers)

# View Contracts
@app.route('/contracts')
def view_contracts():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.contract_id, c.contract_name, s.name AS supplier_name, 
               c.start_date, c.end_date, c.value, c.payment_frequency
        FROM contracts c
        JOIN suppliers s ON c.supplier_id = s.supplier_id
        ORDER BY c.end_date
    """)
    contracts = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('contracts.html', contracts=contracts)
    
#View Supplier
@app.route('/view-supplier/<int:supplier_id>')
def view_supplier(supplier_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch supplier details
    cur.execute("SELECT supplier_id, name FROM suppliers WHERE supplier_id = %s", (supplier_id,))
    supplier_row = cur.fetchone()

    # Convert tuple to dictionary
    if supplier_row:
        supplier = {"supplier_id": supplier_row[0], "name": supplier_row[1]}
    else:
        flash("⚠️ Supplier not found!", "warning")
        return redirect(url_for('view_suppliers'))

    # Fetch primary contact details
    cur.execute("""
        SELECT contact_name, email, office_phone, mobile 
        FROM supplier_contacts 
        WHERE contact_id = (SELECT primary_contact_id FROM suppliers WHERE supplier_id = %s)
    """, (supplier_id,))
    primary_contact_row = cur.fetchone()

    primary_contact = (
        {"contact_name": primary_contact_row[0], "email": primary_contact_row[1], 
         "office_phone": primary_contact_row[2], "mobile": primary_contact_row[3]}
        if primary_contact_row else None
    )

    # Fetch all contacts associated with this supplier
    cur.execute("""
        SELECT contact_id, supplier_id, contact_name, email, office_phone, mobile
        FROM supplier_contacts
        WHERE supplier_id = %s
    """, (supplier_id,))
    contacts = [
        {"contact_id": row[0], "supplier_id": row[1], "contact_name": row[2], 
         "email": row[3], "office_phone": row[4], "mobile": row[5]} 
        for row in cur.fetchall()
    ]

    cur.close()
    conn.close()

    return render_template('view_supplier.html', supplier=supplier, primary_contact=primary_contact, contacts=contacts)

# view_suplier_contacts
@app.route('/view-supplier-contacts/<int:supplier_id>')
def view_supplier_contacts(supplier_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch supplier details
    cur.execute("SELECT supplier_id, name FROM suppliers WHERE supplier_id = %s", (supplier_id,))
    supplier_row = cur.fetchone()

    if not supplier_row:
        flash("⚠️ Supplier not found!", "warning")
        return redirect(url_for('view_suppliers'))

    # Convert tuple to dictionary
    supplier = {"supplier_id": supplier_row[0], "name": supplier_row[1]}

    # Fetch all contacts associated with this supplier
    cur.execute("""
        SELECT contact_id, contact_name, email, office_phone, mobile 
        FROM supplier_contacts WHERE supplier_id = %s
    """, (supplier_id,))
    contacts = [
        {"contact_id": row[0], "contact_name": row[1], "email": row[2], "office_phone": row[3], "mobile": row[4]}
        for row in cur.fetchall()
    ]

    cur.close()
    conn.close()

    return render_template('view_supplier_contacts.html', supplier=supplier, contacts=contacts)


#Add new contact
@app.route('/add-supplier-contact/<int:supplier_id>', methods=['POST'])
def add_supplier_contact(supplier_id):
    if request.method == 'POST':
        contact_name = request.form['contact_name']
        email = request.form['email']
        office_phone = request.form.get('office_phone', None)
        mobile = request.form.get('mobile', None)

        conn = get_db_connection()
        cur = conn.cursor()

        # Insert the new contact into supplier_contacts table
        cur.execute("""
            INSERT INTO supplier_contacts (supplier_id, contact_name, email, office_phone, mobile)
            VALUES (%s, %s, %s, %s, %s)
        """, (supplier_id, contact_name, email, office_phone, mobile))

        conn.commit()
        cur.close()
        conn.close()

        flash('✅ Contact added successfully!', 'success')
        return redirect(url_for('view_supplier', supplier_id=supplier_id))
        
        
#Delete contact
@app.route('/delete-contact/<int:contact_id>', methods=['POST'])
def delete_contact(contact_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Find supplier_id before deleting so we can redirect correctly
    cur.execute("SELECT supplier_id FROM supplier_contacts WHERE contact_id = %s", (contact_id,))
    supplier = cur.fetchone()

    if not supplier:
        flash("⚠️ Contact not found!", "warning")
        return redirect(url_for('view_suppliers'))

    supplier_id = supplier[0]

    # Delete the contact
    cur.execute("DELETE FROM supplier_contacts WHERE contact_id = %s", (contact_id,))
    conn.commit()

    cur.close()
    conn.close()

    flash("✅ Contact deleted successfully!", "success")
    return redirect(url_for('view_supplier', supplier_id=supplier_id))
    
# Set primary  contact    
@app.route('/set-primary-contact/<int:contact_id>', methods=['POST'])
def set_primary_contact(contact_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Get supplier_id of the contact
    cur.execute("SELECT supplier_id FROM supplier_contacts WHERE contact_id = %s", (contact_id,))
    supplier = cur.fetchone()

    if not supplier:
        flash("⚠️ Contact not found!", "warning")
        return redirect(url_for('view_suppliers'))

    supplier_id = supplier[0]

    # Update the supplier's primary contact
    cur.execute("UPDATE suppliers SET primary_contact_id = %s WHERE supplier_id = %s", (contact_id, supplier_id))
    conn.commit()

    cur.close()
    conn.close()

    flash("✅ Primary contact updated successfully!", "success")
    return redirect(url_for('view_supplier', supplier_id=supplier_id))





# Add Supplier
@app.route('/add-supplier', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        name = request.form['name']
        contact_name = request.form.get('contact_name', '')
        email = request.form.get('email', '')
        office_phone = request.form.get('office_phone', '')
        mobile = request.form.get('mobile', '')
        address = request.form.get('address', '')

        # Debugging output
        print(f"DEBUG: Name={name}, Contact={contact_name}, Email={email}, Office={office_phone}, Mobile={mobile}, Address={address}")

        conn = get_db_connection()
        cur = conn.cursor()

        # Ensure correct number of placeholders
        cur.execute("""
            INSERT INTO suppliers (name, contact_name, email, office_phone, mobile, address) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, contact_name, email, office_phone, mobile, address))

        conn.commit()
        cur.close()
        conn.close()

        flash('Supplier added successfully!', 'success')
        return redirect(url_for('view_suppliers'))

    return render_template('add_supplier.html')


# Edit Supplier
@app.route('/edit-supplier/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        contact_name = request.form.get('contact_name', '')
        email = request.form.get('email', '')
        office_phone = request.form.get('office_phone', '')
        mobile = request.form.get('mobile', '')
        address = request.form.get('address', '')

        cur.execute("""
            UPDATE suppliers 
            SET name = %s, contact_name = %s, email = %s, office_phone = %s, mobile = %s, address = %s
            WHERE supplier_id = %s
        """, (name, contact_name, email, office_phone, mobile, address, supplier_id))
        conn.commit()
        cur.close()
        conn.close()

        flash('Supplier updated successfully!', 'success')
        return redirect(url_for('view_suppliers'))

    # Fetch supplier details
    cur.execute("SELECT supplier_id, name, contact_name, email, office_phone, mobile, address FROM suppliers WHERE supplier_id = %s", (supplier_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        flash("⚠️ Supplier not found!", "warning")
        return redirect(url_for('view_suppliers'))

    # Convert Tuple to Dictionary
    supplier = {
        "supplier_id": row[0],  
        "name": row[1],         
        "contact_name": row[2], 
        "email": row[3],        
        "office_phone": row[4],  
        "mobile": row[5],       
        "address": row[6],      
    }

    return render_template('edit_supplier.html', supplier=supplier)
    
  
#Add contract  
@app.route('/add-contract', methods=['GET', 'POST'])
def add_contract():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch suppliers to display in the dropdown
    cur.execute("SELECT supplier_id, name FROM suppliers ORDER BY name")
    suppliers = cur.fetchall()

    if request.method == 'POST':
        contract_name = request.form['contract_name']
        supplier_id = request.form['supplier_id']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        value = request.form['value']
        payment_frequency = request.form['payment_frequency']
        terms = request.form.get('terms', '')

        # Insert into the contracts table
        cur.execute("""
            INSERT INTO contracts (contract_name, supplier_id, start_date, end_date, value, payment_frequency, terms) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (contract_name, supplier_id, start_date, end_date, value, payment_frequency, terms))
        conn.commit()

        cur.close()
        conn.close()

        flash('✅ Contract added successfully!', 'success')
        return redirect(url_for('view_contracts'))

    cur.close()
    conn.close()
    return render_template('add_contract.html', suppliers=suppliers)


# Delete Supplier
@app.route('/delete-supplier/<int:supplier_id>')
def delete_supplier(supplier_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM suppliers WHERE supplier_id = %s", (supplier_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    flash('✅ Supplier deleted successfully!', 'success')
    return redirect(url_for('view_suppliers'))

# Delete Contract
@app.route('/delete-contract/<int:contract_id>')
def delete_contract(contract_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM contracts WHERE contract_id = %s", (contract_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash('✅ Contract deleted successfully!', 'success')
    return redirect(url_for('view_contracts'))

# Edit Contract
@app.route('/edit-contract/<int:contract_id>', methods=['GET', 'POST'])
def edit_contract(contract_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    if request.method == 'POST':
        contract_name = request.form['contract_name']
        supplier_id = request.form['supplier_id']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        value = request.form['value']
        payment_frequency = request.form['payment_frequency']
        terms = request.form.get('terms', '')

        cur.execute("""
            UPDATE contracts
            SET contract_name = %s, supplier_id = %s, start_date = %s, end_date = %s, value = %s, payment_frequency = %s, terms = %s
            WHERE contract_id = %s
        """, (contract_name, supplier_id, start_date, end_date, value, payment_frequency, terms, contract_id))
        conn.commit()
        cur.close()
        conn.close()

        flash('✅ Contract updated successfully!', 'success')
        return redirect(url_for('view_contracts'))

    cur.execute("SELECT * FROM contracts WHERE contract_id = %s", (contract_id,))
    contract = cur.fetchone()
    cur.execute("SELECT supplier_id, name FROM suppliers ORDER BY name")
    suppliers = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('edit_contract.html', contract=contract, suppliers=suppliers)
    
@app.route('/purchase-orders')
def view_purchase_orders():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM purchase_orders ORDER BY po_date DESC")
    purchase_orders = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('purchase_orders.html', purchase_orders=purchase_orders)
    
@app.route('/edit-po/<int:po_id>', methods=['GET', 'POST'])
def edit_po(po_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        po_number = request.form['po_number']
        contract_id = request.form['contract_id'] or None
        po_date = request.form['po_date']
        amount = request.form['amount']
        requester = request.form['requester']
        approver = request.form.get('approver', None)
        status = request.form['status']

        cur.execute("""
            UPDATE purchase_orders
            SET po_number = %s, contract_id = %s, po_date = %s, amount = %s, requester = %s, approver = %s, status = %s
            WHERE po_id = %s
        """, (po_number, contract_id, po_date, amount, requester, approver, status, po_id))
        conn.commit()
        cur.close()
        conn.close()

        flash('✅ Purchase Order updated successfully!', 'success')
        return redirect(url_for('view_purchase_orders'))

    cur.execute("SELECT * FROM purchase_orders WHERE po_id = %s", (po_id,))
    po = cur.fetchone()
    cur.close()
    conn.close()

    if not po:
        flash("⚠️ Purchase Order not found!", "warning")
        return redirect(url_for('view_purchase_orders'))

    return render_template('edit_po.html', po=dict(zip(["po_id", "po_number", "contract_id", "po_date", "amount", "requester", "approver", "status"], po)))

@app.route('/delete-po/<int:po_id>')
def delete_po(po_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM purchase_orders WHERE po_id = %s", (po_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    flash('✅ Purchase Order deleted successfully!', 'success')
    return redirect(url_for('view_purchase_orders'))
    
@app.route('/add-po', methods=['GET', 'POST'])
def add_po():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch existing contracts and suppliers for dropdown selections
    cur.execute("SELECT contract_id, contract_name FROM contracts ORDER BY contract_name")
    contracts = cur.fetchall()

    cur.execute("SELECT supplier_id, name FROM suppliers ORDER BY name")
    suppliers = cur.fetchall()

    if request.method == 'POST':
        contract_id = request.form.get('contract_id') or None
        po_number = request.form['po_number']
        po_date = request.form['po_date']
        amount = request.form['amount']
        requester = request.form['requester']
        approver = request.form.get('approver', None)
        status = request.form['status']

        # Insert into the purchase_orders table
        cur.execute("""
            INSERT INTO purchase_orders (contract_id, po_number, po_date, amount, requester, approver, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (contract_id, po_number, po_date, amount, requester, approver, status))
        conn.commit()

        cur.close()
        conn.close()

        flash('✅ Purchase Order added successfully!', 'success')
        return redirect(url_for('view_purchase_orders'))

    cur.close()
    conn.close()
    return render_template('add_po.html', contracts=contracts, suppliers=suppliers)


if __name__ == '__main__':
    print("Running Flask App...")
    app.run(debug=True)
