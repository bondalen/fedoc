# Чат: Решение проблем с параметрами в Apache AGE Cypher

**Дата:** 19 января 2025  
**Участники:** Александр, Claude  
**Тема:** Анализ и решение ограничений Apache AGE с синтаксисом Cypher

## 🎯 Цель чата

Исследовать и решить проблему с ограничениями Apache AGE 1.6.0 при использовании параметров в переменной глубине путей Cypher запросов, которая возникла после миграции с ArangoDB на PostgreSQL + Apache AGE.

## 🔍 Проблема

### Исходная ситуация:
- **Graph Viewer** успешно мигрирован с ArangoDB на PostgreSQL + Apache AGE
- **Основной функционал** работает (отображение графа, выбор узлов/рёбер)
- **Проблема:** Ограничения Apache AGE с синтаксисом Cypher для параметров в переменной глубине путей

### Конкретные ограничения:
1. **Параметры в переменной глубине** - `*1..$max_depth` не поддерживается
2. **PREPARE/EXECUTE подход** - ошибка `build_vle_match_edge(): properties argument must be an object`
3. **Прямая передача параметров** - ошибка `third argument of cypher function must be a parameter`

## 🧪 Проведённые тесты

### 1. Тестирование базовых Cypher запросов
```sql
-- ✅ РАБОТАЕТ
MATCH (n)-[r*1..3]-(m) RETURN n, r, m
MATCH (n)-[r*1..5]-(m) RETURN n, r, m
MATCH (n)-[r*1..10]-(m) RETURN n, r, m
```

### 2. Тестирование параметров
```sql
-- ❌ НЕ РАБОТАЕТ
MATCH (n)-[r*1..$max_depth]-(m) RETURN n, r, m
-- Ошибка: third argument of cypher function must be a parameter
```

### 3. Тестирование PREPARE/EXECUTE
```sql
-- ❌ НЕ РАБОТАЕТ
PREPARE find_relatives(agtype) AS ...
EXECUTE find_relatives('{"max_depth": 3}');
-- Ошибка: build_vle_match_edge(): properties argument must be an object
```

### 4. Тестирование PL/pgSQL функций
```sql
-- ❌ НЕ РАБОТАЕТ
CREATE OR REPLACE FUNCTION find_relatives_func(max_depth INTEGER) ...
-- Синтаксические ошибки
```

## 💡 Найденное решение

### Функция `_aa3` - динамическая генерация запросов

**Созданная функция:**
```sql
CREATE OR REPLACE FUNCTION _aa3 (max_depth int)
RETURNS TABLE(n agtype, r agtype, m agtype)
AS $a$
DECLARE
    s1 text;
    s2 text;
    s3 text;
    s4 text;
    s5 text;
    s6 text;
    s7 text;
    query_string TEXT;
BEGIN
    s1 := 'SELECT * FROM cypher (';
    s2 := '''common_project_graph'', ';
    s3 := '$$ ';
    s4 := 'MATCH (n)-[r*1..';
    s5 := ']-(m) RETURN n, r, m LIMIT 5 ';
    s6 := '$$ ';
    s7 := ') as (n agtype, r agtype, m agtype);';

    query_string := s1 || s2 || s3 || s4 || max_depth || s5 || s6 || s7;
    RETURN QUERY EXECUTE query_string;
END;
$a$ LANGUAGE plpgsql;
```

### Результаты тестирования:
```sql
-- ✅ РАБОТАЕТ
SELECT * FROM _aa3(1);   -- Глубина 1
SELECT * FROM _aa3(3);    -- Глубина 3  
SELECT * FROM _aa3(5);    -- Глубина 5
SELECT * FROM _aa3(10);   -- Глубина 10
```

## 🎉 Результат

### ✅ Проблема решена!

**Функция `_aa3` успешно решает проблему с параметрами в Apache AGE**, используя:

1. **Динамическую генерацию строки запроса** с встроенным параметром глубины
2. **Выполнение через `EXECUTE`** - обходит ограничения Apache AGE
3. **Возврат результатов** в правильном формате

### Принцип работы:
- Функция принимает параметр `max_depth int`
- Динамически генерирует строку Cypher запроса с встроенным значением
- Выполняет запрос через `EXECUTE`
- Возвращает результаты в формате agtype

## 🔧 Применение для Graph Viewer

### Обновление API сервера:
```python
# Вместо проблемного синтаксиса:
# MATCH path = (start)-[e:project_relation*1..{depth}]->(target)

# Используем функцию:
def get_subgraph_with_depth(node_id, max_depth):
    query = f"SELECT * FROM _aa3({max_depth})"
    # Выполняем запрос...
```

### Восстановление функциональности:
- **"Скрыть узел с вышестоящими"** - можно использовать функцию с нужной глубиной
- **"Скрыть узел с нижестоящими"** - аналогично
- **Динамические запросы** - теперь поддерживаются

## 📊 Технические детали

### Версии:
- **PostgreSQL:** 16.10
- **Apache AGE:** 1.6.0
- **Docker:** apache/age:latest

### Ограничения Apache AGE 1.6.0:
- ❌ Параметры в переменной глубине путей (`*1..$max_depth`)
- ❌ Прямая передача JSON параметров в cypher()
- ❌ PREPARE/EXECUTE с параметрами
- ✅ Статические значения глубины (`*1..3`, `*1..5`)
- ✅ Динамическая генерация через PL/pgSQL

## 🚀 Следующие шаги

1. **Интегрировать функцию `_aa3`** в API сервер Graph Viewer
2. **Обновить эндпоинты** для использования динамических параметров
3. **Восстановить полную функциональность** скрытия узлов с рекурсией
4. **Протестировать** все функции Graph Viewer

## 📝 Выводы

**Проблемы с синтаксисом Cypher в Apache AGE 1.6.0 успешно решены!** 

Функция `_aa3` демонстрирует рабочий подход для динамических параметров в переменной глубине путей. Это решение можно интегрировать в Graph Viewer для восстановления полной функциональности без ограничений Apache AGE.

**Ключевое открытие:** Обход ограничений Apache AGE через динамическую генерацию строк запросов в PL/pgSQL функциях.
