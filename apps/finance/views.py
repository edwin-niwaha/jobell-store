import logging
from datetime import datetime
from decimal import Decimal
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
    IncomeTransactionForm,
    ExpenseTransactionForm,
    JournalEntryForm,
    TransactionFormSet,
    ImportCOAForm,
)

# IncomeTransactionFormSet, ExpenseTransactionFormSet
from apps.sales.models import SaleDetail
from .models import ChartOfAccounts, Transaction, Branch, FinancialPeriod
from apps.sales.forms import ReportPeriodForm

from apps.authentication.decorators import (
    admin_or_manager_or_staff_required,
    admin_or_manager_required,
    admin_required,
)


logger = logging.getLogger(__name__)


# =================================== Account List view ===================================
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
    except Exception as e:
        messages.error(
            request,
            "An error occurred during the deletion process.",
            extra_tags="bg-danger",
        )
        print(f"Error deleting account: {e}")

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
        journal_form = JournalEntryForm(request.POST)
        formset = TransactionFormSet(request.POST)
        logger.debug("Received POST request with data: %s", request.POST)

        if journal_form.is_valid() and formset.is_valid():
            logger.info("Journal form and formset are valid. Processing transactions.")
            journal_entry = journal_form.save()
            transactions = formset.save(commit=False)

            total_debits = 0
            total_credits = 0

            for form in formset.forms:
                transaction = form.save(commit=False, journal_entry=journal_entry)
                logger.debug("Processing transaction: %s", transaction)

                if transaction.transaction_type == "debit":
                    total_debits += transaction.amount
                elif transaction.transaction_type == "credit":
                    total_credits += transaction.amount

            logger.info(
                "Total debits: %s, Total credits: %s", total_debits, total_credits
            )

            if total_debits != total_credits:
                logger.error(
                    "Debits (%s) do not equal credits (%s).",
                    total_debits,
                    total_credits,
                )
                messages.error(
                    request,
                    "Total debits must equal total credits.",
                    extra_tags="danger",
                )
                journal_entry.delete()
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
        journal_form = JournalEntryForm()
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


# =================================== ledger_report ist view ===================================
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


# =================================== profit_and_loss_view ===================================
@login_required
@admin_or_manager_required
def profit_and_loss_view(request):
    # Default date range values
    start_date = None
    end_date = None

    # Initialize the profit and loss sections with dynamic sections
    profit_and_loss = {
        "Income": [],
        "Expenses": [],
        "Summary": [
            {"label": "Gross Profit", "value": 0.0},
            {"label": "Net Profit", "value": 0.0},
        ],
    }

    # Initialize the form
    form = ReportPeriodForm(request.GET or None)

    if form.is_valid():
        # Extract the start and end dates from the form
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]

        # Filter data based on the date range
        # Step 1: Query the related SaleDetails for the desired Sale objects
        sales_details = SaleDetail.objects.filter(
            sale__trans_date__range=(start_date, end_date)
        )

        expense_transactions = Transaction.objects.filter(
            journal_entry__transaction_date__range=(start_date, end_date),
            account__account_type="expense",
        )
        other_income_transactions = Transaction.objects.filter(
            journal_entry__transaction_date__range=(start_date, end_date),
            account__account_type="revenue",
        ).exclude(account__account_name="Sales Revenue")

        # Step 2: Aggregate total revenue (Sum of quantity * price)
        total_revenue = sales_details.aggregate(
            total_revenue=Sum(F("quantity") * F("price"))
        )

        # Step 3: Extract the total revenue value from the dictionary
        # Ensure it is a Decimal (if None, set to Decimal("0.00"))
        revenue_value = Decimal(total_revenue["total_revenue"] or "0.00")

        # Step 4: Calculate Other Income (Sum of amounts for income transactions)
        other_income = other_income_transactions.aggregate(total_income=Sum("amount"))[
            "total_income"
        ] or Decimal(
            "0.00"
        )  # Default to Decimal(0.00) if None or no data

        # Step 5: Calculate Total Income (Revenue + Other Income)
        total_income = revenue_value + other_income

        # Dynamic Operating Expenses Calculation (Aggregate by Account Name or Account Type)
        expense_categories = (
            expense_transactions.values(
                "account__account_name", "account__account_number"
            )
            .annotate(total_expense=Sum("amount"))
            .order_by("account__account_number")
        )

        operating_expenses = {}
        for category in expense_categories:
            account_name = category["account__account_name"]
            account_number = category["account__account_number"]
            operating_expenses[f"{account_number} - {account_name}"] = category[
                "total_expense"
            ]

        total_expenses = sum(operating_expenses.values())

        # Calculate COGS (Cost of Goods Sold)
        cogs = (
            SaleDetail.objects.filter(sale__trans_date__range=[start_date, end_date])
            .annotate(cogs=F("product_volume__volume__cost") * F("quantity"))
            .aggregate(total_cogs=Sum("cogs"))
        )["total_cogs"] or 0

        # Calculate Gross Profit (Revenue - COGS)
        gross_profit = revenue_value - cogs

        # Calculate Net Profit (Gross Profit + Other Income - Operating Expenses)
        net_profit = gross_profit + other_income - total_expenses

        # Update the profit_and_loss dictionary with dynamic values
        # Income Section
        profit_and_loss["Income"].append(
            {"label": "Sales Revenue", "value": revenue_value}
        )

        # Split Other Income into categories (if applicable)
        other_income_categories = (
            other_income_transactions.values(
                "account__account_name", "account__account_number"
            )
            .annotate(total_other_income=Sum("amount"))
            .order_by("account__account_number")
        )
        for income_category in other_income_categories:
            account_name = income_category["account__account_name"]
            account_number = income_category["account__account_number"]
            profit_and_loss["Income"].append(
                {
                    "label": f"{account_number} - {account_name}",
                    "value": income_category["total_other_income"],
                }
            )

        profit_and_loss["Income"].append(
            {"label": "Total Other Income", "value": other_income}
        )
        profit_and_loss["Income"].append(
            {"label": "Total Income", "value": total_income}
        )

        # Expenses Section (Dynamic categories from operating_expenses)
        for category, value in operating_expenses.items():
            profit_and_loss["Expenses"].append({"label": category, "value": value})

        # Add the total expenses
        profit_and_loss["Expenses"].append(
            {"label": "Total Expenses", "value": total_expenses}
        )

        # Add Cost of Goods Sold (COGS)
        profit_and_loss["Expenses"].append(
            {"label": "Cost of Goods Sold (COGS)", "value": cogs}
        )

        # Summary Section
        profit_and_loss["Summary"][0]["value"] = gross_profit
        profit_and_loss["Summary"][1]["value"] = net_profit

    # Pass data to the template
    context = {
        "form": form,
        "profit_and_loss": profit_and_loss,
        "start_date": start_date,
        "end_date": end_date,
        "table_title": "Profit and Loss Statement",
    }
    return render(request, "finance/profit_and_loss.html", context)


@login_required
@admin_or_manager_required
def balance_sheet_view(request):
    # Set the date range (start_date, end_date) based on user input or defaults
    start_date = request.GET.get("start_date", datetime.today().strftime("%Y-%m-%d"))
    end_date = request.GET.get("end_date", datetime.today().strftime("%Y-%m-%d"))

    # Convert string dates to date objects
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Fetch transactions for the selected date range
    transactions = Transaction.objects.filter(
        journal_entry__transaction_date__range=[start_date, end_date]
    )

    # Initialize the balances
    assets = 0
    liabilities = 0
    equity = 0
    revenue = 0
    expenses = 0

    # Calculate the balances based on account type
    for account in ChartOfAccounts.objects.all():
        account_transactions = transactions.filter(account=account)

        # Calculate the net balance for the account
        debit_total = (
            account_transactions.filter(transaction_type="debit").aggregate(
                Sum("amount")
            )["amount__sum"]
            or 0
        )
        credit_total = (
            account_transactions.filter(transaction_type="credit").aggregate(
                Sum("amount")
            )["amount__sum"]
            or 0
        )
        net_balance = debit_total - credit_total

        total_amount = account_transactions.aggregate(Sum("amount"))["amount__sum"] or 0

        if account.account_type == "asset":
            assets += net_balance
        elif account.account_type == "liability":
            liabilities += net_balance
        elif account.account_type == "equity":
            equity += total_amount
        elif account.account_type == "revenue":
            revenue += total_amount
        elif account.account_type == "expense":
            expenses += total_amount

    # Fetch SaleDetails within the date range
    sales_details = SaleDetail.objects.filter(
        sale__trans_date__range=(start_date, end_date)
    )

    # Initialize sales revenue
    sales_revenue = 0

    # Loop through each SaleDetail and apply the discount logic
    for sale_detail in sales_details:
        # Get the corresponding Product instance
        product = sale_detail.product
        discounted_price = product.get_discounted_price()

        # Accumulate revenue (discounted price * quantity)
        sales_revenue += discounted_price * sale_detail.quantity

    # Calculate Cost of Goods Sold (COGS) with discounts considered for prices
    cogs = (
        SaleDetail.objects.filter(sale__trans_date__range=[start_date, end_date])
        .annotate(cogs=F("product_volume__volume__cost") * F("quantity"))
        .aggregate(total_cogs=Sum("cogs"))
    )["total_cogs"] or 0

    # Calculate Gross Profit (Sales Revenue - COGS)
    gross_profit = sales_revenue - cogs

    # Calculate Net Profit (Gross Profit + Other Income - Operating Expenses)
    net_income = gross_profit + revenue - expenses

    # Calculate Retained Earnings: Retained Earnings = Net Income + Previous Retained Earnings
    retained_earnings = equity + net_income

    # Ensure assets = liabilities + equity
    liabilities = assets - equity

    # Return the result to the template
    context = {
        "start_date": start_date,
        "end_date": end_date,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "retained_earnings": retained_earnings,
        "net_income": net_income,
        "table_title": "Statement of Financial Position",
    }

    return render(request, "finance/balance_sheet.html", context)


# balance_sheet_select_period
def balance_sheet_select_period(request):
    financial_periods = FinancialPeriod.objects.filter(status="open")
    return render(
        request,
        "finance/select_balance_sheet_pro_period.html",
        {"financial_periods": financial_periods},
    )


@login_required
def balance_sheet_pro_view(request, financial_period_id=None):
    # Default to current date if no financial period is provided
    if financial_period_id:
        financial_period = get_object_or_404(FinancialPeriod, id=financial_period_id)
        if financial_period.status != "open":
            return render(
                request,
                "finance/error.html",
                {
                    "error": "Cannot generate balance sheet for a closed financial period."
                },
            )
        start_date = financial_period.start_date
        end_date = financial_period.end_date
    else:
        start_date = request.GET.get(
            "start_date", datetime.today().strftime("%Y-%m-%d")
        )
        end_date = request.GET.get("end_date", datetime.today().strftime("%Y-%m-%d"))
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        financial_period = None

    # Initialize balance sheet sections
    assets = {"total": Decimal("0.00"), "accounts": []}
    liabilities = {"total": Decimal("0.00"), "accounts": []}
    equity = {"total": Decimal("0.00"), "accounts": []}

    # Fetch active accounts
    accounts = ChartOfAccounts.objects.filter(status="active", is_deleted=False)

    # Calculate account balances
    for account in accounts:
        transactions = Transaction.objects.filter(
            journal_entry__transaction_date__range=[start_date, end_date],
            journal_entry__financial_period=(
                financial_period if financial_period else Q()
            ),
            account=account,
        ).aggregate(
            total_debit=Sum("amount", filter=Q(transaction_type="debit")),
            total_credit=Sum("amount", filter=Q(transaction_type="credit")),
        )

        debit = transactions["total_debit"] or Decimal("0.00")
        credit = transactions["total_credit"] or Decimal("0.00")
        balance = debit - credit if account.balance_type == "debit" else credit - debit

        if balance == 0:
            continue

        account_data = {
            "name": account.account_name,
            "number": account.account_number,
            "balance": balance,
            "sub_accounts": [],
        }

        # Handle sub-accounts
        for sub_account in account.sub_accounts.filter(
            status="active", is_deleted=False
        ):
            sub_transactions = Transaction.objects.filter(
                journal_entry__transaction_date__range=[start_date, end_date],
                journal_entry__financial_period=(
                    financial_period if financial_period else Q()
                ),
                account=sub_account,
            ).aggregate(
                total_debit=Sum("amount", filter=Q(transaction_type="debit")),
                total_credit=Sum("amount", filter=Q(transaction_type="credit")),
            )
            sub_debit = sub_transactions["total_debit"] or Decimal("0.00")
            sub_credit = sub_transactions["total_credit"] or Decimal("0.00")
            sub_balance = (
                sub_debit - sub_credit
                if sub_account.balance_type == "debit"
                else sub_credit - sub_debit
            )

            if sub_balance != 0:
                account_data["sub_accounts"].append(
                    {
                        "name": sub_account.account_name,
                        "number": sub_account.account_number,
                        "balance": sub_balance,
                    }
                )
                balance += sub_balance

        # Assign balance to appropriate section
        if account.account_type == "asset":
            if account.is_contra_asset:
                assets["total"] -= balance
            else:
                assets["total"] += balance
            assets["accounts"].append(account_data)
        elif account.account_type == "liability":
            liabilities["total"] += balance
            liabilities["accounts"].append(account_data)
        elif account.account_type == "equity":
            equity["total"] += balance
            equity["accounts"].append(account_data)

    # Calculate net income from Transactions
    revenue_transactions = Transaction.objects.filter(
        journal_entry__transaction_date__range=[start_date, end_date],
        journal_entry__financial_period=financial_period if financial_period else Q(),
        account__account_type="revenue",
    ).aggregate(
        total_credit=Sum("amount", filter=Q(transaction_type="credit")),
        total_debit=Sum("amount", filter=Q(transaction_type="debit")),
    )
    revenue = (revenue_transactions["total_credit"] or Decimal("0.00")) - (
        revenue_transactions["total_debit"] or Decimal("0.00")
    )

    expense_transactions = Transaction.objects.filter(
        journal_entry__transaction_date__range=[start_date, end_date],
        journal_entry__financial_period=financial_period if financial_period else Q(),
        account__account_type="expense",
    ).aggregate(
        total_debit=Sum("amount", filter=Q(transaction_type="debit")),
        total_credit=Sum("amount", filter=Q(transaction_type="credit")),
    )
    expenses = (expense_transactions["total_debit"] or Decimal("0.00")) - (
        expense_transactions["total_credit"] or Decimal("0.00")
    )

    net_income = revenue - expenses

    # Update retained earnings in equity
    retained_earnings_account = accounts.filter(
        account_type="equity", account_name__icontains="retained earnings"
    ).first()
    if retained_earnings_account:
        retained_earnings_data = next(
            (
                acc
                for acc in equity["accounts"]
                if acc["name"].lower() == "retained earnings"
            ),
            None,
        )
        if retained_earnings_data:
            retained_earnings_data["balance"] += net_income
        else:
            equity["accounts"].append(
                {
                    "name": "Retained Earnings",
                    "number": retained_earnings_account.account_number,
                    "balance": net_income,
                    "sub_accounts": [],
                }
            )
        equity["total"] += net_income

    # Verify balance
    total_liabilities_and_equity = liabilities["total"] + equity["total"]
    if abs(assets["total"] - total_liabilities_and_equity) > Decimal("0.01"):
        return render(
            request,
            "finance/error.html",
            {
                "error": f'Balance sheet does not balance: Assets ({assets["total"]}) ≠ Liabilities + Equity ({total_liabilities_and_equity})'
            },
        )

    context = {
        "financial_period": financial_period,
        "start_date": start_date,
        "end_date": end_date,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "net_income": net_income,
        "total_liabilities_and_equity": total_liabilities_and_equity,
        "date": timezone.now().date(),
        "table_title": "Statement of Financial Position",
    }
    return render(request, "finance/balance_sheet_pro.html", context)


# @login_required
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


@login_required
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


@login_required
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
        return HttpResponse("Invalid date format. Use YYYY-MM-DD.", status=400)

    user = User.objects.get(id=user_id) if user_id else None
    if user_id and not user:
        return HttpResponse("User not found.", status=404)

    report_data = generate_audit_log_report(start_date, end_date, user)

    if request.GET.get("download"):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit_log_report.csv"'
        response.write("Timestamp,User,Model,Action,Object ID,Details\n")
        for entry in report_data:
            response.write(
                ",".join(
                    [
                        entry["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                        entry["user"],
                        entry["model"],
                        entry["action"],
                        str(entry["object_id"]),
                        f'"{entry['details'].replace('"', '""')}"',
                    ]
                )
                + "\n"
            )
        return response

    # Pagination
    paginator = Paginator(report_data, 10)  # Show 10 entries per page
    try:
        report_data_paginated = paginator.page(page)
    except PageNotAnInteger:
        report_data_paginated = paginator.page(1)
    except EmptyPage:
        report_data_paginated = paginator.page(paginator.num_pages)

    context = {
        "report_data": report_data_paginated,
        "users": User.objects.all(),
        "start_date": start_date,
        "end_date": end_date,
        "selected_user": user,
    }
    return render(request, "finance/audit_logs.html", context)
