from .models import FinancialPeriod


def open_financial_periods(request):
    return {
        "open_periods": FinancialPeriod.objects.filter(status="open").order_by(
            "-start_date"
        )
    }
