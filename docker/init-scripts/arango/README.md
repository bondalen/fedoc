# Скрипты инициализации ArangoDB

Поместите сюда JavaScript файлы для автоматического выполнения при первом запуске ArangoDB.

## Примеры

### Создание базы данных
```javascript
// 01-create-database.js
db._createDatabase("fedoc");
```

### Создание коллекций
```javascript
// 02-create-collections.js
db._useDatabase("fedoc");
db._create("meta_patterns");
db._create("structural_blocks");
db._create("system_rules");
```

Файлы выполняются в алфавитном порядке.

