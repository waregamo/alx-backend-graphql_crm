# crm/schema.py
import re
import graphene
from graphene import Field, List, String, ID, Decimal, Int
from graphene_django import DjangoObjectType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction, DatabaseError
from django.utils import timezone
from decimal import Decimal as PyDecimal

from .models import Customer, Product, Order

# ----------------------------
# Graphene types
# ----------------------------
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "order_date", "total_amount")

# ----------------------------
# Helpers
# ----------------------------
PHONE_REGEXES = [
    re.compile(r'^\+\d{7,15}$'),                      # +1234567890...
    re.compile(r'^\d{3}-\d{3}-\d{4}$'),               # 123-456-7890
    re.compile(r'^\d{7,15}$'),                        # 1234567890...
]

def validate_phone(phone: str):
    if not phone:
        return True
    for rx in PHONE_REGEXES:
        if rx.match(phone):
            return True
    raise ValidationError("Invalid phone format. Use +1234567890 or 123-456-7890 or plain digits.")

# ----------------------------
# Mutations
# ----------------------------
class CreateCustomerPayload(graphene.ObjectType):
    customer = Field(CustomerType)
    success = graphene.Boolean()
    message = graphene.String()

class CreateCustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)

class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CreateCustomerInput(required=True)

    Output = CreateCustomerPayload

    @staticmethod
    def mutate(root, info, input):
        name = input.name.strip()
        email = input.email.strip().lower()
        phone = input.phone.strip() if input.phone else None

        # Validate phone format
        try:
            validate_phone(phone)
        except ValidationError as e:
            return CreateCustomerPayload(customer=None, success=False, message=str(e))

        # Ensure email uniqueness
        if Customer.objects.filter(email=email).exists():
            return CreateCustomerPayload(customer=None, success=False, message="Email already exists.")

        try:
            customer = Customer.objects.create(name=name, email=email, phone=phone)
            return CreateCustomerPayload(customer=customer, success=True, message="Customer created successfully.")
        except Exception as e:
            return CreateCustomerPayload(customer=None, success=False, message=f"Failed to create customer: {str(e)}")


# ----------------------------
# Bulk Create Customers
# ----------------------------
class BulkCreateCustomersPayload(graphene.ObjectType):
    customers = List(CustomerType)
    errors = List(String)

class CustomerInputForBulk(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = List(CustomerInputForBulk, required=True)

    Output = BulkCreateCustomersPayload

    @staticmethod
    def mutate(root, info, input):
        created = []
        errors = []

        # Use a single outer transaction; use savepoints for per-record rollback
        try:
            with transaction.atomic():
                for idx, entry in enumerate(input):
                    sp = transaction.savepoint()
                    try:
                        name = entry.name.strip()
                        email = entry.email.strip().lower()
                        phone = entry.phone.strip() if getattr(entry, 'phone', None) else None

                        try:
                            validate_phone(phone)
                        except ValidationError as e:
                            raise ValueError(f"Row {idx}: Invalid phone: {e}")

                        if Customer.objects.filter(email=email).exists():
                            raise ValueError(f"Row {idx}: Email already exists: {email}")

                        # create
                        c = Customer.objects.create(name=name, email=email, phone=phone)
                        created.append(c)
                        # release savepoint implicitly by not rolling back
                    except Exception as e:
                        # rollback to savepoint for this record and continue
                        transaction.savepoint_rollback(sp)
                        errors.append(str(e))
                # After loop: commit outer transaction - keeps the successful creates
        except DatabaseError as e:
            # If outer transaction failed catastrophically
            errors.append(f"Database error: {str(e)}")

        return BulkCreateCustomersPayload(customers=created, errors=errors)


# ----------------------------
# Create Product
# ----------------------------
class CreateProductPayload(graphene.ObjectType):
    product = Field(ProductType)
    success = graphene.Boolean()
    message = graphene.String()

class CreateProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(required=False)

class CreateProduct(graphene.Mutation):
    class Arguments:
        input = CreateProductInput(required=True)

    Output = CreateProductPayload

    @staticmethod
    def mutate(root, info, input):
        name = input.name.strip()
        try:
            price = PyDecimal(str(input.price))
        except Exception:
            return CreateProductPayload(product=None, success=False, message="Invalid price format.")
        stock = input.stock if input.stock is not None else 0

        if price <= 0:
            return CreateProductPayload(product=None, success=False, message="Price must be a positive number.")
        if stock < 0:
            return CreateProductPayload(product=None, success=False, message="Stock cannot be negative.")

        try:
            product = Product.objects.create(name=name, price=price, stock=stock)
            return CreateProductPayload(product=product, success=True, message="Product created.")
        except Exception as e:
            return CreateProductPayload(product=None, success=False, message=f"Failed to create product: {e}")


# ----------------------------
# Create Order
# ----------------------------
class CreateOrderPayload(graphene.ObjectType):
    order = Field(OrderType)
    success = graphene.Boolean()
    message = graphene.String()

class CreateOrderInput(graphene.InputObjectType):
    customer_id = ID(required=True)
    product_ids = List(ID, required=True)
    order_date = graphene.String(required=False)  # ISO string optional

class CreateOrder(graphene.Mutation):
    class Arguments:
        input = CreateOrderInput(required=True)

    Output = CreateOrderPayload

    @staticmethod
    def mutate(root, info, input):
        # Validate customer
        try:
            customer = Customer.objects.get(pk=input.customer_id)
        except Customer.DoesNotExist:
            return CreateOrderPayload(order=None, success=False, message="Invalid customer ID.")

        # Validate product ids
        product_ids = input.product_ids or []
        if not product_ids:
            return CreateOrderPayload(order=None, success=False, message="At least one product must be selected.")

        products = list(Product.objects.filter(pk__in=product_ids))
        found_ids = {str(p.pk) for p in products}
        invalid_ids = [pid for pid in product_ids if str(pid) not in found_ids]
        if invalid_ids:
            return CreateOrderPayload(order=None, success=False, message=f"Invalid product ID(s): {', '.join(invalid_ids)}")

        # Create order and associate products
        try:
            with transaction.atomic():
                order = Order.objects.create(customer=customer, order_date=timezone.now())
                order.products.set(products)
                # compute total
                total = PyDecimal('0.00')
                for p in products:
                    total += p.price
                order.total_amount = total
                order.save()
            return CreateOrderPayload(order=order, success=True, message="Order created successfully.")
        except Exception as e:
            return CreateOrderPayload(order=None, success=False, message=f"Failed to create order: {str(e)}")


# ----------------------------
# Expose Query & Mutation
# ----------------------------

class Query(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)

    def resolve_customers(root, info):
        return Customer.objects.all()

    def resolve_products(root, info):
        return Product.objects.all()

    def resolve_orders(root, info):
        return Order.objects.select_related('customer').prefetch_related('products').all()

class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
