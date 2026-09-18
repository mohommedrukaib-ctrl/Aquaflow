"""
AquaFlow Setup Command
Powered by Quantum Axis

Run once after first migration:
    python manage.py setup_aquaflow

Creates:
    - Default business
    - Default branch
    - All roles with permissions
    - Master data (vehicle types, colors, fuel types, etc.)
    - PostgreSQL sequences
    - Super Admin profile assignment
"""

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Initialize AquaFlow with default data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--superuser',
            type=str,
            default='superadmin',
            help='Username of the superuser to assign Super Admin role',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                '\n═══════════════════════════════════════\n'
                '  AquaFlow Setup\n'
                '  Powered by Quantum Axis\n'
                '═══════════════════════════════════════\n'
            )
        )

        with transaction.atomic():
            self._create_sequences()
            self._create_business()
            self._create_branch()
            self._create_roles()
            self._create_vehicle_types()
            self._create_colors()
            self._create_fuel_types()
            self._create_payment_methods()
            self._create_units()
            self._create_expense_categories()
            self._create_employee_positions()
            self._create_wash_bays()
            self._assign_superadmin(options['superuser'])

        self.stdout.write(
            self.style.SUCCESS(
                '\n✅ AquaFlow setup complete!\n'
                '   Run: python manage.py runserver 0.0.0.0:8000\n'
            )
        )

    # ─── PostgreSQL Sequences ──────────────────────────────────

    def _create_sequences(self):
        self.stdout.write('  Creating PostgreSQL sequences...')
        sequences = [
            ('customer_code_seq',    1, 1),
            ('order_number_seq',     1, 1),
            ('invoice_number_seq',   1, 1),
            ('booking_number_seq',   1, 1),
            ('job_number_seq',       1, 1),
            ('job_note_seq',         1, 1),  
            ('purchase_number_seq',  1, 1),
            ('expense_number_seq',   1, 1),
            ('membership_number_seq',1, 1),
            ('employee_code_seq',    1, 1),
        ]
        with connection.cursor() as cursor:
            for seq_name, start, increment in sequences:
                cursor.execute(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_sequences
                            WHERE sequencename = '{seq_name}'
                        ) THEN
                            CREATE SEQUENCE {seq_name}
                                START WITH {start}
                                INCREMENT BY {increment}
                                NO MINVALUE
                                NO MAXVALUE
                                CACHE 1;
                        END IF;
                    END $$;
                """)
                self.stdout.write(f'    ✓ {seq_name}')

    # ─── Business ─────────────────────────────────────────────

    def _create_business(self):
        from apps.businesses.models import Business
        self.stdout.write('  Creating default business...')
        business, created = Business.objects.get_or_create(
            pk=1,
            defaults={
                'name':            'Your Business Name',
                'currency_code':   'LKR',
                'currency_symbol': 'Rs.',
                'currency_name':   'Sri Lankan Rupee',
                'timezone':        'Asia/Colombo',
                'country':         'Sri Lanka',
                'print_format':    'thermal_80mm',
                'receipt_footer':  'Thank you for choosing us!',
            }
        )
        if created:
            self.stdout.write('    ✓ Default business created')
        else:
            self.stdout.write('    → Business already exists')

    # ─── Branch ───────────────────────────────────────────────

    def _create_branch(self):
        from apps.businesses.models import Business
        from apps.branches.models import Branch
        self.stdout.write('  Creating default branch...')
        business = Business.objects.get(pk=1)
        branch, created = Branch.objects.get_or_create(
            code='MAIN',
            defaults={
                'business':   business,
                'name':       'Main Branch',
                'is_default': True,
                'status':     'active',
            }
        )
        if created:
            self.stdout.write('    ✓ Main Branch created')
        else:
            self.stdout.write('    → Branch already exists')

    # ─── Roles ────────────────────────────────────────────────

    def _create_roles(self):
        from apps.accounts.models import (
            Role, RolePermission,
            RoleCode, ROLE_DEFAULT_PERMISSIONS
        )
        self.stdout.write('  Creating roles and permissions...')

        role_definitions = [
            (RoleCode.SUPER_ADMIN,
             'Super Admin',
             'Full system access including database configuration.'),
            (RoleCode.OWNER,
             'Owner',
             'Business owner with full operational access.'),
            (RoleCode.MANAGER,
             'Manager',
             'Branch manager with operational access.'),
            (RoleCode.CASHIER,
             'Cashier',
             'POS access, customer and booking management.'),
            (RoleCode.WASHER,
             'Washer',
             'Wash board access only.'),
            (RoleCode.INVENTORY_MANAGER,
             'Inventory Manager',
             'Inventory and supplier management.'),
            (RoleCode.ACCOUNTANT,
             'Accountant',
             'Finance and reports access.'),
        ]

        for code, name, description in role_definitions:
            role, created = Role.objects.get_or_create(
                code=code,
                defaults={
                    'name':        name,
                    'description': description,
                    'is_system':   True,
                }
            )

            # Assign default permissions
            permissions = ROLE_DEFAULT_PERMISSIONS.get(code, [])
            for perm in permissions:
                RolePermission.objects.get_or_create(
                    role=role,
                    permission=perm,
                )

            self.stdout.write(
                f'    ✓ {name} ({len(permissions)} permissions)'
            )

    # ─── Vehicle Types ────────────────────────────────────────

    def _create_vehicle_types(self):
        from apps.vehicles.models import VehicleType
        self.stdout.write('  Creating vehicle types...')
        types = [
            ('Sedan',         1),
            ('SUV',           2),
            ('Hatchback',     3),
            ('Van',           4),
            ('Pickup Truck',  5),
            ('Motorcycle',    6),
            ('Bus',           7),
            ('Lorry / Truck', 8),
            ('Three-Wheeler', 9),
            ('Other',         99),
        ]
        for name, order in types:
            VehicleType.objects.get_or_create(
                name=name,
                defaults={'sort_order': order}
            )
            self.stdout.write(f'    ✓ {name}')

    # ─── Colors ───────────────────────────────────────────────

    def _create_colors(self):
        from apps.vehicles.models import Color
        self.stdout.write('  Creating colors...')
        colors = [
            ('White',   '#FFFFFF'),
            ('Black',   '#000000'),
            ('Silver',  '#C0C0C0'),
            ('Gray',    '#808080'),
            ('Red',     '#FF0000'),
            ('Blue',    '#0000FF'),
            ('Green',   '#008000'),
            ('Brown',   '#A52A2A'),
            ('Beige',   '#F5F5DC'),
            ('Gold',    '#FFD700'),
            ('Orange',  '#FFA500'),
            ('Yellow',  '#FFFF00'),
            ('Purple',  '#800080'),
            ('Maroon',  '#800000'),
            ('Navy',    '#000080'),
            ('Other',   ''),
        ]
        for name, hex_code in colors:
            Color.objects.get_or_create(
                name=name,
                defaults={'hex_code': hex_code}
            )
            self.stdout.write(f'    ✓ {name}')

    # ─── Fuel Types ───────────────────────────────────────────

    def _create_fuel_types(self):
        from apps.vehicles.models import FuelType
        self.stdout.write('  Creating fuel types...')
        fuels = [
            'Petrol',
            'Diesel',
            'Electric',
            'Hybrid',
            'Plug-in Hybrid',
            'CNG',
            'Other',
        ]
        for name in fuels:
            FuelType.objects.get_or_create(name=name)
            self.stdout.write(f'    ✓ {name}')

    # ─── Payment Methods ──────────────────────────────────────

    def _create_payment_methods(self):
        from apps.payments.models import PaymentMethod
        self.stdout.write('  Creating payment methods...')
        methods = [
            ('Cash',         'CASH',   1),
            ('Card',         'CARD',   2),
            ('Bank Transfer','BANK',   3),
            ('Online',       'ONLINE', 4),
            ('Other',        'OTHER',  9),
        ]
        for name, code, order in methods:
            PaymentMethod.objects.get_or_create(
                code=code,
                defaults={
                    'name':       name,
                    'sort_order': order,
                }
            )
            self.stdout.write(f'    ✓ {name}')

    # ─── Units ────────────────────────────────────────────────

    def _create_units(self):
        from apps.inventory.models import Unit
        self.stdout.write('  Creating units...')
        units = [
            ('Piece',      'pcs'),
            ('Litre',      'L'),
            ('Millilitre', 'ml'),
            ('Kilogram',   'kg'),
            ('Gram',       'g'),
            ('Bottle',     'btl'),
            ('Box',        'box'),
            ('Packet',     'pkt'),
            ('Set',        'set'),
            ('Pair',       'pr'),
        ]
        for name, abbr in units:
            Unit.objects.get_or_create(
                abbreviation=abbr,
                defaults={'name': name}
            )
            self.stdout.write(f'    ✓ {name}')

    # ─── Expense Categories ───────────────────────────────────

    def _create_expense_categories(self):
        from apps.finance.models import ExpenseCategory
        self.stdout.write('  Creating expense categories...')
        categories = [
            ('Salaries & Wages',      1),
            ('Rent & Utilities',      2),
            ('Cleaning Supplies',     3),
            ('Equipment & Machinery', 4),
            ('Fuel',                  5),
            ('Maintenance & Repairs', 6),
            ('Marketing',             7),
            ('Insurance',             8),
            ('Transport',             9),
            ('Office Supplies',       10),
            ('Miscellaneous',         99),
        ]
        for name, order in categories:
            ExpenseCategory.objects.get_or_create(
                name=name,
                defaults={'sort_order': order}
            )
            self.stdout.write(f'    ✓ {name}')

    # ─── Employee Positions ───────────────────────────────────

    def _create_employee_positions(self):
        from apps.employees.models import EmployeePosition
        self.stdout.write('  Creating employee positions...')
        positions = [
            'Manager',
            'Cashier',
            'Car Washer',
            'Detailer',
            'Supervisor',
            'Accountant',
            'Driver',
            'Security',
            'Other',
        ]
        for name in positions:
            EmployeePosition.objects.get_or_create(name=name)
            self.stdout.write(f'    ✓ {name}')

    # ─── Wash Bays ────────────────────────────────────────────

    def _create_wash_bays(self):
        from apps.branches.models import Branch
        from apps.wash.models import WashBay
        self.stdout.write('  Creating default wash bays...')
        branch = Branch.objects.filter(code='MAIN').first()
        if not branch:
            self.stdout.write(
                self.style.WARNING('    ⚠ Branch not found, skipping.')
            )
            return
        bays = [
            ('Bay 1', 'BAY1'),
            ('Bay 2', 'BAY2'),
            ('Bay 3', 'BAY3'),
        ]
        for name, code in bays:
            WashBay.objects.get_or_create(
                branch=branch,
                code=code,
                defaults={'name': name}
            )
            self.stdout.write(f'    ✓ {name}')

    # ─── Super Admin Assignment ───────────────────────────────

    def _assign_superadmin(self, username):
        from apps.accounts.models import Role, UserProfile, RoleCode
        from apps.businesses.models import Business
        from apps.branches.models import Branch

        self.stdout.write(
            f'  Assigning Super Admin role to: {username}...'
        )

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    f'    ⚠ User "{username}" not found.\n'
                    f'      Run: python manage.py createsuperuser\n'
                    f'      Then: python manage.py setup_aquaflow '
                    f'--superuser {username}'
                )
            )
            return

        role     = Role.objects.get(code=RoleCode.SUPER_ADMIN)
        business = Business.objects.get(pk=1)
        branch   = Branch.objects.filter(code='MAIN').first()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role     = role
        profile.business = business
        profile.branch   = branch
        profile.status   = 'active'
        profile.save()

        # Ensure Django superuser flag is set
        if not user.is_superuser:
            user.is_superuser = True
            user.is_staff     = True
            user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'    ✓ {username} assigned as Super Admin'
            )
        )


def handle(self, *args, **options):
    # ... existing code ...
    self._create_service_categories()
    self._create_default_services()
    # ... rest of existing code ...

def _create_service_categories(self):
    from apps.services.models import ServiceCategory
    self.stdout.write('  Creating service categories...')
    cats = [
        ('Exterior Wash',    1),
        ('Interior Cleaning', 2),
        ('Full Detail',       3),
        ('Special Services',  4),
    ]
    for name, order in cats:
        ServiceCategory.objects.get_or_create(
            name=name,
            defaults={'sort_order': order}
        )
        self.stdout.write(f'    ✓ {name}')

def _create_default_services(self):
    from apps.services.models import Service, ServiceCategory
    self.stdout.write('  Creating default services...')

    exterior = ServiceCategory.objects.filter(
        name='Exterior Wash'
    ).first()
    interior = ServiceCategory.objects.filter(
        name='Interior Cleaning'
    ).first()
    full     = ServiceCategory.objects.filter(
        name='Full Detail'
    ).first()

    services = [
        {
            'name':             'Basic Wash',
            'category':         exterior,
            'description':      'Exterior rinse and basic wash.',
            'duration_minutes': 20,
        },
        {
            'name':             'Premium Wash',
            'category':         exterior,
            'description':      'Exterior wash with wax and tire shine.',
            'duration_minutes': 40,
        },
        {
            'name':             'Interior Vacuum',
            'category':         interior,
            'description':      'Full interior vacuum and wipe-down.',
            'duration_minutes': 30,
        },
        {
            'name':             'Full Detail',
            'category':         full,
            'description':      'Complete interior and exterior detail.',
            'duration_minutes': 120,
        },
    ]

    for s in services:
        service, created = Service.objects.get_or_create(
            name=s['name'],
            defaults=s,
        )
        if created:
            self.stdout.write(f"    ✓ {s['name']}")
        else:
            self.stdout.write(f"    → {s['name']} exists")