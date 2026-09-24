import os
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row


@contextmanager
def connect():
    # A failed request rolls back its whole transaction.
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as connection:
        yield connection


def initialize():
    from pathlib import Path
    with connect() as connection:
        connection.execute(Path(__file__).with_name("schema.sql").read_text())
