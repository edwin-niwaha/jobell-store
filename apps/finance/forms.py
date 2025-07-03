from django import forms
from datetime import date
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import logging
from django.forms import modelformset_factory
from .models import (
    Transaction,
    JournalEntry,
    ChartOfAccounts,
    FinancialPeriod,
    PAYMENT_METHOD_CHOICES,
    TRANSACTION_TYPE_CHOICES,
)

logger = logging.getLogger(__name__)


# =================================== ChartOfAccountsForm ===================================
class ChartOfAccountsForm(forms.ModelForm):
    class Meta:
        model = ChartOfAccounts
        fields = [
            "account_name",
            "account_type",
            "account_number",
            "balance_type",
            "status",
            "parent_account",
            "branch",
            "description",
            "is_contra_asset",
        ]
        widgets = {
            "account_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Account Name"}
            ),
            "account_type": forms.Select(attrs={"class": "form-control"}),
            "account_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Account Number"}
            ),
            "balance_type": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "parent_account": forms.Select(attrs={"class": "form-control"}),
            "branch": forms.Select(attrs={"class": "form-control"}),
            "is_contra_asset": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Description (optional)",
                    "rows": 4,
                }
            ),
        }

    def clean_account_number(self):
        account_number = self.cleaned_data.get("account_number")
        if account_number and len(account_number) < 3:
            raise forms.ValidationError(
                "Account number must be at least 3 characters long."
            )
        if account_number and not account_number.isdigit():
            raise forms.ValidationError(
                "Account number must contain only numeric characters."
            )
        return account_number

    def clean_account_name(self):
        account_name = self.cleaned_data.get("account_name")
        if account_name and len(account_name) < 3:
            raise forms.ValidationError(
                "Account name must be at least 3 characters long."
            )
        return account_name

    def clean_balance_type(self):
        balance_type = self.cleaned_data.get("balance_type")
        account_type = self.cleaned_data.get("account_type")
        # Use instance for existing accounts, cleaned_data for new accounts
        is_contra_asset = (
            self.instance.is_contra_asset
            if self.instance.pk
            else self.cleaned_data.get("is_contra_asset", False)
        )
        if account_type and balance_type:
            valid_balance_types = {
                "asset": "debit",
                "expense": "debit",
                "liability": "credit",
                "equity": "credit",
                "revenue": "credit",
            }

        if is_contra_asset and account_type == "asset":
            if balance_type != "credit":
                raise ValidationError(
                    "Contra-asset accounts must have credit balance type."
                )
        elif valid_balance_types.get(account_type) != balance_type:
            raise ValidationError(
                f"Account type '{account_type}' must have '{valid_balance_types.get(account_type)}' balance type."
            )
        return balance_type

    def clean_parent_account(self):
        parent_account = self.cleaned_data.get("parent_account")
        if parent_account and parent_account == self.instance:
            raise forms.ValidationError("An account cannot be its own parent.")
        return parent_account

    def clean(self):
        cleaned_data = super().clean()
        account_type = cleaned_data.get("account_type")
        is_contra_asset = (
            self.instance.is_contra_asset
            if self.instance.pk
            else cleaned_data.get("is_contra_asset", False)
        )
        parent_account = cleaned_data.get("parent_account")

        if is_contra_asset and account_type != "asset":
            raise ValidationError("Only asset accounts can be marked as contra-assets.")

        if parent_account:
            # Check for circular references
            current = parent_account
            visited = {self.instance.id} if self.instance.id else set()
            while current:
                if current.id in visited:
                    raise ValidationError("Circular parent account reference detected.")
                visited.add(current.id)
                current = current.parent_account

        return cleaned_data


# =================================== ImportCOAForm ===================================
class ImportCOAForm(forms.Form):
    excel_file = forms.FileField()
    excel_file.widget.attrs["class"] = "form-control-file"


# =================================== IncomeTransactionForm ===================================
class IncomeTransactionForm(forms.ModelForm):
    financial_period = forms.ModelChoiceField(
        queryset=FinancialPeriod.objects.filter(status="open"),
        label=_("Financial Period"),
        empty_label=None,  # Force selection
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    paying_account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(
            account_type="asset",
            parent_account__isnull=False,
            account_name__icontains="Cash",  # Filter for cash-related accounts
        ),
        label="Paying Account",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    receiving_account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(
            account_type="revenue",
            parent_account__isnull=False,  # Include only sub-accounts
        ).exclude(
            account_number="4020"
        ),  # Exclude Sales Revenue
        label="Income Account",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Amount",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    transaction_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Date of Transaction",
    )
    source = forms.CharField(
        max_length=100,
        required=False,
        label="Source (from whom)",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    payment_method = forms.ChoiceField(
        choices=[("", "---------")]
        + list(PAYMENT_METHOD_CHOICES),  # Use JournalEntry choices or define here
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    reference_number = forms.CharField(
        max_length=100,
        required=False,
        label="Receipt Number",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    description = forms.CharField(
        required=False,
        label="Narration",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    class Meta:
        model = Transaction
        fields = [
            "transaction_date",  # When the transaction happened
            "paying_account",  # Where money is coming from (cash/bank)
            "receiving_account",  # Where money is going to (income account)
            "amount",  # Transaction amount
        ]

    def clean_transaction_date(self):
        transaction_date = self.cleaned_data.get("transaction_date")
        if transaction_date and transaction_date > date.today():
            raise forms.ValidationError("Date of Transaction cannot be in the future.")
        return transaction_date

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get("amount")
        reference_number = cleaned_data.get("reference_number")
        transaction_date = cleaned_data.get("transaction_date")
        financial_period = cleaned_data.get("financial_period")

        if amount is not None and amount <= 0:
            self.add_error("amount", "Amount must be greater than zero.")

        if (
            reference_number
            and JournalEntry.objects.filter(reference_number=reference_number).exists()
        ):
            self.add_error("reference_number", "Reference number must be unique.")

        # Validate transaction date against financial period
        if transaction_date and financial_period:
            if not (
                financial_period.start_date
                <= transaction_date
                <= financial_period.end_date
            ):
                self.add_error(
                    "transaction_date",
                    "Transaction date must be within the financial period's date range.",
                )

        return cleaned_data

    def save(self, commit=True):
        # Create a JournalEntry instance
        journal_entry = JournalEntry.objects.create(
            reference_number=self.cleaned_data["reference_number"],
            transaction_date=self.cleaned_data["transaction_date"],
            description=self.cleaned_data["description"],
            source=self.cleaned_data["source"],
            payment_method=self.cleaned_data["payment_method"],
            financial_period=self.cleaned_data["financial_period"],
        )

        # Credit to revenue (receiving account)
        receiving_transaction = super().save(commit=False)
        receiving_transaction.account = self.cleaned_data["receiving_account"]
        receiving_transaction.transaction_type = "credit"
        receiving_transaction.journal_entry = journal_entry
        if commit:
            receiving_transaction.save()

        # Debit from paying account (e.g., cash or bank)
        paying_transaction = Transaction(
            journal_entry=journal_entry,
            account=self.cleaned_data["paying_account"],
            amount=self.cleaned_data["amount"],
            transaction_type="debit",
        )
        if commit:
            paying_transaction.save()

        return receiving_transaction


# =================================== ExpenseTransactionForm ===================================
class ExpenseTransactionForm(forms.ModelForm):
    financial_period = forms.ModelChoiceField(
        queryset=FinancialPeriod.objects.filter(status="open"),
        label=_("Financial Period"),
        empty_label=None,  # Force selection
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    receiving_account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(
            account_type="asset",
            parent_account__isnull=False,
            account_name__icontains="Cash",  # Filter for cash-related accounts
        ),
        label="Receiving Account",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    paying_account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(
            account_type="expense",
            parent_account__isnull=False,
        ).exclude(account_number="5020"),
        label="Expense Account",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label="Amount",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    transaction_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Date of Transaction",
    )
    payee = forms.CharField(
        max_length=100,
        required=False,
        label="Payee (Who is paid?)",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    payment_method = forms.ChoiceField(
        choices=[("", "---------")] + list(PAYMENT_METHOD_CHOICES),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    reference_number = forms.CharField(
        max_length=100,
        required=False,
        label="Voucher Number",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    description = forms.CharField(
        required=False,
        label="Narration",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    class Meta:
        model = Transaction
        fields = [
            "transaction_date",  # When the transaction occurred
            "receiving_account",  # Account money is received to (cash/bank)
            "paying_account",  # Account money is paid from (expense)
            "amount",  # Transaction amount
        ]

    def clean_transaction_date(self):
        transaction_date = self.cleaned_data.get("transaction_date")
        if transaction_date and transaction_date > date.today():
            raise forms.ValidationError("Date of Transaction cannot be in the future.")
        return transaction_date

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get("amount")
        reference_number = cleaned_data.get("reference_number")
        transaction_date = cleaned_data.get("transaction_date")
        financial_period = cleaned_data.get("financial_period")

        if amount is not None and amount <= 0:
            self.add_error("amount", "Amount must be greater than zero.")

        if (
            reference_number
            and JournalEntry.objects.filter(reference_number=reference_number).exists()
        ):
            self.add_error("reference_number", "Reference number must be unique.")

        # Validate transaction date against financial period
        if transaction_date and financial_period:
            if not (
                financial_period.start_date
                <= transaction_date
                <= financial_period.end_date
            ):
                self.add_error(
                    "transaction_date",
                    "Transaction date must be within the financial period's date range.",
                )

        return cleaned_data

    def save(self, commit=True):
        # Create a JournalEntry instance
        journal_entry = JournalEntry.objects.create(
            reference_number=self.cleaned_data["reference_number"],
            transaction_date=self.cleaned_data["transaction_date"],
            description=self.cleaned_data["description"],
            payee=self.cleaned_data["payee"],
            payment_method=self.cleaned_data["payment_method"],
            financial_period=self.cleaned_data["financial_period"],
        )

        # Debit to expense (paying account)
        paying_transaction = super().save(commit=False)
        paying_transaction.account = self.cleaned_data["paying_account"]
        paying_transaction.transaction_type = "debit"
        paying_transaction.journal_entry = journal_entry
        if commit:
            paying_transaction.save()

        # Credit from receiving account (e.g., bank or cash)
        receiving_transaction = Transaction(
            journal_entry=journal_entry,
            account=self.cleaned_data["receiving_account"],
            amount=self.cleaned_data["amount"],
            transaction_type="credit",
        )
        if commit:
            receiving_transaction.save()

        return paying_transaction


# =================================== MultiJournal Entries ===================================
# JournalEntry Form
class JournalEntryForm(forms.ModelForm):
    financial_period = forms.ModelChoiceField(
        queryset=FinancialPeriod.objects.filter(status="open"),
        label=_("Financial Period"),
        empty_label=None,  # Force selection
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    transaction_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Date of Transaction",
    )
    reference_number = forms.CharField(
        max_length=100,
        required=False,
        label="Voucher Number",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    payment_method = forms.ChoiceField(
        choices=[("", "---------")] + list(PAYMENT_METHOD_CHOICES),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    description = forms.CharField(
        required=False,
        label="Narration",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )

    class Meta:
        model = JournalEntry
        fields = [
            "financial_period",
            "transaction_date",
            "reference_number",
            "payment_method",
            "description",
        ]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)  # Store the request
        super().__init__(*args, **kwargs)

        # Automatically set financial_period based on user's branch
        if self.request and self.request.user.is_authenticated:
            user_branch = getattr(
                self.request.user, "branch", None
            )  # Adjust based on User-Branch relationship
            if user_branch:
                open_periods = FinancialPeriod.objects.filter(
                    status="open", branch=user_branch
                )
                if open_periods.exists():
                    self.fields["financial_period"].initial = open_periods.first()
                else:
                    self.add_error(
                        None, "No open financial periods available for your branch."
                    )
                    self.fields["financial_period"].queryset = (
                        FinancialPeriod.objects.none()
                    )
            else:
                self.add_error(None, "User is not associated with any branch.")
                self.fields["financial_period"].queryset = (
                    FinancialPeriod.objects.none()
                )

    def clean_transaction_date(self):
        transaction_date = self.cleaned_data.get("transaction_date")
        financial_period = self.cleaned_data.get("financial_period")

        # Ensure both values are provided
        if not transaction_date or not financial_period:
            return transaction_date  # Let other validations handle missing fields

        if transaction_date > date.today():
            raise ValidationError("Date of Transaction cannot be in the future.")

        # Validate transaction date is within the selected financial period
        if financial_period.start_date and financial_period.end_date:
            if not (
                financial_period.start_date
                <= transaction_date
                <= financial_period.end_date
            ):
                raise ValidationError(
                    "Transaction date must be within the financial period's date range."
                )

        return transaction_date

    def clean_reference_number(self):
        reference_number = self.cleaned_data.get("reference_number")
        if (
            reference_number
            and JournalEntry.objects.filter(reference_number=reference_number).exists()
        ):
            raise ValidationError("Reference number must be unique.")
        return reference_number

    def clean(self):
        cleaned_data = super().clean()
        financial_period = cleaned_data.get("financial_period")
        if not financial_period:
            raise ValidationError("Financial period is required.")
        return cleaned_data

    def save(self, commit=True):
        try:
            # Truncate reference_number to avoid length errors
            reference_number = (
                self.cleaned_data["reference_number"][:100]
                if self.cleaned_data["reference_number"]
                else ""
            )

            # Get the branch from the logged-in user
            user_branch = None
            if self.request and self.request.user.is_authenticated:
                user_branch = getattr(self.request.user, "branch", None)

            logger.debug(
                f"Saving JournalEntry with financial_period: {self.cleaned_data.get('financial_period')}, branch: {user_branch}"
            )

            # Create JournalEntry instance
            journal_entry = super().save(commit=False)
            journal_entry.reference_number = reference_number
            journal_entry.branch = user_branch
            journal_entry.financial_period = self.cleaned_data["financial_period"]
            if commit:
                journal_entry.save()
            return journal_entry
        except ValidationError as e:
            logger.error(f"ValidationError in save: {e}")
            self.add_error(None, e)
            return None


# Updated TransactionForm (without JournalEntry fields)
class TransactionForm(forms.ModelForm):
    account = forms.ModelChoiceField(
        queryset=ChartOfAccounts.objects.filter(
            parent_account__isnull=False,
        ),
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Select Account"}
        ),
        label="Account",
        help_text="Select a sub-account for the transaction (parent accounts are excluded).",
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter Amount",
                "step": "0.01",
            }
        ),
        label="Amount",
    )
    transaction_type = forms.ChoiceField(
        choices=TRANSACTION_TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Transaction Type",
    )

    class Meta:
        model = Transaction
        fields = ["account", "amount", "transaction_type"]

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        return amount

    def save(self, commit=True, journal_entry=None):
        transaction = super().save(commit=False)
        if journal_entry:
            transaction.journal_entry = journal_entry
        if commit:
            transaction.save()
        return transaction


# Updated TransactionFormSet
TransactionFormSet = modelformset_factory(
    Transaction, form=TransactionForm, extra=2, can_delete=True, min_num=2
)
