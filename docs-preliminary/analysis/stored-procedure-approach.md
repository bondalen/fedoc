# Анализ: Хранимые процедуры PostgreSQL для валидации рёбер

**Дата:** 17 октября 2025  
**Идея:** Использовать хранимые процедуры PostgreSQL для централизации логики валидации на стороне БД  
**Статус:** 🔍 Анализ и проверка

---

## 💡 **Суть предложения**

### **Ключевое отличие от триггеров:**

**Триггер (автоматический):**
- Срабатывает при INSERT/UPDATE **автоматически**
- ❌ Проблема: не может вызвать Cypher в AGE

**Хранимая процедура (явный вызов):**
- Приложение **явно вызывает** функцию
- ✅ Функция проверяет дубликаты (SQL)
- ✅ Функция вызывает Cypher CREATE
- ✅ **Вся логика на стороне БД!**

---

## 🎯 **Архитектура решения**

### **Текущая архитектура (валидация в приложении):**

```
Python приложение:
├── check_edge_uniqueness() → AQL запрос к ArangoDB
├── if unique:
│   └── insert_edge() → AQL INSERT
└── return result

Логика: 50% приложение + 50% БД
Операций: 1 проверка + 1 создание = 2 запроса
```

### **Предлагаемая архитектура (PostgreSQL функция):**

```
Python приложение:
└── SELECT create_edge_safe(from, to, label, props)

PostgreSQL функция create_edge_safe():
├── SELECT COUNT от proxy_test._ag_label_edge → проверка дубликатов
├── IF дубликат:
│   └── RETURN error
└── ELSE:
    ├── EXECUTE cypher('CREATE ...') → создание ребра
    └── RETURN success

Логика: 100% на стороне БД!
Операций: 1 вызов функции = 1 запрос из приложения
```

---

## ✅ **Преимущества подхода**

### **1. Централизация логики в БД**
```python
# Приложение (текущее):
if not edge_validator.check_uniqueness(from_id, to_id):
    raise DuplicateError()
result = db.create_edge(from_id, to_id, label)

# Приложение (с функцией БД):
result = db.call_function('create_edge_safe', from_id, to_id, label)
```
Приложение **проще**, вся логика в БД.

### **2. Атомарность**
- Проверка + создание в **одной транзакции** на стороне БД
- Нет race conditions между проверкой и создан

ием

### **3. Единая точка контроля**
- Невозможно обойти валидацию
- Все операции идут через функцию
- Логика изменяется в одном месте (функция БД)

### **4. Производительность**
```
Текущее:     2 запроса (проверка + создание)
С функцией:  1 запрос (функция делает все)
```

### **5. Независимость от языка приложения**
- Python, Java, Node.js - все вызывают одну функцию БД
- Логика не дублируется в разных приложениях

---

## ⚠️ **Потенциальные проблемы**

### **1. Может ли PL/pgSQL вызвать cypher()?**

**Нужно проверить:**
```sql
CREATE FUNCTION test() RETURNS TEXT AS $$
DECLARE
    result RECORD;
BEGIN
    -- Работает ли это?
    EXECUTE 'SELECT * FROM cypher(...) as (r agtype)'
    INTO result;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;
```

**Потенциальные проблемы:**
- cypher() возвращает SET OF records
- EXECUTE INTO может не работать с агрегированными типами
- Нужна специальная обработка agtype

### **2. Обработка ошибок**

Если Cypher CREATE упадет:
- Нужен EXCEPTION блок
- Правильный rollback
- Информативные сообщения

### **3. Возврат результата**

Нужно вернуть:
- success/failure статус
- ID созданного ребра (если успех)
- Сообщение об ошибке (если fail)

---

## 🔧 **Варианты реализации**

### **Вариант A: Простая функция (только проверка)**

```sql
CREATE FUNCTION check_and_allow(from_id BIGINT, to_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    dup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO dup_count
    FROM proxy_test._ag_label_edge
    WHERE (start_id = from_id AND end_id = to_id)
       OR (start_id = to_id AND end_id = from_id);
    
    RETURN (dup_count = 0);
END;
$$ LANGUAGE plpgsql;

-- Приложение:
if db.call('check_and_allow', from, to):
    db.cypher('CREATE ...')
```

**Плюсы:** Работает точно  
**Минусы:** Все еще 2 запроса (проверка + создание)

### **Вариант B: Полная функция (проверка + создание)**

```sql
CREATE FUNCTION create_edge_safe(...)
RETURNS TABLE(success BOOL, edge_id BIGINT, message TEXT) AS $$
BEGIN
    -- Проверка
    IF EXISTS (дубликат) THEN
        RETURN QUERY SELECT FALSE, NULL, 'Duplicate';
    END IF;
    
    -- Создание через Cypher
    EXECUTE format('SELECT cypher(...)') INTO result;
    
    RETURN QUERY SELECT TRUE, result, 'Success';
END;
$$ LANGUAGE plpgsql;
```

**Плюсы:** Вся логика в БД, 1 запрос  
**Минусы:** Нужно проверить, работает ли EXECUTE с cypher()

### **Вариант C: Прямая вставка в таблицу AGE**

```sql
CREATE FUNCTION create_edge_direct(...)
RETURNS BIGINT AS $$
DECLARE
    new_edge_id BIGINT;
BEGIN
    -- Проверка дубликатов
    IF EXISTS (...) THEN
        RAISE EXCEPTION 'Duplicate';
    END IF;
    
    -- Прямая вставка в таблицу рёбер
    INSERT INTO proxy_test._ag_label_edge (id, start_id, end_id, properties)
    VALUES (nextval(...), from_id, to_id, props::agtype)
    RETURNING id INTO new_edge_id;
    
    RETURN new_edge_id;
END;
$$ LANGUAGE plpgsql;
```

**Плюсы:** Точно работает, быстро  
**Минусы:** Обход логики AGE - может сломать граф!

---

## 🧪 **ТЕСТИРОВАНИЕ (нужно провести)**

### **Тест 1: Может ли функция вызвать cypher()?**

```sql
CREATE FUNCTION test_cypher_from_function()
RETURNS TEXT AS $$
BEGIN
    PERFORM cypher('proxy_test', $$ MATCH (n) RETURN n $$);
    RETURN 'OK';
EXCEPTION WHEN OTHERS THEN
    RETURN 'ERROR: ' || SQLERRM;
END;
$$ LANGUAGE plpgsql;

SELECT test_cypher_from_function();
```

**Если "OK"** → ✅ Подход работает!  
**Если "ERROR"** → ❌ Нужен другой способ

### **Тест 2: Полная процедура create_edge_safe**

```sql
-- Создать связь
SELECT * FROM create_edge_safe(node_a_id, node_b_id, 'RELATED', '{}');
-- Ожидается: success=TRUE

-- Попытка создать дубликат
SELECT * FROM create_edge_safe(node_a_id, node_b_id, 'RELATED', '{}');
-- Ожидается: success=FALSE, message='Duplicate'

-- Попытка создать обратную связь
SELECT * FROM create_edge_safe(node_b_id, node_a_id, 'RELATED', '{}');
-- Ожидается: success=FALSE, message='Duplicate (reverse)'
```

---

## 📊 **Сравнение подходов**

| Критерий | App Validation | PostgreSQL Function |
|----------|----------------|---------------------|
| **Где логика** | 50% App + 50% БД | 100% БД |
| **Запросов из приложения** | 2 (check + create) | 1 (call function) |
| **Атомарность** | ⚠️ 2 транзакции | ✅ 1 транзакция |
| **Централизация** | ⚠️ В коде приложения | ✅ В БД |
| **Независимость от языка** | ❌ Нет | ✅ Да |
| **Простота приложения** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Сложность БД** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Работает с ArangoDB** | ✅ Да | ❌ Нет (нет функций в CE) |
| **Работает с PostgreSQL+AGE** | ✅ Да | ❓ Нужно проверить |

---

## 🎯 **КЛЮЧЕВОЙ ВОПРОС**

### **Может ли PL/pgSQL функция вызвать cypher()?**

**Сценарий 1: ✅ РАБОТАЕТ**
```sql
CREATE FUNCTION create_edge_safe(...) AS $$
BEGIN
    -- Проверка в SQL
    IF EXISTS (дубликат) THEN RAISE EXCEPTION; END IF;
    
    -- Cypher CREATE
    EXECUTE format('SELECT cypher(''graph'', $$ CREATE ... $$)');
    
    RETURN success;
END;
$$ LANGUAGE plpgsql;
```

→ ✅ **Подход ОТЛИЧНЫЙ!** Вся логика в БД, 1 запрос из приложения.

**Сценарий 2: ❌ НЕ РАБОТАЕТ**

→ ❌ Придется использовать прямую вставку в таблицу → обход AGE → проблемы

---

## 💡 **МОЕ ПРЕДЛОЖЕНИЕ**

### **Провести эксперимент:**

1. **Создать PostgreSQL функцию** с вызовом cypher()
2. **Протестировать**, работает ли
3. **Если работает** → отличное решение!
4. **Если не работает** → остаться на текущем

### **План теста:**

```sql
-- 1. Простая функция с Cypher
CREATE FUNCTION test_cypher() RETURNS TEXT AS $$
BEGIN
    PERFORM cypher('graph', 'MATCH (n) RETURN n LIMIT 1');
    RETURN 'Works!';
END;
$$ LANGUAGE plpgsql;

-- 2. Вызов
SELECT test_cypher();
```

**Если вернет "Works!"** → ✅ Идем дальше!

---

## 🚀 **Если подход работает:**

### **Преимущества для вашего проекта:**

1. ✅ **Логика валидации в PostgreSQL** (БД на стороне сервера)
2. ✅ **Приложение упрощается** - один вызов функции
3. ✅ **Атомарность** - проверка + создание в одной транзакции
4. ✅ **Централизация** - изменения только в БД
5. ✅ **Multi-client** - Python, Java, любой язык вызывает одну функцию

### **Миграция:**

```
ArangoDB (текущее):
- Валидация: Python код
- Создание: AQL через python-arango

PostgreSQL + AGE (с функциями):
- Валидация: PL/pgSQL функция
- Создание: Cypher через функцию
- Приложение: Один вызов функции

Сложность миграции: ⭐⭐⭐ (средняя)
- Переписать запросы AQL → Cypher
- Создать функции валидации в PostgreSQL
- Обновить приложение для вызова функций
```

---

## 📋 **РЕКОМЕНДУЮ ПРОВЕРИТЬ:**

### **Быстрый эксперимент (5-10 минут):**

```bash
# На удаленном сервере в fedoc-postgres уже есть Apache AGE!
# Просто нужно проверить вызов cypher() из функции
```

### **Если работает:**

✅ **Стоит рассмотреть миграцию на PostgreSQL + AGE**

**Преимущества:**
- Логика в БД (как вы и хотели)
- PostgreSQL - надежнее и популярнее
- Функции дают гибкость

### **Если НЕ работает:**

❌ Остаться на ArangoDB + валидация в приложении

**Или** использовать прямую вставку в таблицы AGE (рискованно)

---

## 🔬 **Код для проверки**

### **Создать тестовую функцию:**

```sql
CREATE OR REPLACE FUNCTION test_stored_proc_approach()
RETURNS TABLE(test_name TEXT, result TEXT) AS $$
DECLARE
    cypher_result RECORD;
BEGIN
    -- Тест 1: Может ли функция вызвать cypher()?
    BEGIN
        PERFORM cypher('proxy_test', $c$ MATCH (n) RETURN n LIMIT 1 $c$);
        RETURN QUERY SELECT 'Cypher PERFORM'::TEXT, 'OK'::TEXT;
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT 'Cypher PERFORM'::TEXT, ('ERROR: ' || SQLERRM)::TEXT;
    END;
    
    -- Тест 2: Можно ли получить результат cypher()?
    BEGIN
        SELECT * INTO cypher_result
        FROM cypher('proxy_test', $c$ MATCH (n) RETURN count(n) $c$) as (cnt agtype);
        
        RETURN QUERY SELECT 'Cypher SELECT INTO'::TEXT, 'OK: ' || cypher_result.cnt::TEXT;
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT 'Cypher SELECT INTO'::TEXT, ('ERROR: ' || SQLERRM)::TEXT;
    END;
    
    -- Тест 3: Dynamic EXECUTE с Cypher
    BEGIN
        EXECUTE 'SELECT * FROM cypher(''proxy_test'', $c$ MATCH (n) RETURN n LIMIT 1 $c$) as (n agtype)';
        RETURN QUERY SELECT 'Cypher EXECUTE'::TEXT, 'OK'::TEXT;
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT 'Cypher EXECUTE'::TEXT, ('ERROR: ' || SQLERRM)::TEXT;
    END;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- Запуск теста
SELECT * FROM test_stored_proc_approach();
```

---

## 📊 **Ожидаемые результаты**

### **Если все 3 теста "OK":**

✅ **Подход ПОЛНОСТЬЮ РАБОТАЕТ!**

→ Стоит мигрировать на PostgreSQL + AGE с функциями

### **Если хотя бы один "ERROR":**

❌ Подход имеет ограничения

→ Нужно анализировать альтернативы:
- Использовать только проверку в функции (Вариант A)
- Прямая вставка в таблицу (Вариант C)
- Остаться на текущем решении

---

## 🎯 **РЕКОМЕНДАЦИИ**

### **Шаг 1: Провести тест** (10 минут)

Apache AGE **уже установлен** на вашем PostgreSQL контейнере!

Просто нужно выполнить тестовый SQL и посмотреть результаты.

### **Шаг 2: Принять решение**

**Если функции работают:**
- ⭐ Мигрировать на PostgreSQL + AGE
- Вся логика в БД
- Приложение упрощается

**Если функции НЕ работают:**
- ⭐ Остаться на ArangoDB Community
- Валидация в приложении (работает отлично)
- Проще и быстрее

---

## 💡 **Дополнительные преимущества PostgreSQL:**

### **Если мигрируем на PostgreSQL + AGE:**

1. ✅ **Полноценные триггеры** на обычных таблицах (для документов)
2. ✅ **Хранимые процедуры** с любой логикой
3. ✅ **CHECK constraints** для валидации
4. ✅ **UNIQUE constraints** (хотя бы для прямых дубликатов)
5. ✅ **Foreign keys** между графом и таблицами
6. ✅ **Транзакции** ACID
7. ✅ **Репликация** встроенная
8. ✅ **Огромная экосистема** расширений

---

## 📋 **План действий**

### **Немедленно (10 минут):**

1. Выполнить тестовый SQL на `fedoc-postgres`
2. Проверить результаты
3. Принять решение

### **Если работает (1-2 недели):**

1. Спроектировать схему графа в AGE
2. Создать функции валидации
3. Написать скрипт миграции данных
4. Переписать запросы AQL → Cypher
5. Обновить приложение
6. Тестирование
7. Миграция

### **Если не работает (0 действий):**

Остаться на текущем решении - оно работает отлично!

---

## ✅ **ВЫВОД**

Ваше наблюдение **абсолютно верное**! 

**Суть не в триггерах, а в том, ЧТО логика на стороне БД.**

Хранимые процедуры PostgreSQL **могут решить эту задачу** элегантно:
- ✅ Вся логика в БД
- ✅ Приложение проще
- ✅ Один запрос вместо двух
- ✅ Атомарность гарантирована

**Нужно только проверить, работает ли вызов cypher() из PL/pgSQL!**

---

**Хотите, чтобы я провел этот тест прямо сейчас на вашем PostgreSQL контейнере?** 🔬


