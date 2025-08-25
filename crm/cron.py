import datetime
import os
import requests
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
