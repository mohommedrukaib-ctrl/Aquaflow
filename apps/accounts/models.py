"""
AquaFlow — Accounts Models
Powered by Quantum Axis

User profiles, roles and permissions.
Extends Django's built-in auth.User.
"""

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# ─── Role Codes ───────────────────────────────────────────────

class RoleCode(models.TextChoices):
    SUPER_ADMIN        = 'SUPER_ADMIN',        'Super Admin'
    OWNER              = 'OWNER',              'Owner'
    MANAGER            = 'MANAGER',            'Manager'
    CASHIER            = 'CASHIER',            'Cashier'
    WASHER             = 'WASHER',             'Washer'
    INVENTORY_MANAGER  = 'INVENTORY_MANAGER',  'Inventory Manager'
    ACCOUNTANT         = 'ACCOUNTANT',         'Accountant'


# ─── Permission Codes ─────────────────────────────────────────

class PermissionCode(models.TextChoices):
    # Database
    DATABASE_CONFIGURE  = 'database.configure',   'Configure Database'
    DATABASE_TEST       = 'database.test',         'Test Database Connection'
    DATABASE_VIEW       = 'database.view',         'View Database Config'

    # System
    SYSTEM_HEALTH       = 'system.health',         'View System Health'
    SYSTEM_SETTINGS     = 'system.settings',       'Manage System Settings'

    # Backup
    BACKUP_CREATE       = 'backup.create',         'Create Backup'
    BACKUP_VIEW         = 'backup.view',           'View Backups'
    BACKUP_DOWNLOAD     = 'backup.download',       'Download Backup'
    BACKUP_DELETE       = 'backup.delete',         'Delete Backup'
    BACKUP_RESTORE      = 'backup.restore',        'Restore Backup'
    BACKUP_SCHEDULE     = 'backup.schedule',       'Schedule Backups'

    # Trash
    TRASH_VIEW          = 'trash.view',            'View Trash'
    TRASH_RESTORE       = 'trash.restore',         'Restore from Trash'
    TRASH_PERM_DELETE   = 'trash.permanent_delete','Permanently Delete'

    # Audit
    AUDIT_VIEW          = 'audit.view',            'View Audit Logs'

    # Users
    USERS_MANAGE        = 'users.manage',          'Manage Users'
    ROLES_MANAGE        = 'roles.manage',          'Manage Roles'

    # Business
    BUSINESS_CONFIGURE  = 'business.configure',   'Configure Business'
    BRANCH_MANAGE       = 'branch.manage',        'Manage Branches'

    # Customers
    CUSTOMERS_VIEW      = 'customers.view',       'View Customers'
    CUSTOMERS_CREATE    = 'customers.create',     'Create Customers'
    CUSTOMERS_EDIT      = 'customers.edit',       'Edit Customers'
    CUSTOMERS_DELETE    = 'customers.delete',     'Delete Customers'

    # Vehicles
    VEHICLES_VIEW       = 'vehicles.view',        'View Vehicles'
    VEHICLES_CREATE     = 'vehicles.create',      'Create Vehicles'
    VEHICLES_EDIT       = 'vehicles.edit',        'Edit Vehicles'
    VEHICLES_DELETE     = 'vehicles.delete',      'Delete Vehicles'

    # Services
    SERVICES_VIEW       = 'services.view',        'View Services'
    SERVICES_MANAGE     = 'services.manage',      'Manage Services'

    # POS
    POS_ACCESS          = 'pos.access',           'Access POS'
    POS_DISCOUNT        = 'pos.discount',         'Apply Discounts'
    POS_REFUND          = 'pos.refund',           'Process Refunds'

    # Orders
    ORDERS_VIEW         = 'orders.view',          'View Orders'
    ORDERS_VOID         = 'orders.void',          'Void Orders'

    # Invoices
    INVOICES_VIEW       = 'invoices.view',        'View Invoices'
    INVOICES_VOID       = 'invoices.void',        'Void Invoices'

    # Inventory
    INVENTORY_VIEW      = 'inventory.view',       'View Inventory'
    INVENTORY_MANAGE    = 'inventory.manage',     'Manage Inventory'
    INVENTORY_ADJUST    = 'inventory.adjust',     'Adjust Stock'

    # Suppliers
    SUPPLIERS_VIEW      = 'suppliers.view',       'View Suppliers'
    SUPPLIERS_MANAGE    = 'suppliers.manage',     'Manage Suppliers'

    # Employees
    EMPLOYEES_VIEW      = 'employees.view',       'View Employees'
    EMPLOYEES_MANAGE    = 'employees.manage',     'Manage Employees'

    # Finance
    FINANCE_VIEW        = 'finance.view',         'View Finance'
    FINANCE_MANAGE      = 'finance.manage',       'Manage Expenses'

    # Reports
    REPORTS_VIEW        = 'reports.view',         'View Reports'
    REPORTS_EXPORT      = 'reports.export',       'Export Reports'

    # Wash
    WASH_VIEW           = 'wash.view',            'View Wash Board'
    WASH_MANAGE         = 'wash.manage',          'Manage Wash Jobs'

    # Bookings
    BOOKINGS_VIEW       = 'bookings.view',        'View Bookings'
    BOOKINGS_MANAGE     = 'bookings.manage',      'Manage Bookings'

    # Memberships
    MEMBERSHIPS_VIEW    = 'memberships.view',     'View Memberships'
    MEMBERSHIPS_MANAGE  = 'memberships.manage',   'Manage Memberships'


# ─── Default Permissions Per Role ─────────────────────────────

ROLE_DEFAULT_PERMISSIONS = {

    RoleCode.SUPER_ADMIN: [p.value for p in PermissionCode],  # ALL

    RoleCode.OWNER: [
        PermissionCode.SYSTEM_HEALTH,
        PermissionCode.BACKUP_CREATE,
        PermissionCode.BACKUP_VIEW,
        PermissionCode.BACKUP_DOWNLOAD,
        PermissionCode.AUDIT_VIEW,
        PermissionCode.USERS_MANAGE,
        PermissionCode.BUSINESS_CONFIGURE,
        PermissionCode.BRANCH_MANAGE,
        PermissionCode.CUSTOMERS_VIEW,
        PermissionCode.CUSTOMERS_CREATE,
        PermissionCode.CUSTOMERS_EDIT,
        PermissionCode.CUSTOMERS_DELETE,
        PermissionCode.VEHICLES_VIEW,
        PermissionCode.VEHICLES_CREATE,
        PermissionCode.VEHICLES_EDIT,
        PermissionCode.VEHICLES_DELETE,
        PermissionCode.SERVICES_VIEW,
        PermissionCode.SERVICES_MANAGE,
        PermissionCode.POS_ACCESS,
        PermissionCode.POS_DISCOUNT,
        PermissionCode.POS_REFUND,
        PermissionCode.ORDERS_VIEW,
        PermissionCode.ORDERS_VOID,
        PermissionCode.INVOICES_VIEW,
        PermissionCode.INVOICES_VOID,
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_MANAGE,
        PermissionCode.INVENTORY_ADJUST,
        PermissionCode.SUPPLIERS_VIEW,
        PermissionCode.SUPPLIERS_MANAGE,
        PermissionCode.EMPLOYEES_VIEW,
        PermissionCode.EMPLOYEES_MANAGE,
        PermissionCode.FINANCE_VIEW,
        PermissionCode.FINANCE_MANAGE,
        PermissionCode.REPORTS_VIEW,
        PermissionCode.REPORTS_EXPORT,
        PermissionCode.WASH_VIEW,
        PermissionCode.WASH_MANAGE,
        PermissionCode.BOOKINGS_VIEW,
        PermissionCode.BOOKINGS_MANAGE,
        PermissionCode.MEMBERSHIPS_VIEW,
        PermissionCode.MEMBERSHIPS_MANAGE,
        PermissionCode.TRASH_VIEW,
    ],

    RoleCode.MANAGER: [
        PermissionCode.CUSTOMERS_VIEW,
        PermissionCode.CUSTOMERS_CREATE,
        PermissionCode.CUSTOMERS_EDIT,
        PermissionCode.CUSTOMERS_DELETE,
        PermissionCode.VEHICLES_VIEW,
        PermissionCode.VEHICLES_CREATE,
        PermissionCode.VEHICLES_EDIT,
        PermissionCode.VEHICLES_DELETE,
        PermissionCode.SERVICES_VIEW,
        PermissionCode.SERVICES_MANAGE,
        PermissionCode.POS_ACCESS,
        PermissionCode.POS_DISCOUNT,
        PermissionCode.POS_REFUND,
        PermissionCode.ORDERS_VIEW,
        PermissionCode.INVOICES_VIEW,
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_MANAGE,
        PermissionCode.INVENTORY_ADJUST,
        PermissionCode.SUPPLIERS_VIEW,
        PermissionCode.EMPLOYEES_VIEW,
        PermissionCode.FINANCE_VIEW,
        PermissionCode.FINANCE_MANAGE,
        PermissionCode.REPORTS_VIEW,
        PermissionCode.WASH_VIEW,
        PermissionCode.WASH_MANAGE,
        PermissionCode.BOOKINGS_VIEW,
        PermissionCode.BOOKINGS_MANAGE,
        PermissionCode.MEMBERSHIPS_VIEW,
        PermissionCode.MEMBERSHIPS_MANAGE,
    ],

    RoleCode.CASHIER: [
        PermissionCode.CUSTOMERS_VIEW,
        PermissionCode.CUSTOMERS_CREATE,
        PermissionCode.CUSTOMERS_EDIT,
        PermissionCode.VEHICLES_VIEW,
        PermissionCode.VEHICLES_CREATE,
        PermissionCode.SERVICES_VIEW,
        PermissionCode.POS_ACCESS,
        PermissionCode.ORDERS_VIEW,
        PermissionCode.INVOICES_VIEW,
        PermissionCode.WASH_VIEW,
        PermissionCode.BOOKINGS_VIEW,
        PermissionCode.BOOKINGS_MANAGE,
        PermissionCode.MEMBERSHIPS_VIEW,
    ],

    RoleCode.WASHER: [
        PermissionCode.WASH_VIEW,
        PermissionCode.WASH_MANAGE,
        PermissionCode.CUSTOMERS_VIEW,
        PermissionCode.VEHICLES_VIEW,
    ],

    RoleCode.INVENTORY_MANAGER: [
        PermissionCode.INVENTORY_VIEW,
        PermissionCode.INVENTORY_MANAGE,
        PermissionCode.INVENTORY_ADJUST,
        PermissionCode.SUPPLIERS_VIEW,
        PermissionCode.SUPPLIERS_MANAGE,
        PermissionCode.REPORTS_VIEW,
    ],

    RoleCode.ACCOUNTANT: [
        PermissionCode.ORDERS_VIEW,
        PermissionCode.INVOICES_VIEW,
        PermissionCode.FINANCE_VIEW,
        PermissionCode.FINANCE_MANAGE,
        PermissionCode.REPORTS_VIEW,
        PermissionCode.REPORTS_EXPORT,
        PermissionCode.CUSTOMERS_VIEW,
    ],
}


# ─── Role Model ───────────────────────────────────────────────

class Role(models.Model):

    code = models.CharField(
        max_length=50,
        unique=True,
        choices=RoleCode.choices,
    )
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system   = models.BooleanField(
        default=True,
        help_text='System roles cannot be deleted.',
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'roles'
        verbose_name        = 'Role'
        verbose_name_plural = 'Roles'
        ordering            = ['name']

    def __str__(self):
        return self.name

    def get_permissions(self):
        return list(
            self.role_permissions.values_list('permission', flat=True)
        )

    def has_permission(self, permission_code):
        return self.role_permissions.filter(
            permission=permission_code
        ).exists()


# ─── Role Permission Model ────────────────────────────────────

class RolePermission(models.Model):

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions',
    )
    permission = models.CharField(
        max_length=100,
        choices=PermissionCode.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'role_permissions'
        unique_together     = ('role', 'permission')
        verbose_name        = 'Role Permission'
        verbose_name_plural = 'Role Permissions'

    def __str__(self):
        return f'{self.role.name} → {self.permission}'


# ─── User Profile Model ───────────────────────────────────────

class UserProfile(models.Model):

    STATUS_ACTIVE   = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_SUSPENDED = 'suspended'

    STATUS_CHOICES = [
        (STATUS_ACTIVE,    'Active'),
        (STATUS_INACTIVE,  'Inactive'),
        (STATUS_SUSPENDED, 'Suspended'),
    ]

    # ─── Core ─────────────────────────────────────────────────
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True,
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # ─── Contact ──────────────────────────────────────────────
    phone  = models.CharField(max_length=50, blank=True)
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
    )

    # ─── Status ───────────────────────────────────────────────
    status     = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'user_profiles'
        verbose_name        = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return (
            f'{self.user.get_full_name() or self.user.username}'
            f' ({self.role})'
        )

    def has_permission(self, permission_code):
        """
        Check if this user has a specific permission.
        Super Admin always returns True.
        """
        if not self.role:
            return False
        if self.role.code == RoleCode.SUPER_ADMIN:
            return True
        return self.role.has_permission(permission_code)

    def is_super_admin(self):
        return (
            self.role and
            self.role.code == RoleCode.SUPER_ADMIN
        )


# ─── Auto-create Profile on User Creation ─────────────────────

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()