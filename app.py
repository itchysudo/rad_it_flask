from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
import os

app = Flask(__name__, template_folder="templates")
app.secret_key = "buVJyxLGE2GRjV"

# Database connection function
def get_db_connection():
    return psycopg2.connect(
        dbname="RAD_IT",
        user="postgres",
        password="Gr33kG0d",  # Need to secure this
        host="localhost"
    )

# Homepage
@app.route('/')
def home():
    return render_template('home.html')

# add supplier Route
@app.route('/add-supplier', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        name = request.form['name']
        contact_name = request.form.get('contact_name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO suppliers (name, contact_name, email, phone, address) 
            VALUES (%s, %s, %s, %s, %s)
        """, (name, contact_name, email, phone, address))
        conn.commit()
        cur.close()
        conn.close()

        flash('✅ Supplier added successfully!', 'success')  # ✅ Flash success message
        return redirect(url_for('view_suppliers'))  # ✅ Redirect to suppliers list

    return render_template('add_supplier.html')

# add contract Route
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
    
    
# add PO route
@app.route('/add-po', methods=['GET', 'POST'])
def add_po():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch existing contracts and suppliers for dropdown selections
    cur.execute("SELECT contract_id, contract_name, value FROM contracts ORDER BY contract_name")
    contracts = cur.fetchall()

    cur.execute("SELECT supplier_id, name FROM suppliers ORDER BY name")
    suppliers = cur.fetchall()

    if request.method == 'POST':
        contract_option = request.form['contract_option']
        contract_id = None

        # Option: Create a new contract if chosen
        if contract_option == "new":
            new_contract_name = request.form['new_contract_name']
            new_supplier_id = request.form['new_supplier_id']
            new_start_date = request.form['new_start_date']
            new_end_date = request.form['new_end_date']
            new_value = request.form['new_value']
            new_payment_frequency = request.form['new_payment_frequency']

            cur.execute("""
                INSERT INTO contracts (contract_name, supplier_id, start_date, end_date, value, payment_frequency) 
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING contract_id
            """, (new_contract_name, new_supplier_id, new_start_date, new_end_date, new_value, new_payment_frequency))
            contract_id = cur.fetchone()[0]  # Get the new contract ID
            conn.commit()

        # Option: Attach to an existing contract if chosen
        elif contract_option == "existing":
            contract_id = request.form['contract_id']

        # For one-off POs (contract_option == "none"), contract_id remains None

        # PO Details
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
        return redirect(url_for('home'))

    cur.close()
    conn.close()
    return render_template('add_po.html', contracts=contracts, suppliers=suppliers)

    
@app.route('/suppliers')
def view_suppliers():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch all suppliers
    cur.execute("SELECT supplier_id, name, contact_name, email, phone, address FROM suppliers ORDER BY name")
    suppliers = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('suppliers.html', suppliers=suppliers)

# Edit supplier    
@app.route('/edit-supplier/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    if request.method == 'POST':
        # Get updated data from the form
        name = request.form['name']
        contact_name = request.form.get('contact_name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')

        # Update supplier record
        cur.execute("""
            UPDATE suppliers 
            SET name = %s, contact_name = %s, email = %s, phone = %s, address = %s
            WHERE supplier_id = %s
        """, (name, contact_name, email, phone, address, supplier_id))
        conn.commit()
        cur.close()
        conn.close()
        
        flash('✅ Supplier updated successfully!', 'success')
        return redirect(url_for('view_suppliers'))
    
    # For GET request, fetch supplier details
    cur.execute("SELECT supplier_id, name, contact_name, email, phone, address FROM suppliers WHERE supplier_id = %s", (supplier_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    # Create a dictionary for easier access in the template
    supplier = {
        'supplier_id': row[0],
        'name': row[1],
        'contact_name': row[2],
        'email': row[3],
        'phone': row[4],
        'address': row[5]
    }
    
    return render_template('edit_supplier.html', supplier=supplier)

# Delete supplier    
@app.route('/delete-supplier/<int:supplier_id>')
def delete_supplier(supplier_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Delete the supplier record
    cur.execute("DELETE FROM suppliers WHERE supplier_id = %s", (supplier_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    flash('✅ Supplier deleted successfully!', 'success')
    return redirect(url_for('view_suppliers'))


    
@app.route('/contracts')
def view_contracts():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch all contracts with supplier names
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
    
    # For GET, fetch the contract data and supplier list
    cur.execute("SELECT contract_id, contract_name, supplier_id, start_date, end_date, value, payment_frequency, terms FROM contracts WHERE contract_id = %s", (contract_id,))
    row = cur.fetchone()
    cur.execute("SELECT supplier_id, name FROM suppliers ORDER BY name")
    suppliers = cur.fetchall()
    cur.close()
    conn.close()
    
    # Create a dictionary for easy access in the template
    contract = {
        'contract_id': row[0],
        'contract_name': row[1],
        'supplier_id': row[2],
        'start_date': row[3],
        'end_date': row[4],
        'value': row[5],
        'payment_frequency': row[6],
        'terms': row[7]
    }
    
    return render_template('edit_contract.html', contract=contract, suppliers=suppliers)
    
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

if __name__ == '__main__':
    print("Running Flask App...")
    app.run(debug=True)
