"""Small native-SQL document repository. A short mutex transaction serializes quotas.

No external API or image work may run inside transaction(). IDs encode unique
business keys (email identity, payment event, invitee reward), enforced by the PK.
Demo snapshots are local-only and atomically replaced; live always uses MySQL.
"""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import json
import os
import threading

class Tx:
    def get(self, bucket, key): raise NotImplementedError
    def put(self, bucket, key, value): raise NotImplementedError
    def delete(self, bucket, key): raise NotImplementedError
    def all(self, bucket): raise NotImplementedError

class MemoryTx(Tx):
    def __init__(self, data): self.data = data
    def get(self, bucket, key): return deepcopy(self.data.get(bucket, {}).get(key))
    def put(self, bucket, key, value): self.data.setdefault(bucket, {})[key] = deepcopy(value)
    def delete(self, bucket, key): self.data.get(bucket, {}).pop(key, None)
    def all(self, bucket): return deepcopy(list(self.data.get(bucket, {}).values()))

class DemoStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.lock = threading.RLock()
        self.data = json.loads(self.path.read_text()) if self.path and self.path.exists() else {}
    @contextmanager
    def transaction(self):
        with self.lock:
            candidate = deepcopy(self.data)
            yield MemoryTx(candidate)
            if self.path:
                temp = self.path.with_suffix('.tmp')
                temp.write_text(json.dumps(candidate, ensure_ascii=False))
                temp.chmod(0o600)
                temp.replace(self.path)
            self.data = candidate

class MySQLTx(Tx):
    def __init__(self, cursor): self.cursor = cursor
    def get(self, bucket, key):
        self.cursor.execute('SELECT payload FROM emjo_records WHERE bucket=%s AND record_id=%s', (bucket,key))
        row = self.cursor.fetchone()
        return json.loads(row[0]) if row else None
    def put(self, bucket, key, value):
        self.cursor.execute('INSERT INTO emjo_records (bucket,record_id,payload) VALUES (%s,%s,%s) '
                            'ON DUPLICATE KEY UPDATE payload=VALUES(payload)',
                            (bucket,key,json.dumps(value,ensure_ascii=False)))
    def delete(self, bucket, key):
        self.cursor.execute('DELETE FROM emjo_records WHERE bucket=%s AND record_id=%s', (bucket,key))
    def all(self, bucket):
        self.cursor.execute('SELECT payload FROM emjo_records WHERE bucket=%s', (bucket,))
        return [json.loads(row[0]) for row in self.cursor.fetchall()]

class MySQLStore:
    def connect(self):
        import pymysql
        return pymysql.connect(host=os.environ['EMJO_MYSQL_HOST'], port=int(os.getenv('EMJO_MYSQL_PORT') or 3306),
            user=os.environ['EMJO_MYSQL_USER'], password=os.environ['EMJO_MYSQL_PASSWORD'],
            database=os.environ['EMJO_MYSQL_DATABASE'], charset='utf8mb4', autocommit=False,
            connect_timeout=5, read_timeout=15, write_timeout=15)
    @contextmanager
    def transaction(self):
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT id FROM emjo_mutex WHERE id=1 FOR UPDATE')
                if not cursor.fetchone(): raise RuntimeError('Run the EMJO schema migration first')
                yield MySQLTx(cursor)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
