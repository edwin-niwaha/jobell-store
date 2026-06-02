from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .middleware import get_current_user
from django.db import models


class AuditableModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        verbose_name=_("Created By"),
    )

    class Meta:
        abstract = True

    def save(self, *args, user=None, **kwargs):
        if not self.pk and not self.created_by:
            # Use provided user or fall back to thread-local user
            self.created_by = user or get_current_user()
        super().save(*args, **kwargs)


class Branch(AuditableModel):  # Inherit from AuditableModel
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    code = models.CharField(max_length=20, unique=True, verbose_name=_("Code"))

    class Meta:
        verbose_name = _("Branch")
        verbose_name_plural = _("Branches")
        ordering = ["name"]
        indexes = [models.Index(fields=["code"], name="branch_code_idx")]

    def __str__(self):
        return self.name


class FinancialPeriod(AuditableModel):  # Inherit from AuditableModel
    name = models.CharField(max_length=100, verbose_name=_("Period Name"))
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"))
    status = models.CharField(
        max_length=20,
        choices=[
            ("open", "Open"),
            ("closed", "Closed"),
            ("locked", "Locked"),
        ],
        default="open",
        verbose_name=_("Status"),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="financial_periods",
        verbose_name=_("Branch"),
    )

    class Meta:
        verbose_name = _("Financial Period")
        verbose_name_plural = _("Financial Periods")
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["branch", "status"], name="period_branch_status_idx"),
            models.Index(fields=["start_date", "end_date"], name="period_date_range_idx"),
            models.Index(fields=["status", "start_date"], name="period_status_start_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"

    def clean(self):
        # Ensure end_date is after start_date
        if self.end_date <= self.start_date:
            raise ValidationError(_("End date must be after start date."))
        # Ensure no overlapping periods for the same branch
        overlapping = FinancialPeriod.objects.filter(
            branch=self.branch,
            start_date__lte=self.end_date,
            end_date__gte=self.start_date,
        ).exclude(id=self.id)
        if overlapping.exists():
            raise ValidationError(
                _("Overlapping financial periods are not allowed for the same branch.")
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)  # Call AuditableModel's save method


# =================================== ChartOfAccounts Model ===================================
class ChartOfAccounts(AuditableModel):
    ACCOUNT_TYPE_CHOICES = [
        ("asset", "Asset"),
        ("liability", "Liability"),
        ("equity", "Equity"),
        ("revenue", "Revenue"),
        ("expense", "Expense"),
    ]

    BALANCE_TYPE_CHOICES = [
        ("debit", "Debit"),
        ("credit", "Credit"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("closed", "Closed"),
    ]

    account_name = models.CharField(max_length=255, verbose_name="Account Name")
    account_type = models.CharField(
        max_length=50, choices=ACCOUNT_TYPE_CHOICES, verbose_name="Account Type"
    )
    account_number = models.CharField(
        max_length=20, unique=True, verbose_name="Account Number"
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    balance_type = models.CharField(
        max_length=10, choices=BALANCE_TYPE_CHOICES, verbose_name="Balance Type"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active", verbose_name="Status"
    )
    parent_account = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_accounts",
        verbose_name="Parent Account",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounts",
        verbose_name=_("Branch"),
    )
    is_deleted = models.BooleanField(default=False, verbose_name=_("Is Deleted"))
    is_contra_asset = models.BooleanField(default=False, verbose_name="Is Contra-Asset")

    class Meta:
        verbose_name = "Chart of Account"
        verbose_name_plural = "Chart of Accounts"
        ordering = ["account_number"]
        db_table = "accounts"
        indexes = [
            models.Index(fields=["account_number"], name="coa_account_number_idx"),
            models.Index(fields=["account_type", "status"], name="coa_type_status_idx"),
            models.Index(fields=["branch", "status"], name="coa_branch_status_idx"),
            models.Index(fields=["parent_account"], name="coa_parent_idx"),
            models.Index(fields=["is_deleted", "status"], name="coa_deleted_status_idx"),
        ]

    def __str__(self):
        return f"{self.account_name} ({self.get_account_type_display()})"

    def clean(self):
        # Validate account number is numeric
        if not self.account_number.isdigit():
            raise ValidationError(
                "Account number must contain only numeric characters."
            )

        # Validate account type
        if self.account_type not in dict(self.ACCOUNT_TYPE_CHOICES).keys():
            raise ValidationError(f"Invalid account type: {self.account_type}")

        # Validate balance type
        if self.balance_type not in dict(self.BALANCE_TYPE_CHOICES).keys():
            raise ValidationError(f"Invalid balance type: {self.balance_type}")

        # Validate status
        if self.status not in dict(self.STATUS_CHOICES).keys():
            raise ValidationError(f"Invalid status: {self.status}")

        # Validate parent account hierarchy
        if self.parent_account and self.parent_account == self:
            raise ValidationError("An account cannot be its own parent.")

        # Ensure balance type aligns with account type, with exception for contra-assets
        valid_balance_types = {
            "asset": "debit",
            "expense": "debit",
            "liability": "credit",
            "equity": "credit",
            "revenue": "credit",
        }
        is_contra_asset = (
            self.account_name
            and "accumulated depreciation" in self.account_name.lower()
        )
        if is_contra_asset and self.balance_type != "credit":
            raise ValidationError(
                f"Contra-asset account '{self.account_name}' must have credit balance type."
            )
        elif (
            not is_contra_asset
            and valid_balance_types.get(self.account_type) != self.balance_type
        ):
            raise ValidationError(
                f"Account type {self.account_type} must have {valid_balance_types.get(self.account_type)} balance type."
            )

        # Prevent circular parent account references
        if self.parent_account:
            current = self.parent_account
            visited = {self.id}
            while current:
                if current.id in visited:
                    raise ValidationError("Circular parent account reference detected.")
                visited.add(current.id)
                current = current.parent_account


# =================================== Transaction Model ===================================
TRANSACTION_TYPE_CHOICES = [
    ("debit", "Debit"),
    ("credit", "Credit"),
]

PAYMENT_METHOD_CHOICES = [
    ("cash", "Cash"),
    ("bank_transfer", "Bank Transfer"),
    ("mobile_money", "Mobile Money"),
    ("cheque", "Cheque"),
    ("other", "Other"),
]


class JournalEntry(AuditableModel):
    reference_number = models.CharField(
        max_length=100, unique=True, verbose_name="Voucher / Receipt Number"
    )
    transaction_date = models.DateField(verbose_name="Date of Transaction")
    description = models.TextField(null=True, blank=True, verbose_name="Narration")
    source = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Source (for Income)"
    )
    payee = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Payee (for Expense)"
    )
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True
    )
    financial_period = models.ForeignKey(
        FinancialPeriod,
        on_delete=models.PROTECT,
        related_name="journal_entries",
        verbose_name=_("Financial Period"),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="journal_entries",
        verbose_name=_("Branch"),
    )

    class Meta:
        ordering = ["-transaction_date", "-id"]
        indexes = [
            models.Index(fields=["reference_number"], name="journal_reference_idx"),
            models.Index(fields=["transaction_date"], name="journal_date_idx"),
            models.Index(fields=["financial_period", "transaction_date"], name="journal_period_date_idx"),
            models.Index(fields=["branch", "transaction_date"], name="journal_branch_date_idx"),
            models.Index(fields=["payment_method"], name="journal_payment_method_idx"),
        ]

    def __str__(self):
        return f"Journal Entry #{self.reference_number} on {self.transaction_date}"

    def clean(self):
        errors = {}

        # Ensure financial_period is provided
        if not self.financial_period:
            errors["financial_period"] = _("Financial period is required.")
        else:
            # Ensure financial period is open
            if self.financial_period.status != "open":
                errors["financial_period"] = _(
                    "Cannot post to a closed or locked financial period."
                )

            # Check for valid date boundaries if both dates are present
            if (
                self.financial_period.start_date
                and self.financial_period.end_date
                and self.transaction_date
            ):
                if not (
                    self.financial_period.start_date
                    <= self.transaction_date
                    <= self.financial_period.end_date
                ):
                    errors["transaction_date"] = _(
                        "Transaction date must be within the financial period's date range."
                    )

        # Raise validation errors if any
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Transaction(AuditableModel):
    journal_entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, related_name="transactions"
    )
    account = models.ForeignKey("ChartOfAccounts", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)

    class Meta:
        indexes = [
            models.Index(fields=["journal_entry", "transaction_type"], name="txn_journal_type_idx"),
            models.Index(fields=["account", "transaction_type"], name="txn_account_type_idx"),
        ]

    def __str__(self):
        return f"{self.transaction_type.title()} {self.amount} ({self.account})"
