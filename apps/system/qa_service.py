"""
AquaFlow — QA / Integrity / Diagnostics Service
Powered by Quantum Axis

Runs comprehensive checks to verify system integrity.
"""

import logging
from decimal import Decimal
from django.db import connection
from django.utils import timezone

logger = logging.getLogger('apps')


class QAService:
    """Runs system integrity + data consistency checks."""

    def __init__(self):
        self.results = []
        self.errors = 0
        self.warnings = 0
        self.passed = 0

    def add_result(self, category, name, status, message='', details=''):
        """status: 'pass' | 'warning' | 'fail'"""
        self.results.append({
            'category': category,
            'name':     name,
            'status':   status,
            'message':  message,
            'details':  details,
        })
        if status == 'pass':
            self.passed += 1
        elif status == 'warning':
            self.warnings += 1
        elif status == 'fail':
            self.errors += 1

    # ─── DATABASE INTEGRITY ────────────────────────────────

    def check_database_connection(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
            self.add_result(
                'Database', 'Connection', 'pass',
                'PostgreSQL connection working.'
            )
        except Exception as e:
            self.add_result(
                'Database', 'Connection', 'fail',
                f'Cannot connect: {e}'
            )

    def check_required_tables(self):
        """Verify all critical tables exist."""
        required = [
            'businesses', 'branches', 'customers', 'vehicles',
            'services', 'service_prices', 'bookings',
            'orders', 'invoices', 'invoice_items', 'payments',
            'products', 'inventory_stock', 'inventory_transactions',
            'wash_jobs', 'audit_logs',
        ]

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                """)
                existing = {row[0] for row in cursor.fetchall()}

            missing = [t for t in required if t not in existing]

            if missing:
                self.add_result(
                    'Database', 'Required Tables', 'fail',
                    f'{len(missing)} tables missing: {", ".join(missing)}',
                )
            else:
                self.add_result(
                    'Database', 'Required Tables', 'pass',
                    f'All {len(required)} critical tables present.'
                )
        except Exception as e:
            self.add_result(
                'Database', 'Required Tables', 'fail', str(e)
            )

    def check_sequences(self):
        """Verify PostgreSQL sequences exist."""
        required_seqs = [
            'customer_code_seq',
            'order_number_seq',
            'invoice_number_seq',
            'booking_number_seq',
            'job_number_seq',
            'purchase_number_seq',
            'expense_number_seq',
            'membership_number_seq',
            'employee_code_seq',
        ]

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT sequence_name FROM information_schema.sequences
                    WHERE sequence_schema = 'public'
                """)
                existing = {row[0] for row in cursor.fetchall()}

            missing = [s for s in required_seqs if s not in existing]

            if missing:
                self.add_result(
                    'Database', 'Sequences', 'fail',
                    f'{len(missing)} sequences missing: {", ".join(missing)}',
                )
            else:
                self.add_result(
                    'Database', 'Sequences', 'pass',
                    f'All {len(required_seqs)} sequences present.'
                )
        except Exception as e:
            self.add_result(
                'Database', 'Sequences', 'fail', str(e)
            )

    def check_migrations(self):
        """Check for pending migrations."""
        try:
            from django.db.migrations.executor import MigrationExecutor
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            plan = executor.migration_plan(targets)

            if plan:
                self.add_result(
                    'Database', 'Migrations', 'warning',
                    f'{len(plan)} pending migrations. Run: python manage.py migrate'
                )
            else:
                self.add_result(
                    'Database', 'Migrations', 'pass',
                    'All migrations applied.'
                )
        except Exception as e:
            self.add_result(
                'Database', 'Migrations', 'fail', str(e)
            )

    # ─── DATA INTEGRITY ────────────────────────────────────

    def check_orphaned_invoices(self):
        """Check for invoices without orders."""
        try:
            from apps.invoices.models import Invoice
            orphans = Invoice.objects.filter(order__isnull=True).count()
            if orphans:
                self.add_result(
                    'Data', 'Orphaned Invoices', 'fail',
                    f'{orphans} invoices with no order.'
                )
            else:
                self.add_result(
                    'Data', 'Orphaned Invoices', 'pass',
                    'All invoices linked to orders.'
                )
        except Exception as e:
            self.add_result(
                'Data', 'Orphaned Invoices', 'warning', str(e)
            )

    def check_invoice_totals(self):
        """Verify invoice totals match item sums."""
        try:
            from apps.invoices.models import Invoice
            from django.db.models import Sum

            mismatches = 0
            invoices = Invoice.objects.filter(
                status='paid'
            ).prefetch_related('items')[:100]

            for inv in invoices:
                item_total = inv.items.aggregate(
                    Sum('line_total')
                )['line_total__sum'] or Decimal('0')

                # Allow 1 cent tolerance for currency rounding
                expected = inv.subtotal - inv.discount_amount + inv.tax_amount
                if abs(item_total - inv.total) > Decimal('0.01'):
                    mismatches += 1

            if mismatches:
                self.add_result(
                    'Data', 'Invoice Totals', 'warning',
                    f'{mismatches} invoices with total mismatch (rounding).'
                )
            else:
                self.add_result(
                    'Data', 'Invoice Totals', 'pass',
                    'Invoice totals match line items.'
                )
        except Exception as e:
            self.add_result(
                'Data', 'Invoice Totals', 'warning', str(e)
            )
    def check_payment_vs_invoice(self):
        """Verify paid invoices have matching payments."""
        try:
            from apps.invoices.models import Invoice
            from django.db.models import Sum

            issues = 0
            invoices = Invoice.objects.filter(
                status='paid'
            ).prefetch_related('payments')[:100]

            for inv in invoices:
                paid = inv.payments.filter(
                    status='completed'
                ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

                if abs(paid - inv.total) > Decimal('1'):
                    issues += 1

            if issues:
                self.add_result(
                    'Data', 'Payment Totals', 'warning',
                    f'{issues} paid invoices with payment mismatch.'
                )
            else:
                self.add_result(
                    'Data', 'Payment Totals', 'pass',
                    'Payments match invoice totals.'
                )
        except Exception as e:
            self.add_result(
                'Data', 'Payment Totals', 'warning', str(e)
            )

    def check_customer_vehicle_orphans(self):
        """Check for vehicles with deleted customers."""
        try:
            from apps.vehicles.models import Vehicle
            orphans = Vehicle.objects.filter(
                customer__is_deleted=True,
                is_deleted=False,
            ).count()

            if orphans:
                self.add_result(
                    'Data', 'Vehicle Ownership', 'warning',
                    f'{orphans} active vehicles have deleted owners.'
                )
            else:
                self.add_result(
                    'Data', 'Vehicle Ownership', 'pass',
                    'All active vehicles have valid owners.'
                )
        except Exception as e:
            self.add_result(
                'Data', 'Vehicle Ownership', 'warning', str(e)
            )

    def check_negative_stock(self):
        """Check for negative inventory quantities."""
        try:
            from apps.inventory.models import InventoryStock
            negative = InventoryStock.objects.filter(quantity__lt=0)

            if negative.exists():
                items = [f'{s.product.name}: {s.quantity}' for s in negative[:5]]
                self.add_result(
                    'Data', 'Negative Stock', 'warning',
                    f'{negative.count()} items with negative stock.',
                    ', '.join(items),
                )
            else:
                self.add_result(
                    'Data', 'Negative Stock', 'pass',
                    'No negative inventory values.'
                )
        except Exception as e:
            self.add_result(
                'Data', 'Negative Stock', 'warning', str(e)
            )

    # ─── SECURITY ─────────────────────────────────────────

    def check_super_admin(self):
        """Verify at least one Super Admin exists."""
        try:
            from apps.accounts.models import UserProfile, RoleCode
            super_admins = UserProfile.objects.filter(
                role__code=RoleCode.SUPER_ADMIN,
                status='active',
            ).count()

            if super_admins == 0:
                self.add_result(
                    'Security', 'Super Admin', 'fail',
                    'No active Super Admin. Run: python manage.py setup_aquaflow --superuser <username>'
                )
            elif super_admins == 1:
                self.add_result(
                    'Security', 'Super Admin', 'pass',
                    '1 Super Admin configured.'
                )
            else:
                self.add_result(
                    'Security', 'Super Admin', 'warning',
                    f'{super_admins} Super Admins exist. Review necessity.'
                )
        except Exception as e:
            self.add_result(
                'Security', 'Super Admin', 'warning', str(e)
            )

    def check_default_business(self):
        try:
            from apps.businesses.models import Business
            biz = Business.objects.filter(pk=1).first()
            if not biz:
                self.add_result(
                    'Setup', 'Business Config', 'fail',
                    'No business configured. Run setup_aquaflow.'
                )
            elif biz.name == 'Your Business Name':
                self.add_result(
                    'Setup', 'Business Config', 'warning',
                    'Business name still default. Update at /business/'
                )
            else:
                self.add_result(
                    'Setup', 'Business Config', 'pass',
                    f'Configured: {biz.name}'
                )
        except Exception as e:
            self.add_result(
                'Setup', 'Business Config', 'fail', str(e)
            )

    def check_default_branch(self):
        try:
            from apps.branches.models import Branch
            branch = Branch.objects.filter(is_default=True).first()
            if not branch:
                self.add_result(
                    'Setup', 'Default Branch', 'fail',
                    'No default branch. Run setup_aquaflow.'
                )
            else:
                self.add_result(
                    'Setup', 'Default Branch', 'pass',
                    f'Default: {branch.name}'
                )
        except Exception as e:
            self.add_result(
                'Setup', 'Default Branch', 'fail', str(e)
            )

    def check_payment_methods(self):
        try:
            from apps.payments.models import PaymentMethod
            active = PaymentMethod.objects.filter(is_active=True).count()
            if active == 0:
                self.add_result(
                    'Setup', 'Payment Methods', 'fail',
                    'No active payment methods.'
                )
            else:
                self.add_result(
                    'Setup', 'Payment Methods', 'pass',
                    f'{active} active payment methods.'
                )
        except Exception as e:
            self.add_result(
                'Setup', 'Payment Methods', 'fail', str(e)
            )

    # ─── BACKUPS ──────────────────────────────────────────

    def check_recent_backup(self):
        try:
            from apps.backups.models import BackupRecord
            from datetime import timedelta

            recent = BackupRecord.objects.filter(
                status='success',
                started_at__gte=timezone.now() - timedelta(days=7),
            ).count()

            if recent == 0:
                self.add_result(
                    'Backups', 'Recent Backup', 'warning',
                    'No successful backup in last 7 days.'
                )
            else:
                self.add_result(
                    'Backups', 'Recent Backup', 'pass',
                    f'{recent} backups in last 7 days.'
                )
        except Exception as e:
            self.add_result(
                'Backups', 'Recent Backup', 'warning', str(e)
            )

    def check_backup_schedule(self):
        try:
            from apps.backups.models import BackupSchedule
            schedule = BackupSchedule.objects.filter(pk=1).first()
            if not schedule or not schedule.enabled:
                self.add_result(
                    'Backups', 'Auto-Backup', 'warning',
                    'Auto-backup disabled. Enable at /system/backups/schedule/'
                )
            else:
                self.add_result(
                    'Backups', 'Auto-Backup', 'pass',
                    f'Enabled: {schedule.get_frequency_display()}'
                )
        except Exception as e:
            self.add_result(
                'Backups', 'Auto-Backup', 'warning', str(e)
            )

    def check_pg_dump(self):
        try:
            from apps.backups.services import BackupService
            info = BackupService.get_system_info()
            if info['sql_available']:
                self.add_result(
                    'Backups', 'pg_dump', 'pass',
                    f'Found at: {info["pg_dump"]}'
                )
            else:
                self.add_result(
                    'Backups', 'pg_dump', 'warning',
                    'pg_dump not found. SQL backups unavailable.'
                )
        except Exception as e:
            self.add_result(
                'Backups', 'pg_dump', 'warning', str(e)
            )

    # ─── SETTINGS ─────────────────────────────────────────

    def check_debug_mode(self):
        try:
            from django.conf import settings
            if settings.DEBUG:
                self.add_result(
                    'Security', 'Debug Mode', 'warning',
                    'DEBUG=True. Turn off in production for security.'
                )
            else:
                self.add_result(
                    'Security', 'Debug Mode', 'pass',
                    'DEBUG=False (production ready).'
                )
        except Exception as e:
            self.add_result(
                'Security', 'Debug Mode', 'warning', str(e)
            )

    def check_secret_key(self):
        try:
            from django.conf import settings
            key = settings.SECRET_KEY
            if 'change' in key.lower() or 'insecure' in key.lower():
                self.add_result(
                    'Security', 'Secret Key', 'fail',
                    'Default/insecure SECRET_KEY. Change in .env'
                )
            elif len(key) < 40:
                self.add_result(
                    'Security', 'Secret Key', 'warning',
                    'SECRET_KEY is short. Should be 50+ characters.'
                )
            else:
                self.add_result(
                    'Security', 'Secret Key', 'pass',
                    'Secret key is strong.'
                )
        except Exception as e:
            self.add_result(
                'Security', 'Secret Key', 'warning', str(e)
            )

    def check_allowed_hosts(self):
        try:
            from django.conf import settings
            if '*' in settings.ALLOWED_HOSTS:
                self.add_result(
                    'Security', 'Allowed Hosts', 'warning',
                    'ALLOWED_HOSTS = ["*"]. Restrict in production.'
                )
            elif not settings.ALLOWED_HOSTS:
                self.add_result(
                    'Security', 'Allowed Hosts', 'fail',
                    'ALLOWED_HOSTS is empty.'
                )
            else:
                self.add_result(
                    'Security', 'Allowed Hosts', 'pass',
                    f'{len(settings.ALLOWED_HOSTS)} hosts configured.'
                )
        except Exception as e:
            self.add_result(
                'Security', 'Allowed Hosts', 'warning', str(e)
            )

    # ─── RUN ALL ──────────────────────────────────────────

    def run_all(self):
        """Run all QA checks."""

        # Database
        self.check_database_connection()
        self.check_required_tables()
        self.check_sequences()
        self.check_migrations()

        # Data
        self.check_orphaned_invoices()
        self.check_invoice_totals()
        self.check_payment_vs_invoice()
        self.check_customer_vehicle_orphans()
        self.check_negative_stock()

        # Setup
        self.check_default_business()
        self.check_default_branch()
        self.check_payment_methods()
        self.check_super_admin()

        # Backups
        self.check_recent_backup()
        self.check_backup_schedule()
        self.check_pg_dump()

        # Security
        self.check_debug_mode()
        self.check_secret_key()
        self.check_allowed_hosts()

        return {
            'results':   self.results,
            'passed':    self.passed,
            'warnings':  self.warnings,
            'errors':    self.errors,
            'total':     len(self.results),
            'timestamp': timezone.now(),
        }