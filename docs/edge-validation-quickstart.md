# Быстрый старт: Валидация рёбер графа

🎯 **Цель:** Предотвращение дублирующих связей в обоих направлениях (A→B и B→A)

---

## ⚡ Быстрый тест

```bash
# 1. Проверить уникальность
curl -X POST http://localhost:8899/api/edges/check \
  -H "Content-Type: application/json" \
  -d '{"_from":"canonical_nodes/c:backend","_to":"canonical_nodes/t:java@21"}'

# 2. Создать связь
curl -X POST http://localhost:8899/api/edges \
  -H "Content-Type: application/json" \
  -d '{
    "_from":"canonical_nodes/c:backend",
    "_to":"canonical_nodes/t:java@21",
    "relationType":"uses",
    "projects":["fepro"]
  }'

# 3. Попытка создать обратную связь (будет отклонена!)
curl -X POST http://localhost:8899/api/edges \
  -H "Content-Type: application/json" \
  -d '{
    "_from":"canonical_nodes/t:java@21",
    "_to":"canonical_nodes/c:backend",
    "relationType":"uses",
    "projects":["fepro"]
  }'
# Ответ: "Связь уже существует (обратная связь: ...)"
```

---

## 📋 API Endpoints

| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | `/api/edges` | Создать ребро |
| `POST` | `/api/edges/check` | Проверить уникальность |
| `DELETE` | `/api/edges/<id>` | Удалить ребро |

---

## 🎯 Статус

✅ Проверка в обоих направлениях  
✅ Создание с валидацией  
✅ **Обновление с валидацией** (исправлено)  
✅ Удаление

---

Полная документация: `docs/edge-validation-guide.md`

