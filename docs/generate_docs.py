"""
AquaFlow Documentation Generator
Powered by Quantum Axis

Run: python docs/generate_docs.py

Generates:
  - docs/AquaFlow_Developer_Guide.html
  - docs/AquaFlow_User_Manual.html
"""

import os
from datetime import datetime


def generate_developer_guide():
    """Generate developer documentation."""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AquaFlow Developer Guide</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; color: #333; line-height: 1.8; }}
        h1 {{ color: #04a9f5; border-bottom: 3px solid #04a9f5; padding-bottom: 10px; }}
        h2 {{ color: #1a2035; border-bottom: 1px solid #ddd; padding-bottom: 6px; margin-top: 30px; }}
        h3 {{ color: #333; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 13px; }}
        pre {{ background: #1a2035; color: #e0e0e0; padding: 15px; border-radius: 6px; overflow-x: auto; font-size: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
        th {{ background: #f4f4f4; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; color: white; }}
        .bg-green {{ background: #14b898; }}
        .bg-blue {{ background: #04a9f5; }}
        .bg-orange {{ background: #f4c22b; color: #333; }}
        .bg-red {{ background: #f44236; }}
        .cover {{ text-align: center; padding: 60px 0; }}
        .cover h1 {{ font-size: 36px; border: none; }}
        .flow-box {{ background: #f8f9fa; border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        @media print {{ body {{ margin: 20mm; }} }}
    </style>
</head>
<body>

<div class="cover">
    <h1>AquaFlow</h1>
    <h2>Car Wash Management System</h2>
    <h3>Developer Guide</h3>
    <p>Version 1.0.0 | Generated: {datetime.now().strftime('%d %B %Y')}</p>
    <p><strong>Powered by Quantum Axis</strong></p>
</div>

<div style="page-break-after: always;"></div>

<h1>1. System Architecture</h1>

<h2>1.1 Technology Stack</h2>
<table>
    <tr><th>Component</th><th>Technology</th><th>Version</th></tr>
    <tr><td>Backend</td><td>Python + Django</td><td>3.13 / 5.2 LTS</td></tr>
    <tr><td>Database</td><td>PostgreSQL</td><td>17.x</td></tr>
    <tr><td>Frontend</td><td>HTML5 + CSS3 + JavaScript</td><td>ES2022+</td></tr>
    <tr><td>UI Framework</td><td>Bootstrap 5 + Custom CSS</td><td>5.3</td></tr>
    <tr><td>WSGI Server</td><td>Waitress (Windows)</td><td>3.x</td></tr>
</table>

<h2>1.2 Project Structure</h2>
<pre>
AquaFlow/
├── manage.py
├── config/
│   ├── urls.py
│   ├── wsgi.py
│   └── settings/
│       ├── base.py
│       ├── development.py
│       └── production.py
├── apps/
│   ├── accounts/      (Users, Roles, Permissions, Security)
│   ├── businesses/    (Business config, logo, tax)
│   ├── branches/      (Multi-branch support)
│   ├── customers/     (Customer management)
│   ├── vehicles/      (Vehicles, brands, models)
│   ├── services/      (Services, pricing)
│   ├── bookings/      (Appointments)
│   ├── pos/           (Point of Sale)
│   ├── orders/        (Orders)
│   ├── invoices/      (Invoices, items)
│   ├── payments/      (Payments, refunds)
│   ├── wash/          (Wash operations, jobs)
│   ├── employees/     (Staff management)
│   ├── inventory/     (Products, stock)
│   ├── suppliers/     (Suppliers, purchases)
│   ├── finance/       (Expenses)
│   ├── memberships/   (Membership plans)
│   ├── loyalty/       (Points program)
│   ├── reports/       (All reports)
│   ├── backups/       (Backup & restore)
│   ├── trash/         (Recycle bin)
│   ├── audit/         (Audit logs)
│   └── system/        (Health, QA, DB config)
├── templates/
├── static/
├── media/
├── logs/
├── backups/
└── docs/
</pre>

<h2>1.3 Business Flow</h2>

<div class="flow-box">
<h3>Complete Car Wash Flow</h3>
<pre>
1. BOOKING (Appointment)
   Customer → Books time slot
   Status: PENDING → CONFIRMED

2. ARRIVAL
   Customer arrives → Booking marked ARRIVED
   Auto-creates WASH JOB on Wash Board

3. WASH OPERATIONS
   Employee assigned → Bay assigned
   Status: WAITING → ASSIGNED → WASHING → QUALITY CHECK → READY

4. INVOICING (POS)
   Wash complete → Click "Invoice This"
   POS opens pre-filled with:
     - Customer
     - Vehicle
     - Service(s) from wash job
   Cashier can add:
     - Extra services
     - Products
     - Repairs
     - Custom items
   Edit prices if needed
   Select payment method
   Complete sale

5. RESULT
   Creates: Order → Invoice → Payment
   Wash Job marked COMPLETED
   Booking marked COMPLETED
   Inventory updated
   Loyalty points awarded
   Membership wash deducted
   Audit log recorded
</pre>
</div>

<h2>1.4 Database Design Principles</h2>
<ul>
    <li><strong>DecimalField</strong> for ALL money — never float</li>
    <li><strong>PostgreSQL sequences</strong> for invoice/order numbering</li>
    <li><strong>Soft delete</strong> for customers, vehicles, services, products</li>
    <li><strong>PROTECT</strong> foreign keys on financial records</li>
    <li><strong>transaction.atomic()</strong> for all critical operations</li>
    <li><strong>Price snapshots</strong> in invoice items (old invoices never change)</li>
    <li><strong>UPPERCASE</strong> for brands, models, vehicle types, colors, fuel types</li>
    <li><strong>Case-insensitive</strong> uniqueness on brands, models</li>
</ul>

<h2>1.5 Key Models</h2>

<h3>Financial Chain</h3>
<pre>
Customer → Vehicle → Booking → WashJob → Order → Invoice → InvoiceItem → Payment
</pre>

<h3>Rules</h3>
<table>
    <tr><th>Record Type</th><th>Can Delete?</th><th>Method</th></tr>
    <tr><td>Customer</td><td>Soft delete</td><td>is_deleted=True</td></tr>
    <tr><td>Vehicle</td><td>Soft delete</td><td>is_deleted=True</td></tr>
    <tr><td>Service</td><td>Soft delete</td><td>is_deleted=True</td></tr>
    <tr><td>Product</td><td>Soft delete</td><td>is_deleted=True</td></tr>
    <tr><td>Order</td><td>VOID only</td><td>status='void'</td></tr>
    <tr><td>Invoice</td><td>VOID only</td><td>status='void'</td></tr>
    <tr><td>Payment</td><td>REFUND only</td><td>negative amount</td></tr>
    <tr><td>Audit Log</td><td>NEVER</td><td>Immutable</td></tr>
</table>

<h1>2. Security</h1>

<h2>2.1 Role System</h2>
<table>
    <tr><th>Role</th><th>Description</th><th>Permissions</th></tr>
    <tr><td>SUPER_ADMIN</td><td>Developer / System Admin</td><td>ALL (53)</td></tr>
    <tr><td>OWNER</td><td>Business Owner</td><td>43</td></tr>
    <tr><td>MANAGER</td><td>Branch Manager</td><td>29</td></tr>
    <tr><td>CASHIER</td><td>POS Operator</td><td>13</td></tr>
    <tr><td>WASHER</td><td>Wash Bay Worker</td><td>4</td></tr>
    <tr><td>INVENTORY_MANAGER</td><td>Stock Manager</td><td>6</td></tr>
    <tr><td>ACCOUNTANT</td><td>Financial User</td><td>7</td></tr>
    <tr><td>Custom Roles</td><td>Created by Super Admin</td><td>Variable</td></tr>
</table>

<h2>2.2 Security Features</h2>
<ul>
    <li>Login attempt tracking</li>
    <li>Account lockout after N failures</li>
    <li>Idle session timeout</li>
    <li>Password strength requirements</li>
    <li>CSRF protection on all forms</li>
    <li>Backend permission checks (never frontend only)</li>
    <li>Encrypted database password storage (Fernet)</li>
    <li>Audit trail for all sensitive actions</li>
</ul>

<h1>3. API Endpoints</h1>

<h2>3.1 Key URLs</h2>
<table>
    <tr><th>URL</th><th>Purpose</th></tr>
    <tr><td>/dashboard/</td><td>Main dashboard</td></tr>
    <tr><td>/pos/</td><td>Point of Sale</td></tr>
    <tr><td>/wash/</td><td>Wash Board</td></tr>
    <tr><td>/bookings/</td><td>Booking management</td></tr>
    <tr><td>/customers/</td><td>Customer management</td></tr>
    <tr><td>/vehicles/</td><td>Vehicle management</td></tr>
    <tr><td>/services/</td><td>Service management</td></tr>
    <tr><td>/orders/</td><td>Order history</td></tr>
    <tr><td>/invoices/</td><td>Invoice management</td></tr>
    <tr><td>/payments/</td><td>Payment history</td></tr>
    <tr><td>/inventory/</td><td>Product & stock</td></tr>
    <tr><td>/suppliers/</td><td>Supplier management</td></tr>
    <tr><td>/finance/</td><td>Expenses</td></tr>
    <tr><td>/employees/</td><td>Employee management</td></tr>
    <tr><td>/memberships/</td><td>Membership plans</td></tr>
    <tr><td>/loyalty/</td><td>Loyalty program</td></tr>
    <tr><td>/reports/</td><td>All reports</td></tr>
    <tr><td>/business/</td><td>Business settings</td></tr>
    <tr><td>/system/</td><td>System admin</td></tr>
    <tr><td>/system/health/</td><td>System health</td></tr>
    <tr><td>/system/qa/</td><td>QA diagnostics</td></tr>
    <tr><td>/system/backups/</td><td>Backup & restore</td></tr>
    <tr><td>/system/database/</td><td>DB configuration</td></tr>
    <tr><td>/system/trash/</td><td>Recycle bin</td></tr>
    <tr><td>/system/audit/</td><td>Audit logs</td></tr>
    <tr><td>/accounts/roles/</td><td>Role management</td></tr>
    <tr><td>/accounts/users/</td><td>User management</td></tr>
    <tr><td>/accounts/security/</td><td>Security settings</td></tr>
</table>

<h1>4. Deployment</h1>

<h2>4.1 Development Setup</h2>
<pre>
git clone [repository]
cd AquaFlow
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements/development.txt
cp .env.example .env  (edit with your settings)
python manage.py migrate
python manage.py createsuperuser
python manage.py setup_aquaflow --superuser [username]
python manage.py runserver 0.0.0.0:8000
</pre>

<h2>4.2 Production (Windows)</h2>
<pre>
1. Install PostgreSQL as Windows Service
2. Install NSSM
3. Create run_server.bat:
   cd /d C:\\AquaFlow
   call venv\\Scripts\\activate
   python -m waitress --host=0.0.0.0 --port=8000 config.wsgi:application
4. nssm install AquaFlow
5. Configure firewall: allow port 8000
6. Access via LAN: http://192.168.x.x:8000/
</pre>

<h2>4.3 Environment Variables (.env)</h2>
<pre>
DJANGO_SECRET_KEY=change-me-50-chars-minimum
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,192.168.1.100
DB_ENGINE=django.db.backends.postgresql
DB_NAME=aquaflow
DB_USER=aquaflow_user
DB_PASSWORD=secure-password
DB_HOST=127.0.0.1
DB_PORT=5432
BACKUP_PATH=backups
</pre>

<div class="cover" style="margin-top:50px;">
    <p><strong>AquaFlow Developer Guide</strong></p>
    <p>Version 1.0.0 | Powered by Quantum Axis</p>
    <p>© {datetime.now().year} Quantum Axis. All rights reserved.</p>
</div>

</body>
</html>"""

    with open('docs/AquaFlow_Developer_Guide.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print('✓ Developer Guide generated: docs/AquaFlow_Developer_Guide.html')


def generate_user_manual():
    """Generate user manual."""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AquaFlow User Manual</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; color: #333; line-height: 1.8; }}
        h1 {{ color: #04a9f5; border-bottom: 3px solid #04a9f5; padding-bottom: 10px; }}
        h2 {{ color: #1a2035; border-bottom: 1px solid #ddd; padding-bottom: 6px; margin-top: 30px; }}
        h3 {{ color: #333; }}
        .step {{ background: #f8f9fa; border-left: 4px solid #04a9f5; padding: 12px 16px; margin: 10px 0; border-radius: 4px; }}
        .step-num {{ background: #04a9f5; color: white; padding: 2px 8px; border-radius: 50%; font-weight: bold; margin-right: 8px; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #f4c22b; padding: 12px 16px; margin: 10px 0; border-radius: 4px; }}
        .tip {{ background: #d4edda; border-left: 4px solid #14b898; padding: 12px 16px; margin: 10px 0; border-radius: 4px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
        th {{ background: #f4f4f4; }}
        .cover {{ text-align: center; padding: 60px 0; }}
        .cover h1 {{ font-size: 36px; border: none; }}
        @media print {{ body {{ margin: 20mm; }} }}
    </style>
</head>
<body>

<div class="cover">
    <h1>AquaFlow</h1>
    <h2>Car Wash Management System</h2>
    <h3>User Manual</h3>
    <p>Version 1.0.0 | {datetime.now().strftime('%d %B %Y')}</p>
    <p><strong>Powered by Quantum Axis</strong></p>
</div>

<div style="page-break-after: always;"></div>

<h1>Table of Contents</h1>
<ol>
    <li>Getting Started</li>
    <li>Dashboard</li>
    <li>Daily Car Wash Flow</li>
    <li>Bookings (Appointments)</li>
    <li>Wash Operations</li>
    <li>Point of Sale (POS)</li>
    <li>Customers & Vehicles</li>
    <li>Services & Pricing</li>
    <li>Orders & Invoices</li>
    <li>Inventory</li>
    <li>Employees</li>
    <li>Reports</li>
    <li>System Settings</li>
    <li>Troubleshooting</li>
</ol>

<h1>1. Getting Started</h1>

<h2>1.1 Login</h2>
<div class="step">
    <span class="step-num">1</span> Open your browser and go to: <strong>http://192.168.x.x:8000/</strong><br>
    <span class="step-num">2</span> Enter your username and password<br>
    <span class="step-num">3</span> Click <strong>Sign In</strong>
</div>

<div class="warning">
    <strong>⚠ Important:</strong> After 5 wrong password attempts, your account will be locked for 30 minutes.
    Contact Super Admin to unlock.
</div>

<h1>2. Dashboard</h1>
<p>The dashboard shows:</p>
<ul>
    <li><strong>Today's Sales</strong> — total revenue today</li>
    <li><strong>Today's Washes</strong> — vehicles washed today</li>
    <li><strong>Pending Bookings</strong> — upcoming appointments</li>
    <li><strong>Total Customers</strong> — registered customers</li>
    <li><strong>Sales Chart</strong> — last 7 days trend</li>
    <li><strong>Quick Actions</strong> — shortcuts to POS, bookings, etc.</li>
</ul>

<h1>3. Daily Car Wash Flow</h1>

<h2>The Complete Process</h2>

<div class="step">
    <span class="step-num">1</span> <strong>BOOKING</strong> — Customer calls or walks in to book<br>
    Go to <em>Bookings → Add Booking</em><br>
    Select: Customer, Vehicle, Service, Date, Time<br>
    Status starts as: <strong>PENDING</strong>
</div>

<div class="step">
    <span class="step-num">2</span> <strong>CUSTOMER ARRIVES</strong> — Mark booking as ARRIVED<br>
    Go to <em>Bookings → Click booking → Mark Arrived</em><br>
    This automatically creates a <strong>Wash Job</strong> on the Wash Board
</div>

<div class="step">
    <span class="step-num">3</span> <strong>WASH OPERATIONS</strong> — Track the wash progress<br>
    Go to <em>Wash Board</em><br>
    Assign employee and wash bay<br>
    Click <strong>Start Washing</strong><br>
    Move through: Washing → Quality Check → Ready
</div>

<div class="step">
    <span class="step-num">4</span> <strong>INVOICE & PAYMENT</strong> — Bill the customer<br>
    On the Wash Board, click <strong>"Invoice"</strong> on the ready wash job<br>
    This opens <strong>POS</strong> pre-filled with customer + vehicle + services<br>
    Add any extra items (products, repairs)<br>
    Select payment method (Cash, Card, etc.)<br>
    Click <strong>Complete Sale</strong><br>
    Receipt prints automatically
</div>

<div class="step">
    <span class="step-num">5</span> <strong>DONE</strong> — Everything is recorded<br>
    Order created, Invoice created, Payment recorded<br>
    Wash job marked COMPLETED<br>
    Inventory updated, Loyalty points awarded
</div>

<div class="tip">
    <strong>💡 Quick Walk-in (No Booking):</strong>
    You can also create a wash job directly from the Wash Board
    or go straight to POS for a quick sale.
</div>

<h1>4. Bookings (Appointments)</h1>

<h2>4.1 Create a Booking</h2>
<div class="step">
    <span class="step-num">1</span> Go to <em>Bookings → Add Booking</em><br>
    <span class="step-num">2</span> Search and select Customer (or create new)<br>
    <span class="step-num">3</span> Search and select Vehicle (or create new)<br>
    <span class="step-num">4</span> Select Service<br>
    <span class="step-num">5</span> Date and Time (defaults to today/now)<br>
    <span class="step-num">6</span> Optionally assign Employee and Wash Bay<br>
    <span class="step-num">7</span> Click <strong>Create Booking</strong>
</div>

<h2>4.2 Booking Statuses</h2>
<table>
    <tr><th>Status</th><th>Meaning</th></tr>
    <tr><td>PENDING</td><td>Just created, not yet confirmed</td></tr>
    <tr><td>CONFIRMED</td><td>Customer confirmed they will come</td></tr>
    <tr><td>ARRIVED</td><td>Customer is here → creates Wash Job</td></tr>
    <tr><td>COMPLETED</td><td>Service done and invoiced</td></tr>
    <tr><td>CANCELLED</td><td>Customer cancelled</td></tr>
    <tr><td>NO SHOW</td><td>Customer didn't come</td></tr>
</table>

<h1>5. Wash Operations</h1>

<h2>5.1 Wash Board</h2>
<p>The Wash Board shows 6 columns:</p>
<table>
    <tr><th>Column</th><th>Meaning</th></tr>
    <tr><td>Waiting</td><td>Car is here, waiting to start</td></tr>
    <tr><td>Assigned</td><td>Employee assigned, about to start</td></tr>
    <tr><td>Washing</td><td>Currently being washed</td></tr>
    <tr><td>Quality Check</td><td>Wash done, being inspected</td></tr>
    <tr><td>Ready</td><td>Car is clean, waiting for customer</td></tr>
    <tr><td>Completed</td><td>Customer picked up (today)</td></tr>
</table>

<h2>5.2 Managing a Wash Job</h2>
<div class="step">
    Click on any wash job card to:<br>
    • Assign/change employee<br>
    • Assign/change wash bay<br>
    • Move to next status (Start → QC → Ready → Complete)<br>
    • Invoice the job (opens POS)
</div>

<h1>6. Point of Sale (POS)</h1>

<h2>6.1 Quick Sale (Walk-in)</h2>
<div class="step">
    <span class="step-num">1</span> Go to <em>POS</em><br>
    <span class="step-num">2</span> Search Customer (or create new)<br>
    <span class="step-num">3</span> Search Vehicle<br>
    <span class="step-num">4</span> Add services and/or products to cart<br>
    <span class="step-num">5</span> Adjust prices/quantities if needed<br>
    <span class="step-num">6</span> Apply discount if any<br>
    <span class="step-num">7</span> Select payment method<br>
    <span class="step-num">8</span> Click <strong>Complete Sale</strong>
</div>

<h2>6.2 Invoice from Wash Job</h2>
<div class="step">
    <span class="step-num">1</span> On Wash Board, find the ready wash job<br>
    <span class="step-num">2</span> Click <strong>"Invoice"</strong><br>
    <span class="step-num">3</span> POS opens with customer + vehicle + service pre-filled<br>
    <span class="step-num">4</span> Add extra items if needed<br>
    <span class="step-num">5</span> Complete payment
</div>

<h2>6.3 Split Payment</h2>
<div class="step">
    Click <strong>Cash</strong> first (enters full amount)<br>
    Click <strong>Card</strong> to add another payment<br>
    Adjust amounts so they total correctly<br>
    Complete sale
</div>

<h2>6.4 Custom Job / Repair</h2>
<div class="step">
    Click <strong>"Custom Job"</strong> button<br>
    Enter description (e.g., "Battery Replacement")<br>
    Enter price<br>
    Added to cart as a service item
</div>

<h1>7. Customers & Vehicles</h1>

<h2>7.1 Add Customer</h2>
<p>Customers can be added from:</p>
<ul>
    <li>Customer list page</li>
    <li>POS (popup)</li>
    <li>Booking form (popup)</li>
    <li>Vehicle form (popup)</li>
</ul>
<p>Required: <strong>Name + Phone number</strong></p>

<h2>7.2 Add Vehicle</h2>
<p>When adding a vehicle:</p>
<ul>
    <li>Type registration → checks if exists</li>
    <li>If new → fill brand, model, type, color, fuel</li>
    <li>All stored in UPPERCASE</li>
    <li>New brands/models auto-created</li>
</ul>

<h1>8. Services & Pricing</h1>

<h2>8.1 Service Prices</h2>
<p>Prices can be different for:</p>
<ul>
    <li>Different vehicle types (Sedan vs SUV vs Van)</li>
    <li>Different branches</li>
    <li>Default price for all</li>
</ul>

<div class="step">
    Go to <em>Services → Click a service → Add Price</em><br>
    Or click the <strong>$</strong> button in service list
</div>

<h1>9. Reports</h1>
<p>Available reports (all with CSV export):</p>
<ul>
    <li>Sales Report (daily/monthly)</li>
    <li>Service Popularity</li>
    <li>Top Customers</li>
    <li>Most Washed Vehicles</li>
    <li>Cashier Performance</li>
    <li>Payment Method Breakdown</li>
    <li>Inventory Report</li>
    <li>Profit & Loss Statement</li>
</ul>

<h1>10. System Admin</h1>

<h2>10.1 Business Settings</h2>
<div class="step">
    Go to <em>Business Settings</em> to change:<br>
    • Company name and logo<br>
    • Address and contact info<br>
    • Tax settings (enable/disable, percentage)<br>
    • Currency<br>
    • Receipt footer message<br>
    • Print format (thermal, dot matrix, A4)
</div>

<h2>10.2 Backups</h2>
<div class="step">
    Go to <em>System → Backups</em><br>
    • Click "Full Backup" for manual backup<br>
    • Configure auto-backup schedule<br>
    • Download backup files<br>
    • Restore from backup if needed
</div>

<h2>10.3 User Management</h2>
<div class="step">
    Go to <em>System → Users</em><br>
    • Create new user accounts<br>
    • Assign roles (Cashier, Manager, etc.)<br>
    • Reset passwords<br>
    • Deactivate users
</div>

<h1>11. Troubleshooting</h1>

<h2>Common Issues</h2>
<table>
    <tr><th>Problem</th><th>Solution</th></tr>
    <tr><td>Can't login</td><td>Check username/password. After 5 fails, account locks for 30 min.</td></tr>
    <tr><td>Permission denied</td><td>Your role doesn't have this permission. Contact admin.</td></tr>
    <tr><td>Service has no price</td><td>Go to Services → click $ button → set price.</td></tr>
    <tr><td>Payment doesn't match</td><td>Payment amount must equal order total exactly.</td></tr>
    <tr><td>Can't delete customer</td><td>Customers with orders can only be soft-deleted (moved to trash).</td></tr>
    <tr><td>Receipt not printing</td><td>Check printer is connected. Try different format (thermal/A4).</td></tr>
    <tr><td>Database error</td><td>Contact Super Admin. Check System Health page.</td></tr>
</table>

<div class="cover" style="margin-top:50px;">
    <p><strong>AquaFlow User Manual</strong></p>
    <p>Version 1.0.0 | Powered by Quantum Axis</p>
    <p>© {datetime.now().year} Quantum Axis. All rights reserved.</p>
</div>

</body>
</html>"""

    with open('docs/AquaFlow_User_Manual.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print('✓ User Manual generated: docs/AquaFlow_User_Manual.html')


if __name__ == '__main__':
    os.makedirs('docs', exist_ok=True)
    generate_developer_guide()
    generate_user_manual()
    print('\n✅ All documentation generated!')
    print('   Open the HTML files in a browser and use Ctrl+P to save as PDF.')