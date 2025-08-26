#!/usr/bin/env python3
"""
Fetch orders placed within the last 7 days via GraphQL
and log reminders with timestamps.
"""

import sys
import asyncio
from datetime import datetime, timedelta
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# GraphQL endpoint
GRAPHQL_URL = "http://localhost:8000/graphql"
LOG_FILE = "/tmp/order_reminders_log.txt"

# Define the query
query = gql("""
    query GetRecentOrders($cutoff: DateTime!) {
        orders(orderDate_Gte: $cutoff) {
            id
            customer {
                email
            }
        }
    }
""")

async def fetch_orders():
    # Set up transport
    transport = RequestsHTTPTransport(
        url=GRAPHQL_URL,
        verify=True,
        retries=3,
    )

    client = Client(transport=transport, fetch_schema_from_transport=True)

    # Cutoff date (7 days ago)
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()

    try:
        result = await client.execute_async(query, variable_values={"cutoff": cutoff})
        orders = result.get("orders", [])
        return orders
    except Exception as e:
        sys.stderr.write(f"GraphQL query failed: {e}\n")
        return []

async def main():
    orders = await fetch_orders()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(LOG_FILE, "a") as f:
        for order in orders:
            order_id = order.get("id")
            email = order.get("customer", {}).get("email")
            if order_id and email:
                line = f"[{ts}] Order {order_id} → Reminder sent to {email}\n"
                f.write(line)

    print("Order reminders processed!")

if __name__ == "__main__":
    asyncio.run(main())
