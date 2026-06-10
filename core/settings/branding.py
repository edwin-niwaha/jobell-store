import os


SITE_NAME = os.getenv("SITE_NAME", "Jobell Store")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Jobell Inc.")
PRIMARY_COLOR = os.getenv("PRIMARY_COLOR", "#D4AF37")
SECONDARY_COLOR = os.getenv("SECONDARY_COLOR", "#000000")
TEXT_COLOR = os.getenv("TEXT_COLOR", "#212529")
BORDER_RADIUS = os.getenv("BORDER_RADIUS", "12px")
LOGO_URL = os.getenv("LOGO_URL", "")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", os.getenv("DEFAULT_FROM_EMAIL", "support@example.com"))
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "")
