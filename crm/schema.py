import re
import graphene

from .models import Product
from crm.models import Product
from graphene import Field, List, String, ID, Decimal, Int
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.core.exceptions import ValidationError
from django.db import transaction, DatabaseError
from django.utils import timezone
from decimal import Decimal as PyDecimal


from .models import Customer, Product, Order, OrderProduct
from .filters import CustomerFilter, ProductFilter, OrderFilter

# Graphene types with Relay Node support for filters
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        filterset_class = CustomerFilter
        interfaces = (graphene.relay.Node,)
        fields = ("id", "name", "email", "phone", "created_at")

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        filterset_class = ProductFilter
        interfaces = (graphene.relay.Node,)
        fields = ("id", "name", "price", "stock", "created_at")

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        filterset_class = OrderFilter
        interfaces = (graphene.relay.Node,)
        fields = ("id", "customer", "products", "order_date", "total_amount")

# Validation helpers
PHONE_REGEXES = [
    re.compile(r'^\+\d{7,15}$'),
    re.compile(r'^\d{3}-\d{3}-\d{4}$'),
    re.compile(r'^\d{7,15}$'),
]

def validate_phone(phone: str):
    if not phone:
        return True
    for rx in PHONE_REGEXES:
        if rx.match(phone):
            return True
    raise ValidationError("Invalid phone format. Use +1234567890 or 123-456-7890 or plain digits.")

# Mutations

# --- CreateCustomer ---
class CreateCustomerPayload(graphene.ObjectType):
    customer = Field(CustomerType)
    success = graphene.Boolean()
    message = graphene.String()

class CreateCustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CreateCustomerInput(required=True)

    Output = CreateCustomerPayload

    @staticmethod
    def mutate(root, info, input):
        name = input.name.strip()
        email = input.email.strip().lower()
        phone = input.phone.strip() if input.phone else None

        try:
            validate_phone(phone)
        except ValidationError as e:
            return CreateCustomerPayload(customer=None, success=False, message=str(e))

        if Customer.objects.filter(email=email).exists():
            return CreateCustomerPayload(customer=None, success=False, message="Email already exists.")

        try:
            customer = Customer.objects.create(name=name, email=email, phone=phone)
            return CreateCustomerPayload(customer=customer, success=True, message="Customer created successfully.")
        except Exception as e:
            return CreateCustomerPayload(customer=None, success=False, message=f"Failed to create customer: {str(e)}")

# --- BulkCreateCustomers ---
class CustomerInputForBulk(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class BulkCreateCustomersPayload(graphene.ObjectType):
    customers = List(CustomerType)
    errors = List(String)

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = List(CustomerInputForBulk, required=True)

    Output = BulkCreateCustomersPayload

    @staticmethod
    def mutate(root, info, input):
        created = []
        errors = []
        try:
            with transaction.atomic():
                for idx, entry in enumerate(input):
                    sp = transaction.savepoint()
                    try:
                        name = entry.name.strip()
                        email = entry.email.strip().lower()
                        phone = entry.phone.strip() if entry.phone else None
                        validate_phone(phone)
                        if Customer.objects.filter(email=email).exists():
                            raise ValueError(f"Row {idx}: Email already exists: {email}")
                        c = Customer.objects.create(name=name, email=email, phone=phone)
                        created.append(c)
                    except Exception as e:
                        transaction.savepoint_rollback(sp)
                        errors.append(str(e))
        except DatabaseError as e:
            errors.append(f"Database error: {str(e)}")
        return BulkCreateCustomersPayload(customers=created, errors=errors)

# --- CreateProduct ---
class CreateProductPayload(graphene.ObjectType):
    product = Field(ProductType)
    success = graphene.Boolean()
    message = graphene.String()

class CreateProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int()

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
            return CreateProductPayload(product=None, success=False, message="Price must be positive.")
        if stock < 0:
            return CreateProductPayload(product=None, success=False, message="Stock cannot be negative.")
        try:
            product = Product.objects.create(name=name, price=price, stock=stock)
            return CreateProductPayload(product=product, success=True, message="Product created successfully.")
        except Exception as e:
            return CreateProductPayload(product=None, success=False, message=f"Failed to create product: {str(e)}")

# --- CreateOrder ---
class CreateOrderPayload(graphene.ObjectType):
    order = Field(OrderType)
    success = graphene.Boolean()
    message = graphene.String()

class CreateOrderInput(graphene.InputObjectType):
    customer_id = ID(required=True)
    product_ids = List(ID, required=True)
    order_date = graphene.String()

class CreateOrder(graphene.Mutation):
    class Arguments:
        input = CreateOrderInput(required=True)

    Output = CreateOrderPayload

    @staticmethod
    def mutate(root, info, input):
        try:
            customer = Customer.objects.get(pk=input.customer_id)
        except Customer.DoesNotExist:
            return CreateOrderPayload(order=None, success=False, message="Invalid customer ID.")

        product_ids = input.product_ids or []
        if not product_ids:
            return CreateOrderPayload(order=None, success=False, message="At least one product must be selected.")

        products = list(Product.objects.filter(pk__in=product_ids))
        found_ids = {str(p.pk) for p in products}
        invalid_ids = [pid for pid in product_ids if str(pid) not in found_ids]
        if invalid_ids:
            return CreateOrderPayload(order=None, success=False, message=f"Invalid product ID(s): {', '.join(invalid_ids)}")

        try:
            with transaction.atomic():
                order = Order.objects.create(customer=customer)
                order.products.set(products)
                total = PyDecimal('0.00')
                for p in products:
                    total += p.price
                order.total_amount = total
                order.save()
            return CreateOrderPayload(order=order, success=True, message="Order created successfully.")
        except Exception as e:
            return CreateOrderPayload(order=None, success=False, message=f"Failed to create order: {str(e)}")

# Query with filters
class Query(graphene.ObjectType):
    all_customers = DjangoFilterConnectionField(CustomerType)
    all_products = DjangoFilterConnectionField(ProductType)
    all_orders = DjangoFilterConnectionField(OrderType)





  # --- UpdateLowStockProducts ---
class UpdateLowStockProductsPayload(graphene.ObjectType):
    updated_products = List(ProductType)
    success = graphene.Boolean()
    message = graphene.String()

class UpdateLowStockProducts(graphene.Mutation):
    Output = UpdateLowStockProductsPayload

    @staticmethod
    def mutate(root, info):
        try:
            low_stock_products = Product.objects.filter(stock__lt=10)
            updated_products = []
            with transaction.atomic():
                for product in low_stock_products:
                    product.stock += 10  # simulate restocking
                    product.save()
                    updated_products.append(product)

            message = f"Updated {len(updated_products)} product(s)."
            return UpdateLowStockProductsPayload(
                updated_products=updated_products,
                success=True,
                message=message,
            )
        except Exception as e:
            return UpdateLowStockProductsPayload(
                updated_products=[],
                success=False,
                message=f"Failed to update low stock: {str(e)}"
            )
  
# Mutation class wiring up
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
    update_low_stock_products = UpdateLowStockProducts.Field()

