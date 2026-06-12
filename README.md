# Jobel Retail

**Jobel Retail** is a comprehensive retail management system designed to streamline business operations, enhance inventory tracking, monitor sales, and strengthen customer relationships. With real-time data updates and an intuitive interface, it is ideal for managing retail stores of any size.

## Features

- **Inventory & Product Management**: Easily track stock levels and manage products.
- **Sales Tracking**: Access detailed sales reports for better insights.
- **Real-Time Stock Updates**: Maintain accurate inventory levels at all times.
- **Customer Relationship Management (CRM)**: Manage customer data and interactions effectively.
- **Customizable Dashboard**: Tailor the dashboard to fit your business needs.

## Requirements

Ensure you have the following installed on your system:

- **Python**: 3.9.13
- **Node.js**: 16.7.1
- **PostgreSQL/MySQL**: Depending on your database choice
- **Django**: Version 3.x or higher
- **Django REST Framework**: (if applicable)
- **Git**: (optional for version control)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/edwin-niwaha/jobel_retail
cd jobel_retail
cd backend
```

### 2. Set Up Python Environment
Create a virtual environment:
```bash
python -m venv .venv

```
### Activate the virtual environment:

- Windows:
```bash
source .venv/Scripts/activate
  # Powershell
    deactivate
    .venv\Scripts\Activate
```


### 3. Install Required Python Packages
```bash
pip install -r requirements.txt
pip freeze > requirements.txt
```

### 4. Set Up Database
- Create a new database in PostgreSQL/MySQL.
- Update your database settings in settings.py.

### 5. Run Migrations
```bash
python manage.py migrate
```

### 6. Create Superuser (optional)
```bash
python manage.py createsuperuser
```

### 7. Seed Initial Data (if applicable)
```bash
python manage.py loaddata <fixture-file>
```

### 8. Frontend Setup (if applicable)
- Navigate to the frontend directory:
```bash
cd frontend
```
### Install Node packages:
```bash
npm install
```

### Start the frontend development server:
```bash
npm start
```

### 9. Run the Django Development Server
```bash
python manage.py runserver
```
### 10. Access the Application
-Open your browser and go to:
http://127.0.0.1:8000

## Async Email Worker

Order confirmation, payment confirmation, order status updates, and admin new-order notifications are queued with Celery and sent through Resend.

Set these environment variables locally or copy `.env.example` to `.env` and fill in real values:

```bash
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
RESEND_API_KEY=
DEFAULT_FROM_EMAIL="My Store <noreply@example.com>"
RESEND_FROM_EMAIL="My Store <noreply@example.com>"
SITE_NAME=My Store
SITE_URL=http://127.0.0.1:8000
ADMIN_ORDER_EMAILS=owner@example.com,manager@example.com
```

Start Redis:

```bash
redis-server
```

Start Django:

```bash
python manage.py runserver
```

Start the Celery worker:

```bash
celery -A core worker -l info
```

- Additional Notes
- Ensure your environment variables are set up correctly, especially for sensitive information like - - API keys and database passwords.
- For production, consider using a web server like Gunicorn with Nginx or Apache.


python manage.py collectstatic --noinput