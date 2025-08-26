import datetime
import os
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport


def log_crm_heartbeat():
    now = datetime.datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    log_message = f"{now} CRM is alive\n"

    log_file = "/tmp/crm_heartbeat_log.txt"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    with open(log_file, "a") as f:
        f.write(log_message)

    # --- Optional GraphQL check ---
    try:
        transport = RequestsHTTPTransport(
            url="http://localhost:8000/graphql",
            verify=False,
            retries=3,
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)

        query = gql(
            """
            query {
                hello
            }
            """
        )
        response = client.execute(query)
        with open(log_file, "a") as f:
            f.write(f"{now} GraphQL hello response: {response['hello']}\n")
    except Exception as e:
        with open(log_file, "a") as f:
            f.write(f"{now} GraphQL check failed: {e}\n")


def update_low_stock():
    """Run GraphQL mutation to restock low-stock products and log results."""
    now = datetime.datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    log_file = "/tmp/low_stock_updates_log.txt"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    try:
        transport = RequestsHTTPTransport(
            url="http://localhost:8000/graphql",
            verify=False,
            retries=3,
        )
        client = Client(transport=transport, fetch_schema_from_transport=True)

        mutation = gql(
            """
            mutation {
                updateLowStockProducts {
                    updatedProducts {
                        name
                        stock
                    }
                    success
                    message
                }
            }
            """
        )

        response = client.execute(mutation)
        result = response["updateLowStockProducts"]

        with open(log_file, "a") as f:
            f.write(f"{now} Mutation success: {result['success']}, message: {result['message']}\n")
            for product in result["updatedProducts"]:
                f.write(f"{now} Updated product: {product['name']} (new stock: {product['stock']})\n")

    except Exception as e:
        with open(log_file, "a") as f:
            f.write(f"{now} Mutation failed: {e}\n")

