# seed_db.py
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_backend_graphql_crm.settings")
django.setup()

from crm.models import Customer, Product
from decimal import Decimal

def run():
    print("Seeding database...")

    # sample customers
    sample_customers = [
        {"name": "Alice", "email": "alice@example.com", "phone": "+254755852877"},
        {"name": "Bob", "email": "bob@example.com", "phone": "123-456-7890"},
    ]

    for c in sample_customers:
        Customer.objects.update_or_create(email=c['email'], defaults=c)

    # sample products
    sample_products = [
        {"name": "Laptop", "price": Decimal("999.99"), "stock": 10},
        {"name": "Mouse", "price": Decimal("19.99"), "stock": 100},
        {"name": "Keyboard", "price": Decimal("49.99"), "stock": 50},
    ]

    for p in sample_products:
        Product.objects.update_or_create(name=p['name'], defaults=p)

    print("Done seeding.")

if __name__ == "__main__":
    run()
