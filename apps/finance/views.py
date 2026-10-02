import csv
import logging
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum, F, Q
from django.utils import timezone
from django.db import transaction
from datetime import date
from openpyxl import load_workbook
from .forms import (
    ChartOfAccountsForm,
    FinancialPeriodForm,
    IncomeTransactionForm,
    ExpenseTransactionForm,
    JournalEntryForm,
    TransactionFormSet,
    ImportCOAForm,
)

from .models import ChartOfAccounts, Transaction, Branch, FinancialPeriod
from apps.sales.forms import ReportPeriodForm

from apps.authentication.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
    admin_required,
)


logger = logging.getLogger(__name__)


# =================================== Financial Period Settings ===================================
@login_required
@admin_required
def financial_period_list_view(request):
    periods = FinancialPeriod.objects.select_related("branch").order_by(
        "-start_date", "-id"
    )
    form = FinancialPeriodForm()

    return render(
        request,
        "finance/financial_periods.html",
        {
            "periods": periods,
            "form": form,
            "form_title": "Add financial period",
            "open_count": periods.filter(status="open").count(),
            "closed_count": periods.filter(status="closed").count(),
            "locked_count": periods.filter(status="locked").count(),
        },
    )


@login_required
@admin_required
def financial_period_create_view(request):
    if request.method != "POST":
        return redirect("finance:financial_periods")

    form = FinancialPeriodForm(request.POST)
    periods = FinancialPeriod.objects.select_related("branch").order_by(
        "-start_date", "-id"
    )
    if form.is_valid():
        period = form.save(commit=False)
        period.save(user=request.user)
        messages.success(request, "Financial period added.", extra_tags="bg-success")
        return redirect("finance:financial_periods")

    messages.error(request, "Please correct the financial period details.")
    return render(
        request,
        "finance/financial_periods.html",
        {
            "periods": periods,
            "form": form,
            "form_title": "Add financial period",
            "open_count": periods.filter(status="open").count(),
            "closed_count": periods.filter(status="closed").count(),
            "locked_count": periods.filter(status="locked").count(),
        },
    )


@login_required
@admin_required
def financial_period_update_view(request, period_id):
    period = get_object_or_404(FinancialPeriod, id=period_id)
    if request.method == "POST":
        form = FinancialPeriodForm(request.POST, instance=period)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Financial period updated.", extra_tags="bg-success"
            )
            return redirect("finance:financial_periods")
        messages.error(request, "Please correct the financial period details.")
    else:
        form = FinancialPeriodForm(instance=period)

    periods = FinancialPeriod.objects.select_related("branch").order_by(
        "-start_date", "-id"
    )
    return render(
        request,
        "finance/financial_periods.html",
        {
            "periods": periods,
            "form": form,
            "form_title": f"Update {period.name}",
            "editing_period": period,
            "open_count": periods.filter(status="open").count(),
            "closed_count": periods.filter(status="closed").count(),
            "locked_count": periods.filter(status="locked").count(),
        },
    )


# =================================== Account List view ===================================
@login_required
@admin_or_manager_or_staff_required
def chart_of_accounts_list_view(request):
    accounts = ChartOfAccounts.objects.all()  # Retrieve all accounts
    accounts_by_type = {}  # Dictionary to group accounts by type

    # Group accounts by their account type
    for account in accounts:
        account_type = account.get_account_type_display()
        if account_type not in accounts_by_type:
            accounts_by_type[account_type] = []
        accounts_by_type[account_type].append(account)

    context = {
        "accounts_by_type": accounts_by_type,
        "table_title": "Chart of Accounts",
    }
    return render(request, "finance/chart_of_accounts_list.html", context)


# =================================== Process and Import Excel data ===================================
@login_required
@admin_required
@transaction.atomic
def import_coa_data(request):
    if request.method == "POST":
        form = ImportCOAForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES.get("excel_file")
            if excel_file and excel_file.name.endswith(".xlsx"):
                try:
                    # Call process_and_import_accounts_data function
                    errors = process_and_import_accounts_data(excel_file)
                    if errors:
                        for error in errors:
                            messages.error(request, error, extra_tags="bg-danger")
                    else:
                        messages.success(
                            request,
                            "Data imported successfully!",
                            extra_tags="bg-success",
                        )
                except Exception as e:
                    messages.error(
                        request, f"Error importing data: {e}", extra_tags="bg-danger"
                    )
                return redirect("finance:chart_of_accounts_list")
            else:
                messages.error(
                    request, "Please upload a valid Excel file.", extra_tags="bg-danger"
                )
    else:
        form = ImportCOAForm()
    return render(
        request,
        "finance/accounts_import.html",
        {"form_name": "Import Accounts - Excel", "form": form},
    )


# Function to import Excel data
@transaction.atomic
def process_and_import_accounts_data(excel_file):
    errors = []
    try:
        wb = load_workbook(excel_file)
        sheet = wb.active

        for row_num, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            try:
                # Extract data from Excel row
                account_name = row[0].value
                account_type = row[1].value
                account_number = row[2].value
                description = row[3].value
                balance_type = row[4].value
                status = row[5].value
                parent_account_number = row[6].value
                branch_id = row[7].value

                # Ensure account_number is treated as a string
                if account_number is None:
                    errors.append(f"Missing account number on row {row_num}")
                    continue
                account_number = str(account_number)

                # Check for required fields
                if not all(
                    [account_name, account_type, account_number, balance_type, status]
                ):
                    errors.append(f"Missing required fields on row {row_num}")
                    continue

                # Validate account type
                if account_type not in dict(ChartOfAccounts.ACCOUNT_TYPE_CHOICES):
                    errors.append(
                        f"Invalid account type '{account_type}' on row {row_num}"
                    )
                    continue

                # Validate balance type
                if balance_type not in dict(ChartOfAccounts.BALANCE_TYPE_CHOICES):
                    errors.append(
                        f"Invalid balance type '{balance_type}' on row {row_num}"
                    )
                    continue

                # Validate status
                if status not in dict(ChartOfAccounts.STATUS_CHOICES):
                    errors.append(f"Invalid status '{status}' on row {row_num}")
                    continue

                # Validate account number is numeric
                if not account_number.isdigit():
                    errors.append(f"Account number must be numeric on row {row_num}")
                    continue

                # Validate balance type aligns with account type, with exception for contra-assets
                valid_balance_types = {
                    "asset": "debit",
                    "expense": "debit",
                    "liability": "credit",
                    "equity": "credit",
                    "revenue": "credit",
                }
                is_contra_asset = (
                    account_name and "accumulated depreciation" in account_name.lower()
                )
                if is_contra_asset and balance_type != "credit":
                    errors.append(
                        f"Contra-asset account '{account_name}' must have 'credit' balance type on row {row_num}"
                    )
                    continue
                elif (
                    not is_contra_asset
                    and valid_balance_types.get(account_type) != balance_type
                ):
                    errors.append(
                        f"Account type '{account_type}' must have '{valid_balance_types.get(account_type)}' balance type on row {row_num}"
                    )
                    continue

                # Retrieve parent account if provided
                parent_account = None
                if parent_account_number:
                    try:
                        parent_account = ChartOfAccounts.objects.get(
                            account_number=str(parent_account_number)
                        )
                    except ChartOfAccounts.DoesNotExist:
                        errors.append(
                            f"Parent account '{parent_account_number}' not found on row {row_num}"
                        )
                        continue

                # Retrieve branch if provided
                branch = None
                if branch_id:
                    try:
                        branch = Branch.objects.get(id=branch_id)
                    except Branch.DoesNotExist:
                        errors.append(
                            f"Branch ID '{branch_id}' not found on row {row_num}"
                        )
                        continue

                # Create the account
                try:
                    account = ChartOfAccounts(
                        account_name=account_name,
                        account_type=account_type,
                        account_number=account_number,
                        description=description,
                        balance_type=balance_type,
                        status=status,
                        parent_account=parent_account,
                        branch=branch,
                        is_deleted=False,
                    )
                    account.clean()  # Run model validation
                    account.save()
                except ValidationError as e:
                    errors.append(f"Validation error on row {row_num}: {e}")
                    logger.error(f"Validation error on row {row_num}: {e}")
                except Exception as e:
                    errors.append(f"Error creating account on row {row_num}: {e}")
                    logger.error(f"Error creating account on row {row_num}: {e}")
            except Exception as e:
                errors.append(f"Error processing row {row_num}: {e}")
                logger.error(f"Error processing row {row_num}: {e}")
    except Exception as e:
        errors.append(f"Failed to process the Excel file: {e}")
        logger.error(f"Failed to process the Excel file: {e}")

    return errors


# =================================== Add Account view ===================================
@login_required
@admin_or_manager_required
def add_chart_of_account_view(request):
    form = ChartOfAccountsForm(request.POST or None)

    if form.is_valid():
        form.save()
        messages.success(
            request, "Account added successfully!", extra_tags="bg-success"
        )
        return redirect("finance:add_chart_of_account")

    # Additional context for the template
    context = {
        "form": form,
        "table_title": "Add New Account",
    }

    return render(request, "finance/chart_of_account_add.html", context)


# =================================== Account update view ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def chart_of_account_update_view(request, account_id):
    account = get_object_or_404(ChartOfAccounts, id=account_id)

    if request.method == "POST":
        form = ChartOfAccountsForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Account: {account.account_name} updated successfully!",
                extra_tags="bg-success",
            )
            return redirect("finance:chart_of_accounts_list")
        else:
            messages.error(
                request,
                "There was an error updating the account!",
                extra_tags="bg-danger",
            )
    else:
        form = ChartOfAccountsForm(instance=account)

    context = {"form": form, "account": account, "page_title": "Update Account"}

    return render(request, "finance/chart_of_account_update.html", context)


# =================================== Account delete view ===================================
@login_required
@admin_required
@transaction.atomic
def chart_of_account_delete_view(request, account_id):
    account = get_object_or_404(ChartOfAccounts, id=account_id)

    try:
        account.delete()
        messages.success(
            request,
            f"Account: {account.account_name} deleted successfully!",
            extra_tags="bg-success",
        )
    except Exception:
        logger.exception("Error deleting chart of account %s", account_id)
        messages.error(
            request,
            "An error occurred during the deletion process.",
            extra_tags="bg-danger",
        )

    return redirect("finance:chart_of_accounts_list")


# =================================== Income transaction creation view ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def income_transaction_create_view(request):
    if request.method == "POST":
        form = IncomeTransactionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Income transaction posted successfully.",
                extra_tags="bg-success",
            )
            return redirect("finance:income_add")
    else:
        form = IncomeTransactionForm()

    context = {
        "form": form,
        "form_title": "Add New Income Transaction",
    }

    return render(request, "finance/income_add.html", context)


# =================================== expense add view ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def expense_transaction_create_view(request):
    if request.method == "POST":
        form = ExpenseTransactionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Expense transaction posted successfully.",
                extra_tags="bg-success",
            )
            return redirect("finance:expense_add")
    else:
        form = ExpenseTransactionForm()

    context = {
        "form": form,
        "form_title": "Add New Expense Transaction",
    }

    return render(request, "finance/expense_add.html", context)


# =================================== multi-journal entry view ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def multi_journal_view(request):
    if request.method == "POST":
        journal_form = JournalEntryForm(request.POST, request=request)
        formset = TransactionFormSet(request.POST)
        logger.debug("Received POST request with data: %s", request.POST)

        if journal_form.is_valid() and formset.is_valid():
            logger.info("Journal form and formset are valid. Processing transactions.")
            journal_entry = journal_form.save()
            if journal_entry is None:
                messages.error(
                    request, "Unable to create the journal entry.", extra_tags="danger"
                )
                return render(
                    request,
                    "finance/multi_journal_entry_add.html",
                    {
                        "formset": formset,
                        "journal_form": journal_form,
                        "form_title": "Add New Journal Entries",
                    },
                )

            for form in formset.forms:
                if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                    continue
                form.save(journal_entry=journal_entry)
                logger.debug("Saved transaction for form: %s", form.cleaned_data)

            logger.info("Journal entries posted successfully.")
            messages.success(request, "Journal entries posted successfully.")
            return redirect("finance:multi_journal")

        else:
            logger.error(
                "Form errors: Journal form: %s, Formset: %s",
                journal_form.errors,
                formset.errors,
            )
            logger.error("Non-form errors: %s", formset.non_form_errors())
            for i, form in enumerate(formset.forms):
                logger.error("Form %d errors: %s", i, form.errors)
            messages.error(
                request, "Please correct the errors below.", extra_tags="danger"
            )
    else:
        logger.debug("Rendering formset for GET request.")
        journal_form = JournalEntryForm(request=request)
        formset = TransactionFormSet(queryset=Transaction.objects.none())

    return render(
        request,
        "finance/multi_journal_entry_add.html",
        {
            "formset": formset,
            "journal_form": journal_form,
            "form_title": "Add New Journal Entries",
        },
    )


# =================================== ledger_report view ===================================
def get_financial_year_dates():
    """Returns the start and end dates for the current financial year."""
    today = date.today()

    # Check if today is after July 1st (start of the financial year)
    if today.month >= 7:
        start_date = date(today.year, 7, 1)  # July 1st of the current year
        end_date = date(today.year + 1, 6, 30)  # June 30th of the next year
    else:
        start_date = date(today.year - 1, 7, 1)  # July 1st of the previous year
        end_date = date(today.year, 6, 30)  # June 30th of the current year

    return start_date, end_date


@login_required
@admin_or_manager_required
def ledger_report_view(request):
    selected_account_id = request.GET.get("account_id")  # Get selected account ID
    ledger_data = []
    accounts = ChartOfAccounts.objects.all()  # Fetch all accounts for the dropdown
    total_debits = 0
    total_credits = 0

    # Get the start and end dates for the current financial year
    financial_year_start, financial_year_end = get_financial_year_dates()

    # Use query parameters or default to the financial year range
    start_date = request.GET.get("start_date") or financial_year_start
    end_date = request.GET.get("end_date") or financial_year_end

    selected_account = None
    opening_balance = 0

    if selected_account_id:
        selected_account = get_object_or_404(ChartOfAccounts, id=selected_account_id)

        # Get transactions within the selected date range
        ledger_data = Transaction.objects.filter(
            account=selected_account,
            journal_entry__transaction_date__range=[start_date, end_date],
        ).order_by("journal_entry__transaction_date")

        # Get opening balance by calculating the balance before the start_date
        opening_balance_queryset = Transaction.objects.filter(
            account=selected_account, journal_entry__transaction_date__lt=start_date
        )

        # Calculate the opening balance as the sum of all prior debits and credits
        for transaction in opening_balance_queryset:
            if transaction.transaction_type == "debit":
                opening_balance += transaction.amount
            elif transaction.transaction_type == "credit":
                opening_balance -= transaction.amount

        # Calculate debits, credits, and running balance
        running_balance = opening_balance
        for transaction in ledger_data:
            if transaction.transaction_type == "debit":
                transaction.debit = transaction.amount
                transaction.credit = 0
                total_debits += transaction.amount
            elif transaction.transaction_type == "credit":
                transaction.debit = 0
                transaction.credit = transaction.amount
                total_credits += transaction.amount
            else:
                transaction.debit = 0
                transaction.credit = 0

            # Update running balance
            running_balance += transaction.debit - transaction.credit
            transaction.running_balance = running_balance

    return render(
        request,
        "finance/ledger_report.html",
        {
            "ledger_data": ledger_data,
            "accounts": accounts,
            "selected_account": selected_account,
            "selected_account_id": selected_account_id,
            "start_date": start_date,
            "end_date": end_date,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "opening_balance": opening_balance,  # Pass opening balance to template
        },
    )


# =================================== ledger_report detailed view ===================================
@login_required
@admin_or_manager_required
def ledger_select_period(request):
    """Display a list of open financial periods for ledger report selection."""
    financial_periods = FinancialPeriod.objects.filter(status="open").order_by(
        "-start_date"
    )
    return render(
        request,
        "finance/select_ledger_period.html",
        {"financial_periods": financial_periods},
    )


# @login_required
# @admin_or_manager_required
# def ledger_report_detailed(request, period_id):
#     """Generate ledger report for the selected financial period."""
#     ledger_data = []
#     accounts = ChartOfAccounts.objects.all().order_by(
#         "account_number"
#     )  # Sort accounts by account_number
#     total_debits = 0
#     total_credits = 0

#     # Get the selected financial period
#     financial_period = get_object_or_404(FinancialPeriod, id=period_id, status="open")
#     start_date = financial_period.start_date
#     end_date = financial_period.end_date

#     # Get all transactions within the financial period, sorted by account_number
#     ledger_data = (
#         Transaction.objects.filter(
#             journal_entry__transaction_date__range=[start_date, end_date]
#         )
#         .select_related("account")
#         .order_by("account__account_number", "journal_entry__transaction_date")
#     )

#     # Calculate opening balance for each account
#     opening_balances = {}
#     opening_balance_queryset = Transaction.objects.filter(
#         journal_entry__transaction_date__lt=start_date
#     ).select_related("account")

#     for transaction in opening_balance_queryset:
#         account_id = transaction.account.id
#         if account_id not in opening_balances:
#             opening_balances[account_id] = 0
#         if transaction.transaction_type == "debit":
#             opening_balances[account_id] += transaction.amount
#         elif transaction.transaction_type == "credit":
#             opening_balances[account_id] -= transaction.amount

#     # Calculate debits, credits, and running balance
#     running_balances = {
#         account_id: balance for account_id, balance in opening_balances.items()
#     }
#     for transaction in ledger_data:
#         account_id = transaction.account.id
#         if account_id not in running_balances:
#             running_balances[account_id] = opening_balances.get(account_id, 0)

#         if transaction.transaction_type == "debit":
#             transaction.debit = transaction.amount
#             transaction.credit = 0
#             total_debits += transaction.amount
#         elif transaction.transaction_type == "credit":
#             transaction.debit = 0
#             transaction.credit = transaction.amount
#             total_credits += transaction.amount
#         else:
#             transaction.debit = 0
#             transaction.credit = 0

#         # Update running balance
#         running_balances[account_id] += transaction.debit - transaction.credit
#         transaction.running_balance = running_balances[account_id]

#     return render(
#         request,
#         "finance/ledger_report_detailed.html",
#         {
#             "ledger_data": ledger_data,
#             "accounts": accounts,
#             "financial_period": financial_period,
#             "start_date": start_date,
#             "end_date": end_date,
#             "total_debits": total_debits,
#             "total_credits": total_credits,
#             "opening_balances": opening_balances,
#         },
#     )


@login_required
@admin_or_manager_required
def ledger_report_detailed(request, period_id):
    """Generate ledger report for the selected financial period."""
    ledger_data = []
    accounts = ChartOfAccounts.objects.all().order_by(
        "account_number"
    )  # Sort accounts by account_number
    total_debits = 0
    total_credits = 0

    # Get the selected financial period
    financial_period = get_object_or_404(FinancialPeriod, id=period_id, status="open")
    start_date = financial_period.start_date
    end_date = financial_period.end_date

    # Get all transactions within the financial period, sorted by account_number
    ledger_data = (
        Transaction.objects.filter(
            journal_entry__transaction_date__range=[start_date, end_date]
        )
        .select_related("account")
        .order_by("account__account_number", "journal_entry__transaction_date")
    )

    # Pagination
    paginator = Paginator(ledger_data, 25)  # Show 25 transactions per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calculate opening balance for each account
    opening_balances = {}
    opening_balance_queryset = Transaction.objects.filter(
        journal_entry__transaction_date__lt=start_date
    ).select_related("account")

    for transaction in opening_balance_queryset:
        account_id = transaction.account.id
        if account_id not in opening_balances:
            opening_balances[account_id] = 0
        if transaction.transaction_type == "debit":
            opening_balances[account_id] += transaction.amount
        elif transaction.transaction_type == "credit":
            opening_balances[account_id] -= transaction.amount

    # Calculate debits, credits, and running balance
    running_balances = {
        account_id: balance for account_id, balance in opening_balances.items()
    }
    for transaction in page_obj:  # Process only transactions on current page
        account_id = transaction.account.id
        if account_id not in running_balances:
            running_balances[account_id] = opening_balances.get(account_id, 0)

        if transaction.transaction_type == "debit":
            transaction.debit = transaction.amount
            transaction.credit = 0
            total_debits += transaction.amount
        elif transaction.transaction_type == "credit":
            transaction.debit = 0
            transaction.credit = transaction.amount
            total_credits += transaction.amount
        else:
            transaction.debit = 0
            transaction.credit = 0

        # Update running balance
        running_balances[account_id] += transaction.debit - transaction.credit
        transaction.running_balance = running_balances[account_id]

    return render(
        request,
        "finance/ledger_report_detailed.html",
        {
            "ledger_data": page_obj,  # Pass paginated data
            "accounts": accounts,
            "financial_period": financial_period,
            "start_date": start_date,
            "end_date": end_date,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "opening_balances": opening_balances,
            "page_obj": page_obj,  # For pagination controls
        },
    )


# =================================== Delete detailed transaction ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_transaction_detailed(request, transaction_id):
    try:
        transaction = get_object_or_404(Transaction, id=transaction_id)
        journal_entry = transaction.journal_entry
        journal_ref = journal_entry.reference_number
        if journal_entry.financial_period.status != "open":
            messages.error(
                request,
                "Cannot delete: Financial period closed.",
                extra_tags="bg-danger",
            )
            return redirect("finance:ledger_select_period")
        journal_entry.delete()
        messages.success(
            request, f"Journal Entry #{journal_ref} deleted!", extra_tags="bg-success"
        )
    except ValidationError as e:
        logger.warning("Validation error deleting detailed transaction %s: %s", transaction_id, e)
        messages.error(request, f"Validation error: {str(e)}", extra_tags="bg-danger")
    except Exception:
        logger.exception("Error deleting detailed transaction %s", transaction_id)
        messages.error(request, "Deletion error!", extra_tags="bg-danger")
    return redirect("finance:ledger_select_period")


# =================================== Delete transaction ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_transaction(request, transaction_id):
    try:
        transaction = get_object_or_404(Transaction, id=transaction_id)
        journal_entry = transaction.journal_entry
        journal_ref = journal_entry.reference_number
        if journal_entry.financial_period.status != "open":
            messages.error(
                request,
                "Cannot delete: Financial period closed.",
                extra_tags="bg-danger",
            )
            return redirect("finance:ledger_report")
        journal_entry.delete()
        messages.success(
            request, f"Journal Entry #{journal_ref} deleted!", extra_tags="bg-success"
        )
    except ValidationError as e:
        logger.warning("Validation error deleting transaction %s: %s", transaction_id, e)
        messages.error(request, f"Validation error: {str(e)}", extra_tags="bg-danger")
    except Exception:
        logger.exception("Error deleting transaction %s", transaction_id)
        messages.error(request, "Deletion error!", extra_tags="bg-danger")
    return redirect("finance:ledger_report")


# =================================== profit_and_loss_view pro ===================================
@login_required
@admin_or_manager_required
def profit_loss_statement_view(request):
    # Initialize the profit and loss sections
    profit_and_loss = {
        "income": {"accounts": [], "total": 0.0},
        "expenses": {"accounts": [], "total": 0.0},
        "net_profit": 0.0,
    }

    # Initialize the form
    form = ReportPeriodForm(request.GET or None)

    start_date = None
    end_date = None
    selected_branch = None
    company_name = settings.COMPANY_NAME
    company_location = "Kampala, Uganda"
    company_contact = f"Phone: {settings.SUPPORT_PHONE or 'N/A'} | Email: {settings.SUPPORT_EMAIL}"

    if form.is_valid():
        # Extract the start date, end date, and branch from the form
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]
        selected_branch = form.cleaned_data.get("branch_id")

        # Build transaction filter for revenue
        transaction_filter = {
            "journal_entry__transaction_date__range": (start_date, end_date),
            "account__account_type": "revenue",
            "transaction_type": "credit",
            "account__is_deleted": False,
        }
        if selected_branch:
            transaction_filter["journal_entry__branch"] = selected_branch

        # Filter revenue transactions
        revenue_transactions = Transaction.objects.filter(**transaction_filter)

        # Aggregate revenue by account
        revenue_categories = (
            revenue_transactions.values(
                "account__account_name",
                "account__account_number",
                "account__parent_account__id",
                "account__parent_account__account_name",
                "account__parent_account__account_number",
            )
            .annotate(balance=Sum("amount"))
            .order_by("account__account_number")
        )

        total_revenue = Decimal("0.00")
        for category in revenue_categories:
            amount = category["balance"] or Decimal("0.00")
            is_subaccount = bool(category["account__parent_account__id"])
            # Remove "Revenue" prefix from account names
            parent_name = (
                category["account__parent_account__account_name"]
                if category["account__parent_account__account_name"]
                else ""
            )
            account_name = category["account__account_name"]
            display_name = (
                f"{account_name}" if is_subaccount and parent_name else account_name
            )
            # Use only sub-account number for sub-accounts
            display_number = (
                category["account__account_number"]
                if is_subaccount and category["account__account_number"]
                else category["account__account_number"]
            )
            profit_and_loss["income"]["accounts"].append(
                {
                    "name": display_name,
                    "account_number": display_number,
                    "balance": float(amount),
                    "is_subaccount": is_subaccount,
                }
            )
            total_revenue += amount
        profit_and_loss["income"]["total"] = float(total_revenue)

        # Update filter for expenses
        transaction_filter["account__account_type"] = "expense"
        transaction_filter["transaction_type"] = "debit"

        # Filter expense transactions
        expense_transactions = Transaction.objects.filter(**transaction_filter)

        # Aggregate expenses by account
        expense_categories = (
            expense_transactions.values(
                "account__account_name",
                "account__account_number",
                "account__parent_account__id",
                "account__parent_account__account_name",
                "account__parent_account__account_number",
            )
            .annotate(balance=Sum("amount"))
            .order_by("account__account_number")
        )

        total_expenses = Decimal("0.00")
        for category in expense_categories:
            amount = category["balance"] or Decimal("0.00")
            is_subaccount = bool(category["account__parent_account__id"])
            # Remove "Expenses" prefix from account names
            parent_name = (
                category["account__parent_account__account_name"]
                if category["account__parent_account__account_name"]
                else ""
            )
            account_name = category["account__account_name"]
            display_name = (
                f"{account_name}" if is_subaccount and parent_name else account_name
            )
            # Use only sub-account number for sub-accounts
            display_number = (
                category["account__account_number"]
                if is_subaccount and category["account__account_number"]
                else category["account__account_number"]
            )
            profit_and_loss["expenses"]["accounts"].append(
                {
                    "name": display_name,
                    "account_number": display_number,
                    "balance": float(amount),
                    "is_subaccount": is_subaccount,
                }
            )
            total_expenses += amount
        profit_and_loss["expenses"]["total"] = float(total_expenses)

        # Calculate net profit
        profit_and_loss["net_profit"] = float(total_revenue - total_expenses)

    logger.debug("Profit and loss report generated: %s", profit_and_loss)

    # Pass data to the template
    context = {
        "form": form,
        "profit_and_loss": profit_and_loss,
        "start_date": start_date,
        "end_date": end_date,
        "selected_branch": selected_branch,
        "selected_branch_name": (
            selected_branch.name if selected_branch else "All Branches"
        ),
        "company_name": company_name,
        "company_location": company_location,
        "company_contact": company_contact,
    }
    return render(request, "finance/profit_loss_statement.html", context)


# =================================== balance_sheet_view ===================================


@login_required
@admin_or_manager_required
def balance_sheet_view(request):
    # Get query parameters
    branch_id = request.GET.get("branch_id")
    period_id = request.GET.get("period_id")

    # Initialize filters
    branches = Branch.objects.all()
    financial_periods = FinancialPeriod.objects.all()

    # Default to current open period and all branches if not specified
    selected_period = None
    selected_branch = None
    if period_id:
        selected_period = FinancialPeriod.objects.filter(id=period_id).first()
    else:
        selected_period = FinancialPeriod.objects.filter(status="open").first()

    if branch_id:
        selected_branch = Branch.objects.filter(id=branch_id).first()

    # Initialize balance sheet data with singular keys to match account_type
    balance_sheet = {
        "asset": {"total": Decimal("0.00"), "accounts": []},
        "liability": {"total": Decimal("0.00"), "accounts": []},
        "equity": {"total": Decimal("0.00"), "accounts": []},
    }

    if selected_period:
        # Define date range for cumulative data (up to the end of selected period)
        end_date = selected_period.end_date
        transactions = Transaction.objects.filter(
            journal_entry__financial_period__end_date__lte=end_date,
            journal_entry__financial_period__status__in=["open", "closed"],
        )

        if selected_branch:
            transactions = transactions.filter(journal_entry__branch=selected_branch)

        # Aggregate balances by account type
        for account_type in ["asset", "liability", "equity"]:
            accounts = ChartOfAccounts.objects.filter(
                account_type=account_type, status="active", is_deleted=False
            )

            if selected_branch:
                accounts = accounts.filter(branch=selected_branch)

            for account in accounts:
                # Skip Retained Earnings in initial loop; handle it separately
                if account.account_name.lower() == "retained earnings":
                    continue

                # Calculate balance based on transaction type and balance type
                debit_sum = transactions.filter(
                    account=account, transaction_type="debit"
                ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

                credit_sum = transactions.filter(
                    account=account, transaction_type="credit"
                ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

                # Determine balance based on account's balance type
                balance = (
                    debit_sum - credit_sum
                    if account.balance_type == "debit"
                    else credit_sum - debit_sum
                )

                # Adjust for contra-assets
                if account.is_contra_asset:
                    balance = -balance

                if balance != 0:
                    balance_sheet[account_type]["accounts"].append(
                        {
                            "name": account.account_name,
                            "balance": balance,
                            "account_number": account.account_number,
                        }
                    )
                    balance_sheet[account_type]["total"] += balance

        # Calculate Net Income (Revenue - Expenses) for all periods up to end_date
        revenue_transactions = Transaction.objects.filter(
            journal_entry__financial_period__end_date__lte=end_date,
            journal_entry__financial_period__status__in=["open", "closed"],
            account__account_type="revenue",
        )
        if selected_branch:
            revenue_transactions = revenue_transactions.filter(
                journal_entry__branch=selected_branch
            )

        revenue_credit = revenue_transactions.filter(
            transaction_type="credit"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        revenue_debit = revenue_transactions.filter(transaction_type="debit").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
        revenue_total = revenue_credit - revenue_debit  # Revenue is typically credit

        expense_transactions = Transaction.objects.filter(
            journal_entry__financial_period__end_date__lte=end_date,
            journal_entry__financial_period__status__in=["open", "closed"],
            account__account_type="expense",
        )
        if selected_branch:
            expense_transactions = expense_transactions.filter(
                journal_entry__branch=selected_branch
            )

        expense_debit = expense_transactions.filter(transaction_type="debit").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
        expense_credit = expense_transactions.filter(
            transaction_type="credit"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        expense_total = expense_debit - expense_credit  # Expenses are typically debit

        net_income = revenue_total - expense_total

        # Handle Retained Earnings
        retained_earnings_account = ChartOfAccounts.objects.filter(
            account_type="equity",
            account_name__iexact="Retained Earnings",
            status="active",
            is_deleted=False,
        ).first()

        retained_earnings_balance = net_income  # Start with net income
        if retained_earnings_account:
            # Add direct transactions to Retained Earnings
            re_debit = transactions.filter(
                account=retained_earnings_account, transaction_type="debit"
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            re_credit = transactions.filter(
                account=retained_earnings_account, transaction_type="credit"
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            re_balance = (
                re_credit - re_debit
                if retained_earnings_account.balance_type == "credit"
                else re_debit - re_credit
            )
            retained_earnings_balance += re_balance

        if retained_earnings_balance != 0:
            balance_sheet["equity"]["accounts"].append(
                {
                    "name": (
                        retained_earnings_account.account_name
                        if retained_earnings_account
                        else "Retained Earnings"
                    ),
                    "balance": retained_earnings_balance,
                    "account_number": (
                        retained_earnings_account.account_number
                        if retained_earnings_account
                        else "N/A"
                    ),
                }
            )
            balance_sheet["equity"]["total"] += retained_earnings_balance

    # Calculate total liabilities and equity
    total_liabilities_equity = (
        balance_sheet["liability"]["total"] + balance_sheet["equity"]["total"]
    )

    # Verify balance
    if abs(balance_sheet["asset"]["total"] - total_liabilities_equity) > Decimal(
        "0.01"
    ):
        return render(
            request,
            "finance/error.html",
            {
                "error": f"Balance sheet does not balance: Assets ({balance_sheet['asset']['total']}) ≠ Liabilities + Equity ({total_liabilities_equity})"
            },
        )

    context = {
        "balance_sheet": balance_sheet,
        "branches": branches,
        "financial_periods": financial_periods,
        "selected_branch": selected_branch,
        "selected_period": selected_period,
        "total_liabilities_equity": total_liabilities_equity,
        "current_date": (
            selected_period.end_date if selected_period else timezone.now().date()
        ),
        "company_name": settings.COMPANY_NAME,
        "company_location": "Kampala, Uganda",
        "company_contact": f"Phone: {settings.SUPPORT_PHONE or 'N/A'} | Email: {settings.SUPPORT_EMAIL}",
        "financial_period_name": (
            selected_period.name if selected_period else "Current Period"
        ),
        "selected_branch_name": (
            selected_branch.name if selected_branch else "All Branches"
        ),
    }

    return render(request, "finance/balance_sheet.html", context)


# =================================== cash_flow_statement ===================================
@login_required
@admin_or_manager_required
def cash_flow_select_period(request):
    """Display a list of open financial periods for cash flow statement selection."""
    financial_periods = FinancialPeriod.objects.filter(status="open").order_by(
        "-start_date"
    )
    return render(
        request,
        "finance/select_cash_flow_period.html",
        {"financial_periods": financial_periods},
    )


@login_required
@admin_or_manager_required
def cash_flow_statement(request, period_id):
    """Generate the cash flow statement for a given financial period."""
    financial_period = get_object_or_404(FinancialPeriod, id=period_id)

    # Define account types for cash flow categories
    cash_accounts = ChartOfAccounts.objects.filter(
        account_type="asset", account_name__icontains="cash"
    ).values_list("id", flat=True)

    operating_accounts = ChartOfAccounts.objects.filter(
        Q(account_type="revenue") | Q(account_type="expense")
    ).values_list("id", flat=True)

    investing_accounts = ChartOfAccounts.objects.filter(
        Q(account_type="asset")
        & ~Q(id__in=cash_accounts)
        & ~Q(account_name__icontains="accumulated depreciation")
    ).values_list("id", flat=True)

    financing_accounts = ChartOfAccounts.objects.filter(
        Q(account_type="liability") | Q(account_type="equity")
    ).values_list("id", flat=True)

    # Calculate cash flows
    transactions = Transaction.objects.filter(
        journal_entry__financial_period=financial_period,
        journal_entry__transaction_date__range=[
            financial_period.start_date,
            financial_period.end_date,
        ],
    )

    def calculate_net_cash_flow(account_ids):
        debit_sum = transactions.filter(
            account_id__in=account_ids, transaction_type="debit"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        credit_sum = transactions.filter(
            account_id__in=account_ids, transaction_type="credit"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        return debit_sum - credit_sum

    # Calculate cash flows for each category
    operating_cash_flow = calculate_net_cash_flow(operating_accounts)
    investing_cash_flow = calculate_net_cash_flow(investing_accounts)
    financing_cash_flow = calculate_net_cash_flow(financing_accounts)

    # Calculate net cash flow and cash balance
    net_cash_flow = operating_cash_flow + investing_cash_flow + financing_cash_flow

    cash_balance = transactions.filter(account_id__in=cash_accounts).aggregate(
        net_cash=Sum("amount", filter=Q(transaction_type="debit"))
        - Sum("amount", filter=Q(transaction_type="credit"))
    )["net_cash"] or Decimal("0.00")

    context = {
        "financial_period": financial_period,
        "operating_cash_flow": operating_cash_flow,
        "investing_cash_flow": investing_cash_flow,
        "financing_cash_flow": financing_cash_flow,
        "net_cash_flow": net_cash_flow,
        "cash_balance": cash_balance,
        "report_date": datetime.now().date(),
    }

    return render(request, "finance/cash_flow_statement.html", context)


# =================================== trial_balance ===================================
@login_required
@admin_or_manager_required
def trial_balance_select_period(request):
    """Display a list of open financial periods for trial balance selection."""
    financial_periods = FinancialPeriod.objects.filter(status="open").order_by(
        "-start_date"
    )
    return render(
        request,
        "finance/select_trial_balance_period.html",
        {"financial_periods": financial_periods},
    )


@login_required
@admin_or_manager_required
def trial_balance(request, period_id):
    """Generate the trial balance for a given financial period."""
    financial_period = get_object_or_404(FinancialPeriod, id=period_id)

    # Validate financial period status
    if financial_period.status != "open":
        return render(
            request,
            "finance/trial_balance.html",
            {
                "error": "Trial balance can only be generated for an open financial period.",
                "financial_period": financial_period,
                "report_date": datetime.now().date(),
            },
        )

    # Fetch all active accounts
    accounts = ChartOfAccounts.objects.filter(
        status="active",
        is_deleted=False,
        branch=financial_period.branch,
    ).order_by("account_number")

    # Initialize trial balance data and totals
    trial_balance = []
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    # Calculate balances for each account
    for account in accounts:
        transactions = Transaction.objects.filter(
            account=account,
            journal_entry__financial_period=financial_period,
            journal_entry__transaction_date__range=[
                financial_period.start_date,
                financial_period.end_date,
            ],
        ).aggregate(
            total_debits=Sum("amount", filter=Q(transaction_type="debit")),
            total_credits=Sum("amount", filter=Q(transaction_type="credit")),
        )

        # Handle None values
        debit_amount = transactions["total_debits"] or Decimal("0.00")
        credit_amount = transactions["total_credits"] or Decimal("0.00")

        # Calculate net balance based on account's balance type
        if account.balance_type == "debit":
            balance = debit_amount - credit_amount
            debit_column = balance if balance > 0 else Decimal("0.00")
            credit_column = -balance if balance < 0 else Decimal("0.00")
        else:  # credit balance type
            balance = credit_amount - debit_amount
            credit_column = balance if balance > 0 else Decimal("0.00")
            debit_column = -balance if balance < 0 else Decimal("0.00")

        # Add to totals
        total_debit += debit_column
        total_credit += credit_column

        # Append to trial balance
        trial_balance.append(
            {
                "account_number": account.account_number,
                "account_name": account.account_name,
                "account_type": account.get_account_type_display(),
                "debit": debit_column,
                "credit": credit_column,
            }
        )

    context = {
        "financial_period": financial_period,
        "trial_balance": trial_balance,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "report_date": datetime.now().date(),
    }

    return render(request, "finance/trial_balance.html", context)


def generate_audit_log_report(start_date=None, end_date=None, user=None):
    """Generate audit log report for specified models."""
    end_date = end_date or timezone.now().date()
    start_date = start_date or (end_date - timezone.timedelta(days=30))

    report_data = []
    for model_name in ["ChartOfAccounts", "JournalEntry", "Transaction"]:
        model = ContentType.objects.get(
            app_label="finance", model=model_name.lower()
        ).model_class()

        # Base query for date range
        base_query = {
            "created_at__date__gte": start_date,
            "created_at__date__lte": end_date,
        }
        if user:
            base_query["created_by"] = user

        # Created records
        for record in model.objects.filter(**base_query):
            report_data.append(
                {
                    "model": model_name,
                    "action": "CREATE",
                    "timestamp": record.created_at,
                    "user": (
                        record.created_by.username if record.created_by else "System"
                    ),
                    "object_id": record.id,
                    "details": str(record),
                }
            )

        # Updated records
        base_query["updated_at__date__gte"] = start_date
        base_query["updated_at__date__lte"] = end_date
        for record in model.objects.filter(
            **base_query, updated_at__gt=F("created_at")
        ):
            report_data.append(
                {
                    "model": model_name,
                    "action": "UPDATE",
                    "timestamp": record.updated_at,
                    "user": (
                        record.created_by.username if record.created_by else "System"
                    ),
                    "object_id": record.id,
                    "details": str(record),
                }
            )

        # Deleted records (ChartOfAccounts only)
        if model_name == "ChartOfAccounts":
            for record in model.objects.filter(**base_query, is_deleted=True):
                report_data.append(
                    {
                        "model": model_name,
                        "action": "DELETE",
                        "timestamp": record.updated_at,
                        "user": (
                            record.created_by.username
                            if record.created_by
                            else "System"
                        ),
                        "object_id": record.id,
                        "details": str(record),
                    }
                )

    return sorted(report_data, key=lambda x: x["timestamp"], reverse=True)


# =================================== audit_log_view ===================================
@login_required
@admin_or_manager_required
def audit_log_view(request):
    """Handle audit log display and CSV download with pagination."""
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    user_id = request.GET.get("user_id")
    page = request.GET.get("page", 1)

    try:
        start_date = (
            datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        )
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    except ValueError:
        messages.error(request, "Invalid date format. Use YYYY-MM-DD.", extra_tags="bg-danger")
        start_date = None
        end_date = None

    user = None
    if user_id:
        user = User.objects.filter(id=user_id).first()
        if not user:
            messages.error(request, "Selected user was not found.", extra_tags="bg-danger")
            user_id = ""

    report_data = generate_audit_log_report(start_date, end_date, user)

    if request.GET.get("download"):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit_log_report.csv"'
        writer = csv.writer(response)
        writer.writerow(["Timestamp", "User", "Model", "Action", "Object ID", "Details"])
        for entry in report_data:
            writer.writerow(
                [
                    entry["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                    entry["user"],
                    entry["model"],
                    entry["action"],
                    entry["object_id"],
                    entry["details"],
                ]
            )
        return response

    # Pagination
    paginator = Paginator(report_data, 10)  # Show 10 entries per page
    report_data_paginated = paginator.get_page(page)

    context = {
        "report_data": report_data_paginated,
        "users": User.objects.all(),
        "start_date": start_date,
        "end_date": end_date,
        "selected_user": user,
        "user_id": user_id,
        "audit_total": len(report_data),
    }
    return render(request, "finance/audit_logs.html", context)
