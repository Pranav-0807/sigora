import csv
import psycopg


CSV_FILE = "../Sigora/transaction.csv"


def migrate_transactions():
    conn = psycopg.connect("dbname=sigora")

    with conn.cursor() as cur:
        with open(CSV_FILE, "r", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                cur.execute(
                    """
                    INSERT INTO transactions
                    (id, transaction_type, amount, category, description, date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        int(row["id"]),
                        row["transaction_type"],
                        float(row["amount"]),
                        row["category"],
                        row["description"],
                        row["date"]
                    )
                )

    conn.commit()
    conn.close()

    print("CSV migration completed successfully!")


if __name__ == "__main__":
    migrate_transactions()