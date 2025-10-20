#!/usr/bin/env python3
import os
import json
import requests
import psycopg2
from psycopg2.extras import Json

ARANGO_URL = os.getenv("ARANGO_URL", "http://localhost:8529")
ARANGO_DB = os.getenv("ARANGO_DB", "fedoc")
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "")

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "15432"))
PG_DB = os.getenv("PG_DB", "fedoc")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "fedoc_test_2025")

COLLECTIONS = os.getenv("COLLECTIONS", "projects,rules").split(",")

s = requests.Session()
s.auth = (ARANGO_USER, ARANGO_PASSWORD)

cursor_endpoint = f"{ARANGO_URL}/_db/{ARANGO_DB}/_api/cursor"

def aql(query, bindVars=None, batchSize=1000):
    payload = {"query": query, "bindVars": bindVars or {}, "batchSize": batchSize}
    r = s.post(cursor_endpoint, json=payload)
    r.raise_for_status()
    res = r.json()
    for doc in res.get("result", []):
        yield doc
    while res.get("hasMore"):
        nid = res.get("id")
        r = s.put(cursor_endpoint + "/" + nid)
        r.raise_for_status()
        res = r.json()
        for doc in res.get("result", []):
            yield doc


def upsert_projects(conn):
    cur = conn.cursor()
    total = 0
    for d in aql("FOR d IN projects RETURN d"):
        key = d.get("_key") or d.get("key")
        name = d.get("name")
        description = d.get("description")
        data = d
        cur.execute(
            """
            INSERT INTO public.projects(key, name, description, data)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET
              name = EXCLUDED.name,
              description = EXCLUDED.description,
              data = EXCLUDED.data,
              updated_at = now()
            """,
            (key, name, description, Json(data)),
        )
        total += 1
    cur.close()
    print(f"projects upserted: {total}")


def upsert_rules(conn):
    cur = conn.cursor()
    total = 0
    for d in aql("FOR d IN rules RETURN d"):
        key = d.get("_key") or d.get("key")
        title = d.get("title") or d.get("name")
        description = d.get("description")
        data = d
        cur.execute(
            """
            INSERT INTO public.rules(key, title, description, data)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET
              title = EXCLUDED.title,
              description = EXCLUDED.description,
              data = EXCLUDED.data,
              updated_at = now()
            """,
            (key, title, description, Json(data)),
        )
        total += 1
    cur.close()
    print(f"rules upserted: {total}")


def main():
    conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASSWORD)
    conn.autocommit = True
    if "projects" in COLLECTIONS:
        upsert_projects(conn)
    if "rules" in COLLECTIONS:
        upsert_rules(conn)
    conn.close()

if __name__ == "__main__":
    main()
