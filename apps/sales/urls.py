from django.urls import path

from . import views

app_name = "sales"

# Sales URLs
urlpatterns = [
    path("", views.sales_list_view, name="sales_list"),
    path("sales-report/", views.sales_report_view, name="sales_report"),
    path("add", views.sales_add_view, name="sales_add"),
    path("details/<str:sale_id>", views.sales_details_view, name="sales_details"),
    path("sale/delete/<int:sale_id>/", views.sale_delete_view, name="delete_sale"),
    path("pdf/<str:sale_id>", views.receipt_pdf_view, name="sales_receipt_pdf"),
]
