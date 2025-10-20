-- Тестовая функция для проверки передачи параметров в Apache AGE
LOAD 'age';
SET search_path = ag_catalog, public;

-- Создаем простую тестовую функцию
CREATE OR REPLACE FUNCTION test_simple_params(max_depth INTEGER)
RETURNS TABLE(n agtype, r agtype, m agtype)
LANGUAGE plpgsql
AS $func$
DECLARE 
    sql VARCHAR;
BEGIN
    LOAD 'age';
    SET search_path TO ag_catalog;
    
    sql := FORMAT('
        SELECT *
        FROM cypher(''common_project_graph'', $$
            MATCH (n)-[r*1..%s]-(m) 
            RETURN n, r, m 
            LIMIT 2
        $$) AS (n agtype, r agtype, m agtype);
    ', max_depth);
    
    RETURN QUERY EXECUTE sql;
END;
$func$;

-- Тестируем функцию
SELECT 'Testing simple function:' as test;
SELECT * FROM test_simple_params(3);
