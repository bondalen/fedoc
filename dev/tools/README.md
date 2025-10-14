# Инструменты разработки fedoc

## 🛠️ Доступные инструменты

### view-graph.sh

Визуализация графов проектов из ArangoDB

**Использование:**
```bash
# Просмотреть весь граф
./view-graph.sh

# Просмотреть только проект FEPRO
./view-graph.sh --project fepro

# Просмотреть с кастомными параметрами
./view-graph.sh --project femsq --depth 8 --theme light
```

**Параметры:**
- `--project` - фильтр по проекту (fepro, femsq, fedoc)
- `--depth` - глубина обхода графа (default: 10)
- `--theme` - тема (dark/light, default: dark)
- `--start-node` - стартовая вершина
- `--no-browser` - не открывать браузер автоматически

**Требования:**
- Python 3.10+
- Установленные зависимости: `pip install -r ../../requirements.txt`
- Доступ к ArangoDB (localhost:8529 или через SSH туннель)

## 📚 См. также

- [Библиотека graph_viewer](../../src/lib/graph_viewer/README.md)
- [MCP-сервер](../../src/mcp_server/README.md)
