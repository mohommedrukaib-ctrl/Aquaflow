"""
AquaFlow — Finance / Expense Models
Powered by Quantum Axis
"""

from django.db import models, connection
from django.contrib.auth.models import User


class ExpenseCategory(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    sort_order  = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'expense_categories'
        ordering            = ['sort_order', 'name']
        verbose_name        = 'Expense Category'
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return self.name


class Expense(models.Model):

    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING,  'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    expense_number = models.CharField(
        max_length=30, unique=True, editable=False,
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='expenses',
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.PROTECT,
        related_name='expenses',
    )

    amount        = models.DecimalField(max_digits=12, decimal_places=2)
    description   = models.CharField(max_length=255)
    expense_date  = models.DateField(db_index=True)
    payment_method = models.ForeignKey(
        'payments.PaymentMethod',
        on_delete=models.PROTECT,
        related_name='expenses',
        null=True, blank=True,
    )
    receipt_image  = models.ImageField(
        upload_to='expenses/receipts/',
        null=True, blank=True,
    )
    notes         = models.TextField(blank=True)

    status      = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_APPROVED,
    )
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_expenses',
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_expenses',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expenses'
        ordering = ['-expense_date', '-created_at']
        indexes  = [
            models.Index(fields=['expense_date']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.expense_number} — {self.description}'

    def save(self, *args, **kwargs):
        if not self.expense_number:
            with connection.cursor() as cursor:
                cursor.execute("SELECT nextval('expense_number_seq')")
                num = cursor.fetchone()[0]
            self.expense_number = f'EXP-{num:06d}'
        super().save(*args, **kwargs)