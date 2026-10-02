from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Branch, ChartOfAccounts, JournalEntry, Transaction, FinancialPeriod


# Register Branch model
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")
    list_filter = ("name",)
    ordering = ("name",)


# Register FinancialPeriod model
@admin.register(FinancialPeriod)
class FinancialPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "status", "branch", "created_at")
    search_fields = ("name",)
    list_filter = ("status", "branch", "start_date")
    date_hierarchy = "start_date"
    ordering = ("-start_date",)
    list_per_page = 25

    fieldsets = (
        (None, {"fields": ("name", "start_date", "end_date", "status")}),
        (
            _("Additional Information"),
            {
                "fields": ("branch", "created_by"),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("start_date", "end_date")
        return ()


# Register ChartOfAccounts model
@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(admin.ModelAdmin):
    list_display = (
        "account_name",
        "account_number",
        "account_type",
        "balance_type",
        "status",
        "branch",
        "is_deleted",
    )
    list_filter = (
        "account_type",
        "balance_type",
        "status",
        "branch",
        "is_deleted",
        "is_contra_asset",
    )
    search_fields = ("account_name", "account_number", "description")
    list_editable = ("status",)
    ordering = ("account_number",)
    raw_id_fields = (
        "parent_account",
        "branch",
    )  # For better performance with ForeignKey fields
    list_per_page = 25

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "account_name",
                    "account_number",
                    "account_type",
                    "balance_type",
                )
            },
        ),
        (
            _("Additional Information"),
            {
                "fields": (
                    "description",
                    "status",
                    "parent_account",
                    "branch",
                    "is_deleted",
                    "is_contra_asset",
                ),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        # Make account_number read-only if the object already exists
        if obj:
            return ("account_number",)
        return ()


# Register JournalEntry model
@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = (
        "reference_number",
        "transaction_date",
        "description",
        "payment_method",
        "created_at",
    )
    search_fields = ("reference_number", "description", "source", "payee")
    list_filter = ("transaction_date", "payment_method")
    date_hierarchy = "transaction_date"
    ordering = ("-transaction_date",)
    list_per_page = 25

    fieldsets = (
        (None, {"fields": ("reference_number", "transaction_date", "description")}),
        (
            _("Transaction Details"),
            {
                "fields": ("source", "payee", "payment_method"),
            },
        ),
    )


# Register Transaction model
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("journal_entry", "account", "amount", "transaction_type")
    search_fields = ("journal_entry__reference_number", "account__account_name")
    list_filter = ("transaction_type", "account")
    raw_id_fields = (
        "journal_entry",
        "account",
    )  # For better performance with ForeignKey fields
    ordering = ("-journal_entry__transaction_date",)
    list_per_page = 25
