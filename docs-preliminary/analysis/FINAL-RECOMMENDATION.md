# Финальная рекомендация: Валидация рёбер графа

**Дата:** 17 октября 2025  
**Вопрос:** Где должна находиться логика валидации - в приложении или в БД?  
**Ответ:** ✅ Решение найдено

---

## 💡 **Ключевой инсайт**

**Александр прав:** Суть не в триггерах как таковых, а в том, что **логика валидации выполняется на стороне БД**, а не в приложении.

---

## 📊 **Сравнение подходов**

### **Подход 1: Валидация в приложении** (текущий с ArangoDB)

```python
# Python приложение
def create_edge(from_id, to_id):
    # Проверка (запрос к БД)
    if edge_validator.check_uniqueness(from_id, to_id):
        # Создание (запрос к БД)
        return db.create_edge(from_id, to_id)
    else:
        raise DuplicateError()
```

**Характеристики:**
- Логика: 50% приложение + 50% БД
- Запросов: 2 (проверка + создание)
- Атомарность: ⚠️ Две отдельные операции

### **Подход 2: Хранимая процедура PostgreSQL** (предложение)

```python
# Python приложение
def create_edge(from_id, to_id):
    # Один вызов функции БД
    return db.call_function('create_edge_safe', from_id, to_id)
```

```sql
-- PostgreSQL функция
CREATE FUNCTION create_edge_safe(from_id, to_id) AS $$
BEGIN
    -- Проверка дубликатов (SQL)
    IF EXISTS (дубликат) THEN
        RAISE EXCEPTION 'Duplicate';
    END IF;
    
    -- Создание через Cypher (?)
    EXECUTE 'SELECT cypher(...CREATE...)';
    
    RETURN success;
END;
$$ LANGUAGE plpgsql;
```

**Характеристики:**
- Логика: 100% в БД
- Запросов: 1 (вызов функции)
- Атомарность: ✅ Одна транзакция

---

## 🔍 **Технический анализ**

### **Вопрос: Может ли PL/pgSQL функция вызвать cypher()?**

**Проверено:**
- ❌ `PERFORM cypher(...)` - функция не найдена в контексте
- ⏳ `EXECUTE 'SELECT cypher(...)'` - требует дополнительного тестирования

**Альтернатива:** Прямая вставка в таблицу AGE:
```sql
INSERT INTO graph._ag_label_edge (id, start_id, end_id, properties)
VALUES (nextval(...), from_id, to_id, props);
```

**Риски:**
- ⚠️ Обход внутренней логики AGE
- ⚠️ Может сломать индексы и метаданные
- ⚠️ Несовместимость с будущими версиями

---

## 🎯 **Практическая рекомендация**

### **Вариант A: PostgreSQL + AGE + Функции** ⭐ **ЕСЛИ ТЕСТ УСПЕШЕН**

**Если** EXECUTE с cypher() работает:

✅ **Мигрировать на PostgreSQL + Apache AGE**

**План:**
1. Создать функции валидации в PostgreSQL
2. Мигрировать данные из ArangoDB
3. Переписать AQL → Cypher
4. Упростить приложение (один вызов функции)

**Преимущества:**
- ✅ Вся логика в БД
- ✅ PostgreSQL - надежнее, популярнее
- ✅ Функции + constraint + триггеры на таблицах
- ✅ Огромная экосистема

**Время миграции:** ~2-3 недели

### **Вариант B: ArangoDB + Валидация в приложении** ⭐ **ТЕКУЩЕЕ**

**Если** EXECUTE с cypher() НЕ работает:

✅ **Оставить ArangoDB Community**

**Преимущества:**
- ✅ Уже работает на 100%
- ✅ Специализирована для графов
- ✅ AQL удобнее для multi-model
- ✅ Нет затрат на миграцию

---

## 📋 **Что нужно сделать СЕЙЧАС:**

### **Провести финальный тест:**

```sql
-- Тест вызова Cypher из функции PostgreSQL
CREATE FUNCTION final_test() AS $$
DECLARE
    result RECORD;
BEGIN
    -- Попытка вызвать Cypher через EXECUTE
    EXECUTE 'SELECT * FROM ag_catalog.cypher(''proxy_test'', $c$ MATCH (n) RETURN count(n) $c$) as (cnt agtype)'
    INTO result;
    
    RETURN 'OK: ' || result.cnt;
EXCEPTION WHEN OTHERS THEN
    RETURN 'FAIL: ' || SQLERRM;
END;
$$ LANGUAGE plpgsql;

SELECT final_test();
```

**Если результат "OK:"** → PostgreSQL + AGE отличное решение!  
**Если "FAIL:"** → ArangoDB лучше

---

## ✅ **РЕЗЮМЕ**

### **Ваше наблюдение верное:**

✅ PostgreSQL **позволяет** создавать функции (в отличие от ArangoDB CE)  
✅ Функции **могут** централизовать логику в БД  
✅ Это **упрощает** приложение (1 вызов вместо 2)  
✅ Дает **атомарность** (проверка + создание в одной транзакции)

### **Нужно проверить:**

❓ Может ли функция PostgreSQL **вызвать cypher()** для создания рёбер в графе AGE

**Если ДА** → PostgreSQL + AGE становится **лучшим** решением  
**Если НЕТ** → ArangoDB остается **оптимальным**

---

**Apache AGE уже установлен на вашем сервере - можно провести тест когда удобно!** 🔬
