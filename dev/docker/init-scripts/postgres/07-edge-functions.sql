-- ============================================================================
-- EDGE helper functions for Graph Viewer (PostgreSQL + Apache AGE)
-- Creates create_edge_safe() used by migration script
-- ============================================================================

\c fedoc
LOAD 'age';
SET search_path = ag_catalog, "$user", public;

-- Recreate function with expected signature
DROP FUNCTION IF EXISTS ag_catalog.create_edge_safe(TEXT, BIGINT, BIGINT, TEXT, JSONB);

CREATE OR REPLACE FUNCTION ag_catalog.create_edge_safe(
    graph_name TEXT,
    from_vertex_id BIGINT,
    to_vertex_id BIGINT,
    edge_label TEXT,
    properties JSONB DEFAULT '{}'::jsonb
) RETURNS TABLE(success BOOLEAN, edge_id TEXT, error_message TEXT) AS $$
DECLARE
    res_eid agtype;
    props_text TEXT;
    sql TEXT;
BEGIN
    -- Build properties object text for inline Cypher
    props_text := COALESCE(properties::text, '{}');

    sql := FORMAT('
        SELECT * FROM cypher(''%s'', $$
            MATCH (a) WHERE id(a) = %s
            MATCH (b) WHERE id(b) = %s
            CREATE (a)-[e:%I %s]->(b)
            RETURN id(e)
        $$) AS (eid agtype);
    ', graph_name, from_vertex_id, to_vertex_id, edge_label, props_text);

    EXECUTE sql INTO res_eid;

    RETURN QUERY SELECT TRUE, res_eid::text, NULL::TEXT;
EXCEPTION WHEN OTHERS THEN
    RETURN QUERY SELECT FALSE, NULL::TEXT, SQLERRM;
END;
$$ LANGUAGE plpgsql;
