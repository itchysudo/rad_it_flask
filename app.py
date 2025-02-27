from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, send_from_directory
import psycopg2
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder="templates")
app.secret_key = "buVJyxLGE2GRjV"

# File Upload Configurations
UPLOAD_FOLDER = r"C:\projects\rad_it_flask\uploads\contracts"
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database Connection
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname="RAD_IT",
            user="postgres",
            password=os.getenv("DB_PASSWORD"),
            host="localhost"
        )
        return conn
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to the database - {e}")
        return None
    
@app.route('/')
def home():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch total numbers for dashboard
    cur.execute("SELECT COUNT(*) FROM contracts")
    total_contracts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM suppliers")
    total_suppliers = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM purchase_orders")
    total_pos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM contracts WHERE end_date <= CURRENT_DATE + INTERVAL '30 days'")
    upcoming_renewals = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template(
        'home.html',
        total_contracts=total_contracts,
        total_suppliers=total_suppliers,
        total_pos=total_pos,
        upcoming_renewals=upcoming_renewals
    )

@app.route('/suppliers')
def view_suppliers():
    """View all suppliers."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch suppliers
    cur.execute("SELECT supplier_id, name, primary_contact_id FROM suppliers ORDER BY name")
    suppliers = cur.fetchall()

    # Fetch contacts for each supplier
    cur.execute("SELECT supplier_id, contact_id, contact_name FROM supplier_contacts")
    contacts = cur.fetchall()

    # Organize contacts in a dictionary
    supplier_contacts = {}
    for contact in contacts:
        supplier_id = contact[0]
        if supplier_id not in supplier_contacts:
            supplier_contacts[supplier_id] = []
        supplier_contacts[supplier_id].append((contact[1], contact[2]))

      # Fetch suppliers and their primary contact name
    cur.execute("""
        SELECT s.supplier_id, s.name, c.contact_name
        FROM suppliers s
        LEFT JOIN supplier_contacts c ON s.primary_contact_id = c.contact_id
        ORDER BY s.supplier_id
    """)
    suppliers = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('suppliers.html', suppliers=suppliers, supplier_contacts=supplier_contacts)



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
    return redirect(url_for('view_supplier_contacts', supplier_id=supplier_id))




@app.route('/supplier/<int:supplier_id>/contacts')
def view_supplier_contacts(supplier_id):
    """View contacts associated with a specific supplier."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch supplier details
    cur.execute("SELECT supplier_id, name FROM suppliers WHERE supplier_id = %s", (supplier_id,))
    supplier_row = cur.fetchone()

    if not supplier_row:
        flash("⚠️ Supplier not found!", "warning")
        return redirect(url_for('view_suppliers'))

    # Convert supplier tuple to dictionary
    supplier = {"supplier_id": supplier_row[0], "name": supplier_row[1]}

    # Fetch contacts for the supplier and convert tuples to dictionaries
    cur.execute("SELECT contact_id, contact_name, email, office_phone, mobile FROM supplier_contacts WHERE supplier_id = %s", (supplier_id,))
    contacts = [
        {"contact_id": row[0], "contact_name": row[1], "email": row[2], "office_phone": row[3], "mobile": row[4]}
        for row in cur.fetchall()
    ]

    cur.close()
    conn.close()

    return render_template('supplier_contacts.html', supplier=supplier, contacts=contacts)



@app.route('/edit-supplier/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    """Edit an existing supplier."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch supplier details from the database
    cur.execute("""
        SELECT supplier_id, name, contact_name, email, office_phone, mobile, address, primary_contact_id 
        FROM suppliers 
        WHERE supplier_id = %s
    """, (supplier_id,))
    supplier_row = cur.fetchone()

    if not supplier_row:
        flash("⚠️ Supplier not found!", "warning")
        return redirect(url_for('view_suppliers'))

    # Convert tuple to dictionary
    supplier = {
        "supplier_id": supplier_row[0],
        "name": supplier_row[1],
        "contact_name": supplier_row[2],
        "email": supplier_row[3],  
        "office_phone": supplier_row[4],  
        "mobile": supplier_row[5],  
        "address": supplier_row[6],
        "primary_contact_id": supplier_row[7]
    }

    # Fetch all contacts associated with the supplier (for primary contact selection)
    cur.execute("SELECT contact_id, contact_name FROM supplier_contacts WHERE supplier_id = %s", (supplier_id,))
    contacts = cur.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        contact_name = request.form.get('contact_name', '')  
        email = request.form.get('email', '')  
        office_phone = request.form.get('office_phone', '')  
        mobile = request.form.get('mobile', '')  
        address = request.form.get('address', '')
        primary_contact_id = request.form.get('primary_contact_id', None)

        # Ensure primary_contact_id is NULL-safe for SQL
        if primary_contact_id == '' or primary_contact_id is None:
            primary_contact_id = None

        # Update supplier in the database
        cur.execute("""
            UPDATE suppliers 
            SET name = %s, contact_name = %s, email = %s, office_phone = %s, mobile = %s, address = %s, primary_contact_id = %s
            WHERE supplier_id = %s
        """, (name, contact_name, email, office_phone, mobile, address, primary_contact_id, supplier_id))

        conn.commit()
        cur.close()
        conn.close()

        flash("✅ Supplier updated successfully!", "success")
        return redirect(url_for('view_suppliers'))

    cur.close()
    conn.close()

    return render_template('edit_supplier.html', supplier=supplier, contacts=contacts)



@app.route('/delete-supplier/<int:supplier_id>', methods=['POST'])
def delete_supplier(supplier_id):
    """Delete a supplier and any associated contracts."""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # First, check if the supplier exists
        cur.execute("SELECT * FROM suppliers WHERE supplier_id = %s", (supplier_id,))
        supplier = cur.fetchone()

        if not supplier:
            flash("⚠️ Supplier not found!", "warning")
            return redirect(url_for('view_suppliers'))

        # Delete any contracts linked to this supplier (optional, based on DB constraints)
        cur.execute("DELETE FROM contracts WHERE supplier_id = %s", (supplier_id,))

        # Delete the supplier itself
        cur.execute("DELETE FROM suppliers WHERE supplier_id = %s", (supplier_id,))
        conn.commit()

        flash("✅ Supplier deleted successfully!", "success")
    except Exception as e:
        flash(f"❌ Error deleting supplier: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('view_suppliers'))

@app.route('/delete-contact/<int:contact_id>', methods=['POST'])
def delete_contact(contact_id):
    """Delete a specific contact from a supplier."""
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
    return redirect(url_for('view_supplier_contacts', supplier_id=supplier_id))  # ✅ Redirect to supplier contacts


from datetime import datetime, date
from decimal import Decimal

@app.route('/purchase-orders')
def view_purchase_orders():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch all purchase orders, joining suppliers and contracts
    cur.execute("""
        SELECT po.po_id, po.po_number, 
               COALESCE(c.contract_name, 'N/A') AS contract_name,  
               po.po_date, po.amount, po.requester, po.status, 
               COALESCE(s.name, 'N/A') AS supplier_name, po.department
        FROM purchase_orders po
        LEFT JOIN contracts c ON po.contract_id = c.contract_id
        LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
    """)

    purchase_orders = cur.fetchall()

    # Convert tuples to lists and ensure proper formatting
    updated_purchase_orders = []
    for po in purchase_orders:
        po = list(po)  # Convert tuple to list for modifications

        # ✅ Fix `po_date`
        if isinstance(po[3], (datetime, date)):  
            po[3] = po[3].strftime("%d/%m/%Y")  # Convert date to string
        elif isinstance(po[3], str):
            try:
                po[3] = datetime.strptime(po[3], "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                po[3] = "Invalid Date"

        # ✅ Fix `amount` (ensure it's always a float)
        try:
            po[4] = float(po[4])  # Convert from string or Decimal to float
        except (ValueError, TypeError):
            print(f"❌ ERROR: Amount for PO ID {po[0]} is invalid: {po[4]}")
            po[4] = 0.00  # Default to 0.00 if invalid

        updated_purchase_orders.append(po)

    # Fetch suppliers for dropdown
    cur.execute("SELECT supplier_id, name FROM suppliers ORDER BY name")
    suppliers = cur.fetchall()

    # Fetch contracts for dropdown
    cur.execute("SELECT contract_id, contract_name FROM contracts ORDER BY contract_name")
    contracts = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('purchase_orders.html', 
                           purchase_orders=updated_purchase_orders, 
                           suppliers=suppliers, 
                           contracts=contracts)




@app.route('/edit-po/<int:po_id>', methods=['GET', 'POST'])
def edit_po(po_id):
    conn = get_db_connection()
    cur = conn.cursor()

    print(f"\n🔵 DEBUG: Fetching PO ID {po_id}")

    if request.method == 'POST':
        po_number = request.form['po_number']
        supplier_id = request.form.get('supplier_id') or None
        contract_id = request.form.get('contract_id') or None
        po_date = request.form['po_date']
        amount = request.form['amount']
        requester = request.form['requester']
        status = request.form['status']
        department = request.form.get('department', '')
        notes = request.form.get('notes', '')

        print("\n🔴 DEBUG: Received POST request to update PO.")
        print(f"PO Number: {po_number}, Supplier ID: {supplier_id}, Contract ID: {contract_id}")
        print(f"Date: {po_date}, Amount: {amount}, Requester: {requester}, Status: {status}")

        cur.execute("""
            UPDATE purchase_orders
            SET po_number = %s, supplier_id = %s, contract_id = %s, po_date = %s, amount = %s, 
                requester = %s, status = %s, department = %s, notes = %s
            WHERE po_id = %s
        """, (po_number, supplier_id, contract_id, po_date, amount, requester, status, department, notes, po_id))

        conn.commit()
        cur.close()
        conn.close()

        print("\n✅ DEBUG: Purchase Order updated successfully!")
        flash('✅ Purchase Order updated successfully!', 'success')
        return redirect(url_for('view_purchase_orders'))

    # Fetch PO details
    cur.execute("""
        SELECT po_id, po_number, supplier_id, contract_id, po_date, amount, requester, status, department, notes 
        FROM purchase_orders WHERE po_id = %s
    """, (po_id,))
    po = cur.fetchone()

    if not po:
        flash("⚠️ Purchase Order not found!", "warning")
        print("❌ DEBUG: PO not found!")
        return redirect(url_for('view_purchase_orders'))

    print(f"\n🟢 DEBUG: Fetched PO Details for PO ID {po_id}: {po}\n")

    # Fetch suppliers list for dropdown
    cur.execute("SELECT supplier_id, name FROM suppliers ORDER BY name")
    suppliers = cur.fetchall()

    print(f"\n✅ DEBUG: Suppliers Retrieved - {len(suppliers)} found")
    if not suppliers:
        print("❌ DEBUG: No suppliers found!")

    for supplier in suppliers:
        print(f" - Supplier ID: {supplier[0]}, Name: {supplier[1]}")

    # Fetch contracts list for dropdown
    cur.execute("SELECT contract_id, contract_name FROM contracts ORDER BY contract_name")
    contracts = cur.fetchall()

    print(f"\n✅ DEBUG: Contracts Retrieved - {len(contracts)} found")
    if not contracts:
        print("❌ DEBUG: No contracts found!")

    for contract in contracts:
        print(f" - Contract ID: {contract[0]}, Name: {contract[1]}")

    cur.close()
    conn.close()

    po_dict = {
        "po_id": po[0], "po_number": po[1], "supplier_id": po[2], "contract_id": po[3], 
        "po_date": po[4], "amount": po[5], "requester": po[6], "status": po[7], 
        "department": po[8], "notes": po[9]
    }

    return render_template('edit_po.html', po=po_dict, suppliers=suppliers, contracts=contracts)


import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = r"C:\projects\rad_it_flask\uploads\contracts"
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'png', 'jpg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/edit-contract/<int:contract_id>', methods=['GET', 'POST'])
def edit_contract(contract_id):
    """Edit an existing contract."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch contract details
    cur.execute("""
        SELECT contract_id, contract_name, supplier_id, start_date, end_date, value, payment_frequency 
        FROM contracts WHERE contract_id = %s
    """, (contract_id,))
    contract_row = cur.fetchone()

    if not contract_row:
        flash("⚠️ Contract not found!", "warning")
        return redirect(url_for('view_contracts'))

    # Convert tuple to dictionary and ensure dates are formatted as YYYY-MM-DD
    contract = {
        "contract_id": contract_row[0],
        "contract_name": contract_row[1],
        "supplier_id": contract_row[2],
        "start_date": contract_row[3].strftime('%Y-%m-%d') if contract_row[3] else '',
        "end_date": contract_row[4].strftime('%Y-%m-%d') if contract_row[4] else '',
        "value": contract_row[5],
        "payment_frequency": contract_row[6]
    }

    # 🔴 Debugging Output - Double-check retrieved contract details
    print(f"\n🔵 DEBUG: Retrieved Contract {contract_id} for Editing")
    print(f"Start Date from DB: {contract['start_date']}, End Date from DB: {contract['end_date']}\n")

    # Fetch suppliers for dropdown
    cur.execute("SELECT supplier_id, name FROM suppliers ORDER BY name")
    suppliers = cur.fetchall()

    if request.method == 'POST':
        contract_name = request.form['contract_name']
        supplier_id = request.form['supplier_id']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        value = request.form['value']
        payment_frequency = request.form['payment_frequency']

        print(f"\n🔵 DEBUG: Updating Contract {contract_id}")
        print(f"Start Date: {start_date}, End Date: {end_date}")

        # Update contract in database
        cur.execute("""
            UPDATE contracts 
            SET contract_name = %s, supplier_id = %s, start_date = %s, end_date = %s, 
                value = %s, payment_frequency = %s
            WHERE contract_id = %s
        """, (contract_name, supplier_id, start_date, end_date, value, payment_frequency, contract_id))

        conn.commit()

        # ✅ Handle File Upload
        if 'contract_file' in request.files:
            file = request.files['contract_file']

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                try:
                    # Ensure the upload directory exists
                    if not os.path.exists(app.config['UPLOAD_FOLDER']):
                        os.makedirs(app.config['UPLOAD_FOLDER'])

                    file.save(file_path)  # Save file to upload folder

                    # ✅ Insert file into `contract_files` table
                    cur.execute("INSERT INTO contract_files (contract_id, file_path) VALUES (%s, %s)", (contract_id, file_path))
                    conn.commit()

                    print(f"✅ File successfully uploaded: {file_path}")
                except Exception as e:
                    print(f"❌ ERROR: Could not save file {filename}: {e}")

        cur.close()
        conn.close()

        flash("✅ Contract updated successfully!", "success")
        return redirect(url_for('view_contracts'))

    cur.close()
    conn.close()

    return render_template('edit_contract.html', contract=contract, suppliers=suppliers)




@app.route('/add-contract', methods=['GET', 'POST'])
def add_contract():
    """Add a new contract."""
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        contract_name = request.form['contract_name']
        supplier_id = request.form.get('supplier_id')
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        value = request.form['value']
        payment_frequency = request.form['payment_frequency']

        print(f"\n🔴 DEBUG: Adding New Contract")
        print(f"Contract Name: {contract_name}, Supplier ID: {supplier_id}")
        print(f"Start Date: {start_date}, End Date: {end_date}, Value: {value}, Payment Frequency: {payment_frequency}\n")

        cur.execute("""
            INSERT INTO contracts (contract_name, supplier_id, start_date, end_date, value, payment_frequency)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (contract_name, supplier_id, start_date, end_date, value, payment_frequency))

        conn.commit()
        cur.close()
        conn.close()

        flash("✅ Contract added successfully!", "success")
        return redirect(url_for('view_contracts'))

    # Fetch suppliers for dropdown
    cur.execute("SELECT supplier_id, name FROM suppliers ORDER BY name")
    suppliers = cur.fetchall()

    print(f"\n✅ DEBUG: Suppliers Retrieved - {len(suppliers)} found")
    for supplier in suppliers:
        print(f" - Supplier ID: {supplier[0]}, Name: {supplier[1]}")

    cur.close()
    conn.close()

    return render_template('add_contract.html', suppliers=suppliers)



@app.route('/add-supplier-contact/<int:supplier_id>', methods=['POST'])
def add_supplier_contact(supplier_id):
    """Add a new contact to a supplier."""
    contact_name = request.form['contact_name']
    email = request.form.get('email', None)
    office_phone = request.form.get('office_phone', None)
    mobile = request.form.get('mobile', None)

    conn = get_db_connection()
    cur = conn.cursor()

    # Insert the new contact into the supplier_contacts table
    cur.execute("""
        INSERT INTO supplier_contacts (supplier_id, contact_name, email, office_phone, mobile)
        VALUES (%s, %s, %s, %s, %s)
    """, (supplier_id, contact_name, email, office_phone, mobile))

    conn.commit()
    cur.close()
    conn.close()

    flash("✅ Contact added successfully!", "success")
    return redirect(url_for('view_supplier_contacts', supplier_id=supplier_id))  # ✅ Redirect to supplier contacts


@app.route('/download-contract/<int:contract_id>')
def download_contract(contract_id):
    """Download the latest uploaded contract file for a given contract."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch the most recent file for the contract
    cur.execute("""
        SELECT file_path FROM contract_files 
        WHERE contract_id = %s 
        ORDER BY file_id DESC LIMIT 1
    """, (contract_id,))
    
    file = cur.fetchone()
    cur.close()
    conn.close()

    if not file or not file[0]:
        flash("⚠️ No contract file found for this contract.", "warning")
        return redirect(url_for('view_contracts'))

    return send_file(file[0], as_attachment=True)

# 📌 View Contracts (Fix for Contract Files)
from datetime import datetime, date  # Ensure 'date' is imported

@app.route('/contracts')
def view_contracts():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch suppliers first
    cur.execute("SELECT supplier_id, name FROM suppliers ORDER BY name")
    suppliers = cur.fetchall()

    # Debugging output
    print("DEBUG: Suppliers List:", suppliers)

    # Fetch contracts with suppliers
    cur.execute("""
        SELECT c.contract_id, c.contract_name, s.name AS supplier_name, 
               c.start_date, c.end_date, c.value, c.payment_frequency
        FROM contracts c
        LEFT JOIN suppliers s ON c.supplier_id = s.supplier_id
        ORDER BY c.end_date
    """)
    contracts = cur.fetchall()

    # Fetch contract files separately
    cur.execute("SELECT contract_id, file_id, file_path FROM contract_files")
    contract_files = {}
    for row in cur.fetchall():
        contract_id, file_id, file_path = row
        if contract_id not in contract_files:
            contract_files[contract_id] = []
        contract_files[contract_id].append((file_id, file_path))

    # Process contracts for display
    updated_contracts = []
    for contract in contracts:
        contract_id, contract_name, supplier_name, start_date, end_date, value, payment_frequency = contract

        from datetime import datetime, date

        # Ensure start_date and end_date are formatted correctly before passing to Jinja
        if isinstance(start_date, date):
            start_date = start_date.strftime("%d/%m/%Y")  # Convert to string
        if isinstance(end_date, date):
            end_date = end_date.strftime("%d/%m/%Y")  # Convert to string



        # Calculate installment amount
        try:
            start_dt = datetime.strptime(start_date, "%d/%m/%Y")
            end_dt = datetime.strptime(end_date, "%d/%m/%Y")

            contract_duration_months = max(1, (relativedelta(end_dt, start_dt).years * 12 +
                                               relativedelta(end_dt, start_dt).months))

            num_payments = {
                "One-time": 1,
                "Monthly": contract_duration_months,
                "Quarterly": contract_duration_months // 3,
                "Annually": contract_duration_months // 12
            }.get(payment_frequency, 1)

            installment_amount = round(value / max(1, num_payments), 2)
        except Exception as e:
            print(f"❌ ERROR: Failed to calculate installment amount for contract {contract_id}: {e}")
            installment_amount = value  # Fallback to total value if error occurs

        # Attach contract files (if available)
        files = contract_files.get(contract_id, [])

        updated_contracts.append(
            (contract_id, contract_name, supplier_name, start_date, end_date, value, installment_amount, payment_frequency, files)
        )

    cur.close()
    conn.close()

    print(f"✅ DEBUG: Final contract data sent to template: {updated_contracts}")


    return render_template('contracts.html', contracts=updated_contracts, suppliers=suppliers)




# 📌 Upload Contract Files (Multiple Files)
@app.route('/upload-contract-files/<int:contract_id>', methods=['POST'])
def upload_contract_files(contract_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if 'contract_files' in request.files:
        files = request.files.getlist('contract_files')
        for file in files:
            if file and file.filename.strip():  
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], f"contract_{contract_id}_{filename}")
                file.save(file_path)

                # Insert file record into database
                cur.execute("""
                    INSERT INTO contract_files (contract_id, file_path)
                    VALUES (%s, %s)
                """, (contract_id, file_path))

    conn.commit()
    cur.close()
    conn.close()

    flash("✅ Contract files uploaded successfully!", "success")
    return redirect(url_for('view_contracts'))


# 📌 View Contract File
@app.route('/view-contract-file/<int:file_id>')
def view_contract_file(file_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT file_path FROM contract_files WHERE file_id = %s", (file_id,))
    file = cur.fetchone()

    cur.close()
    conn.close()

    if not file:
        flash("⚠️ File not found!", "warning")
        return redirect(url_for('view_contracts'))

    return send_file(file[0], as_attachment=False)

@app.route('/delete-contract/<int:contract_id>', methods=['POST'])
def delete_contract(contract_id):
    """Delete a specific contract and its associated files."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Delete associated files
    cur.execute("DELETE FROM contract_files WHERE contract_id = %s", (contract_id,))

    # Delete contract
    cur.execute("DELETE FROM contracts WHERE contract_id = %s", (contract_id,))
    conn.commit()

    cur.close()
    conn.close()

    flash("✅ Contract deleted successfully!", "success")
    return redirect(url_for('view_contracts'))

    


# 📌 Delete Contract File
@app.route('/delete-contract-file/<int:file_id>', methods=['POST'])
def delete_contract_file(file_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch file path before deletion
    cur.execute("SELECT file_path FROM contract_files WHERE file_id = %s", (file_id,))
    file = cur.fetchone()

    if file:
        file_path = file[0]

        # Delete from system
        try:
            os.remove(file_path)
        except FileNotFoundError:
            print(f"WARNING: File {file_path} not found, skipping delete.")

    # Remove from database
    cur.execute("DELETE FROM contract_files WHERE file_id = %s", (file_id,))
    conn.commit()

    cur.close()
    conn.close()

    flash("✅ File deleted successfully!", "success")
    return redirect(url_for('view_contracts'))


# 📌 Download Contract File
@app.route('/download-contract-file/<int:file_id>')
def download_contract_file(file_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT file_path FROM contract_files WHERE file_id = %s", (file_id,))
    file = cur.fetchone()

    cur.close()
    conn.close()

    if not file:
        flash("⚠️ File not found!", "warning")
        return redirect(url_for('view_contracts'))

    return send_file(file[0], as_attachment=True)


# Run the Flask App
if __name__ == '__main__':
    print("Running Flask App...")
    app.run(debug=True)
