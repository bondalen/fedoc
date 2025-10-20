#!/usr/bin/env python3
import os
import psycopg2

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "15432"))
PG_DB = os.getenv("PG_DB", "fedoc")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "fedoc_test_2025")
GRAPH = os.getenv("AGE_GRAPH", "common_project_graph")

OLD_ID = int(os.getenv("OLD_ID", "1407374883553284"))
NEW_ID = int(os.getenv("NEW_ID", "1407374883553328"))


def main():
    conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASSWORD)
    conn.autocommit = True
    cur = conn.cursor()

    # Load AGE extension context
    cur.execute("LOAD 'age';")
    cur.execute("SET search_path = ag_catalog, public;")

    def q(query, cols=1):
        sql = f"SELECT * FROM cypher('{GRAPH}', $$ {query} $$) AS (" + ",".join([f"c{i} agtype" for i in range(cols)]) + ");"
        cur.execute(sql)
        return cur.fetchall()

    def build_props(projects, reltype):
        parts = []
        if projects is not None:
            arr = str(projects)  # agtype -> text like ["fepro","femsq"]
            parts.append(f"projects: {arr}")
        if reltype is not None:
            rs = str(reltype).strip('"')
            if rs:
                rs = rs.replace("'", "\\'")
                parts.append(f"relationType: '{rs}'")
        return '{' + ', '.join(parts) + '}' if parts else '{}'

    def ensure_edge(from_id: int, to_id: int, props_text: str):
        cnt_rows = q(f"MATCH (a)-[e:project_relation]->(b) WHERE id(a)={from_id} AND id(b)={to_id} RETURN count(e)", 1)
        c = int(str(cnt_rows[0][0])) if cnt_rows else 0
        if c == 0:
            q(f"MATCH (a),(b) WHERE id(a) = {from_id} AND id(b) = {to_id} CREATE (a)-[e:project_relation {props_text}]->(b) RETURN id(e)", 1)

    print(f"Fixing duplicate node: old={OLD_ID}, new={NEW_ID}")

    # 1) Outgoing edges old -> x
    out_rows = q(f"MATCH (old:canonical_node)-[e:project_relation]->(x) WHERE id(old) = {OLD_ID} RETURN id(x), e.projects, e.relationType", 3)
    print(f"Outgoing edges from old: {len(out_rows)}")
    for xid, projects, reltype in out_rows:
        xid = int(str(xid))
        props = build_props(projects, reltype)
        ensure_edge(NEW_ID, xid, props)

    # 2) Incoming edges x -> old
    in_rows = q(f"MATCH (x)-[e:project_relation]->(old:canonical_node) WHERE id(old) = {OLD_ID} RETURN id(x), e.projects, e.relationType", 3)
    print(f"Incoming edges to old: {len(in_rows)}")
    for xid, projects, reltype in in_rows:
        xid = int(str(xid))
        props = build_props(projects, reltype)
        ensure_edge(xid, NEW_ID, props)

    # 3) Delete edges around old
    q(f"MATCH (n)-[e]-() WHERE id(n) = {OLD_ID} DELETE e RETURN 1", 1)
    # 4) Delete old node
    q(f"MATCH (n) WHERE id(n) = {OLD_ID} DELETE n RETURN 1", 1)

    # Verify remain nodes for key
    rows = q("MATCH (n:canonical_node {arango_key: 'c:project'}) RETURN id(n)", 1)
    print("Remaining nodes for c:project:", [str(r[0]) for r in rows])

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
