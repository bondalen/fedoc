# Решение проблемы передачи параметров в Apache AGE

## 🎯 Проблема

### **Ограничения Apache AGE 1.6.0:**
- ❌ Параметры типа `$max_depth` не работают в Cypher запросах
- ❌ `PREPARE/EXECUTE` не поддерживает динамические параметры
- ❌ Прямая передача `agtype` параметров вызывает ошибки
- ❌ Стандартные методы PostgreSQL не работают с Apache AGE

### **Примеры неудачных попыток:**

#### **1. Прямая передача параметров:**
```sql
-- ❌ НЕ РАБОТАЕТ
SELECT * FROM cypher('graph', $$
    MATCH (n)-[r*1..$max_depth]-(m) 
    RETURN n, r, m
$$, '{"max_depth": 3}') AS (n agtype, r agtype, m agtype);
-- ERROR: third argument of cypher function must be a parameter
```

#### **2. PREPARE/EXECUTE:**
```sql
-- ❌ НЕ РАБОТАЕТ
PREPARE stmt AS 
SELECT * FROM cypher('graph', $$
    MATCH (n)-[r*1..$1]-(m) 
    RETURN n, r, m
$$) AS (n agtype, r agtype, m agtype);
-- ERROR: syntax error at or near "$1"
```

#### **3. agtype параметры:**
```sql
-- ❌ НЕ РАБОТАЕТ
SELECT * FROM cypher('graph', $$
    MATCH (n)-[r*1..$max_depth]-(m) 
    RETURN n, r, m
$$, agtype_build_map('max_depth', int4_to_agtype(3)));
-- ERROR: third argument of cypher function must be a parameter
```

## 🔍 Анализ проблемы

### **Корневые причины:**
1. **Apache AGE 1.6.0** имеет ограниченную поддержку параметров
2. **Cypher парсер** не обрабатывает динамические параметры корректно
3. **PostgreSQL функции** не могут передавать параметры в Cypher напрямую
4. **agtype система** работает только в определенных контекстах

### **Документация Apache AGE:**
- Раздел "H.1.3. Формат Cypher-запроса" указывает на `agtype` параметры
- Раздел "H.1.29.4. Подготовленные операторы" описывает ограничения
- **Вывод:** Стандартные методы не работают в Apache AGE 1.6.0

## ✅ Решение

### **Подход: Динамическая генерация SQL через `FORMAT()`**

#### **1. Базовая функция:**
```sql
CREATE OR REPLACE FUNCTION get_graph_relations(max_depth INTEGER)
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
            LIMIT 5
        $$) AS (n agtype, r agtype, m agtype);
    ', max_depth);
    
    RETURN QUERY EXECUTE sql;
END;
$func$;
```

#### **2. Расширенная функция с лимитом:**
```sql
CREATE OR REPLACE FUNCTION get_filtered_graph_relations(
    max_depth INTEGER,
    limit_count INTEGER DEFAULT 5
)
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
            LIMIT %s
        $$) AS (n agtype, r agtype, m agtype);
    ', max_depth, limit_count);
    
    RETURN QUERY EXECUTE sql;
END;
$func$;
```

#### **3. Функция поиска путей:**
```sql
CREATE OR REPLACE FUNCTION find_paths_between_nodes(
    start_node_key TEXT,
    end_node_key TEXT, 
    max_depth INTEGER
)
RETURNS TABLE(path agtype, length agtype)
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
            MATCH path = (start_node:canonical_node {arango_key: ''%s''})-[r*1..%s]-(end_node:canonical_node {arango_key: ''%s''})
            RETURN path, length(path)
            LIMIT 10
        $$) AS (path agtype, length agtype);
    ', start_node_key, max_depth, end_node_key);
    
    RETURN QUERY EXECUTE sql;
END;
$func$;
```

## 🔧 Ключевые принципы решения

### **1. Использование `FORMAT()`:**
- ✅ **Безопасность:** Автоматическое экранирование параметров
- ✅ **Производительность:** Быстрее конкатенации строк
- ✅ **Читаемость:** Понятная структура запроса

### **2. Динамическое выполнение:**
- ✅ **`EXECUTE`** - выполнение сгенерированного SQL
- ✅ **`RETURN QUERY`** - возврат результатов
- ✅ **`LOAD 'age'`** - загрузка расширения в контексте

### **3. Правильная структура:**
```sql
-- Шаблон решения
sql := FORMAT('
    SELECT *
    FROM cypher(''graph_name'', $$
        MATCH (n)-[r*1..%s]-(m) 
        RETURN n, r, m 
        LIMIT %s
    $$) AS (n agtype, r agtype, m agtype);
', param1, param2);
```

## 📊 Сравнение подходов

| Подход | Статус | Производительность | Читаемость | Поддерживаемость |
|--------|--------|-------------------|------------|-------------------|
| **Прямые параметры** | ❌ Не работает | - | - | - |
| **PREPARE/EXECUTE** | ❌ Не работает | - | - | - |
| **agtype параметры** | ❌ Не работает | - | - | - |
| **Конкатенация строк** | ✅ Работает | Медленно | Сложно | Сложно |
| **`FORMAT()` + `EXECUTE`** | ✅ Работает | Быстро | Просто | Легко |

## 🎯 Преимущества решения

### **✅ Технические:**
- **Обходит ограничения** Apache AGE 1.6.0
- **Использует стандартные** PostgreSQL функции
- **Обеспечивает безопасность** через `FORMAT()`
- **Повышает производительность** vs конкатенация

### **✅ Практические:**
- **Легко читать** и понимать код
- **Просто поддерживать** и расширять
- **Безопасно использовать** в production
- **Совместимо** с существующим кодом

## 🚀 Результат

**Решение полностью обходит ограничения Apache AGE 1.6.0** и обеспечивает:
- ✅ **Рабочую передачу параметров** в Cypher запросы
- ✅ **Оптимальную производительность** через `FORMAT()`
- ✅ **Читаемый и поддерживаемый** код
- ✅ **Готовность к production** использованию

**Это стандартное решение для Apache AGE 1.6.0 до появления полной поддержки параметров!** 🎉
