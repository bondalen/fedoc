# Упрощённая система типов вершин

**Дата**: 2025-11-05  
**Статус**: Предложение (упрощение)  
**Приоритет**: Высокий

---

## Предложение

Использовать строковые ключи типа `"g:v:a:c"` (граф:вершина:сегмент:тип) для определения типа узла и хранения стилей визуализации в JSON файле.

---

## Формат ключей

### Структура: `g:v:{segment}:{type}`

**Примеры**:
- `g:v:a:c` — граф:вершина:архитектура:концепт
- `g:v:a:t` — граф:вершина:архитектура:технология
- `g:v:a:v` — граф:вершина:архитектура:версия
- `g:v:c:m` — граф:вершина:код:модуль
- `g:v:c:comp` — граф:вершина:код:компонент
- `g:v:c:class` — граф:вершина:код:класс
- `g:v:c:nested` — граф:вершина:код:вложенный_класс
- `g:v:f:d` — граф:вершина:файловая_система:директория
- `g:v:f:file` — граф:вершина:файловая_система:файл
- `g:v:o` — граф:вершина:прочие

### Сегменты (segment)
- `a` — architecture (архитектура)
- `c` — code_structure (структура кода)
- `f` — filesystem (файловая система)
- `o` — other (прочие)

---

## Структура JSON конфигурации

**Файл**: `config/vertex_styles.json`

```json
{
  "g:v:a:c": {
    "dark": {
      "color": "#1976D2",
      "border": "#0D47A1",
      "shape": "box",
      "size": {
        "width": 120,
        "height": 36,
        "borderRadius": 6,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#ffffff",
        "size": 12,
        "strokeWidth": 2,
        "strokeColor": "#1976D2"
      }
    },
    "light": {
      "color": "#E3F2FD",
      "border": "#90CAF9",
      "shape": "box",
      "size": {
        "width": 120,
        "height": 36,
        "borderRadius": 6,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#000000",
        "size": 12,
        "strokeWidth": 2,
        "strokeColor": "#E3F2FD"
      }
    }
  },
  "g:v:a:t": {
    "dark": {
      "color": "#388E3C",
      "border": "#1B5E20",
      "shape": "circle",
      "size": {
        "size": 36,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#ffffff",
        "size": 12,
        "strokeWidth": 2,
        "strokeColor": "#388E3C"
      }
    },
    "light": {
      "color": "#E8F5E9",
      "border": "#81C784",
      "shape": "circle",
      "size": {
        "size": 36,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#000000",
        "size": 12,
        "strokeWidth": 2,
        "strokeColor": "#E8F5E9"
      }
    }
  },
  "g:v:a:v": {
    "dark": {
      "color": "#7B1FA2",
      "border": "#4A148C",
      "shape": "diamond",
      "size": {
        "size": 24,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#ffffff",
        "size": 12,
        "strokeWidth": 2,
        "strokeColor": "#7B1FA2"
      }
    },
    "light": {
      "color": "#F3E5F5",
      "border": "#BA68C8",
      "shape": "diamond",
      "size": {
        "size": 24,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#000000",
        "size": 12,
        "strokeWidth": 2,
        "strokeColor": "#F3E5F5"
      }
    }
  },
  "g:v:c:m": {
    "dark": {
      "color": "#F57C00",
      "border": "#E65100",
      "shape": "box",
      "size": {
        "width": 140,
        "height": 40,
        "borderRadius": 4,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#ffffff",
        "size": 11,
        "strokeWidth": 1,
        "strokeColor": "#F57C00"
      }
    },
    "light": {
      "color": "#FFF3E0",
      "border": "#FFB74D",
      "shape": "box",
      "size": {
        "width": 140,
        "height": 40,
        "borderRadius": 4,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#000000",
        "size": 11,
        "strokeWidth": 1,
        "strokeColor": "#FFF3E0"
      }
    }
  },
  "g:v:c:comp": {
    "dark": {
      "color": "#5C6BC0",
      "border": "#283593",
      "shape": "box",
      "size": {
        "width": 130,
        "height": 38,
        "borderRadius": 5,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#ffffff",
        "size": 11,
        "strokeWidth": 1,
        "strokeColor": "#5C6BC0"
      }
    },
    "light": {
      "color": "#E8EAF6",
      "border": "#7986CB",
      "shape": "box",
      "size": {
        "width": 130,
        "height": 38,
        "borderRadius": 5,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#000000",
        "size": 11,
        "strokeWidth": 1,
        "strokeColor": "#E8EAF6"
      }
    }
  },
  "g:v:c:class": {
    "dark": {
      "color": "#00897B",
      "border": "#004D40",
      "shape": "box",
      "size": {
        "width": 120,
        "height": 35,
        "borderRadius": 3,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#ffffff",
        "size": 10,
        "strokeWidth": 1,
        "strokeColor": "#00897B"
      }
    },
    "light": {
      "color": "#B2DFDB",
      "border": "#4DB6AC",
      "shape": "box",
      "size": {
        "width": 120,
        "height": 35,
        "borderRadius": 3,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#000000",
        "size": 10,
        "strokeWidth": 1,
        "strokeColor": "#B2DFDB"
      }
    }
  },
  "g:v:c:nested": {
    "dark": {
      "color": "#00695C",
      "border": "#003D33",
      "shape": "box",
      "size": {
        "width": 110,
        "height": 32,
        "borderRadius": 2,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#ffffff",
        "size": 9,
        "strokeWidth": 1,
        "strokeColor": "#00695C"
      }
    },
    "light": {
      "color": "#80CBC4",
      "border": "#26A69A",
      "shape": "box",
      "size": {
        "width": 110,
        "height": 32,
        "borderRadius": 2,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#000000",
        "size": 9,
        "strokeWidth": 1,
        "strokeColor": "#80CBC4"
      }
    }
  },
  "g:v:f:d": {
    "dark": {
      "color": "#757575",
      "border": "#424242",
      "shape": "box",
      "size": {
        "width": 150,
        "height": 30,
        "borderRadius": 0,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#ffffff",
        "size": 10,
        "strokeWidth": 0,
        "strokeColor": "transparent"
      }
    },
    "light": {
      "color": "#E0E0E0",
      "border": "#9E9E9E",
      "shape": "box",
      "size": {
        "width": 150,
        "height": 30,
        "borderRadius": 0,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#000000",
        "size": 10,
        "strokeWidth": 0,
        "strokeColor": "transparent"
      }
    }
  },
  "g:v:f:file": {
    "dark": {
      "color": "#616161",
      "border": "#212121",
      "shape": "box",
      "size": {
        "width": 140,
        "height": 28,
        "borderRadius": 0,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#ffffff",
        "size": 9,
        "strokeWidth": 0,
        "strokeColor": "transparent"
      }
    },
    "light": {
      "color": "#F5F5F5",
      "border": "#BDBDBD",
      "shape": "box",
      "size": {
        "width": 140,
        "height": 28,
        "borderRadius": 0,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#000000",
        "size": 9,
        "strokeWidth": 0,
        "strokeColor": "transparent"
      }
    }
  },
  "g:v:o": {
    "dark": {
      "color": "#2d3748",
      "border": "#4a5568",
      "shape": "box",
      "size": {
        "width": 120,
        "height": 36,
        "borderRadius": 6,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#ffffff",
        "size": 12,
        "strokeWidth": 2,
        "strokeColor": "#2d3748"
      }
    },
    "light": {
      "color": "#ffffff",
      "border": "#e0e0e0",
      "shape": "box",
      "size": {
        "width": 120,
        "height": 36,
        "borderRadius": 6,
        "borderWidth": 1,
        "margin": 10
      },
      "font": {
        "color": "#000000",
        "size": 12,
        "strokeWidth": 2,
        "strokeColor": "#ffffff"
      }
    }
  }
}
```

---

## Реализация

### Бакенд: Определение типа по ключу узла

```python
# utils/vertex_type.py
def get_vertex_type_key(node_key: str, node_type: str) -> str:
    """
    Получить ключ типа для визуализации на основе ключа узла и типа
    
    Args:
        node_key: Ключ узла (например, "c:project", "t:python")
        node_type: Тип узла (например, "concept", "technology")
    
    Returns:
        Ключ типа для визуализации (например, "g:v:a:c")
    """
    # Маппинг типа узла на сегмент и подтип
    type_mapping = {
        'concept': ('a', 'c'),
        'technology': ('a', 't'),
        'version': ('a', 'v'),
        'module': ('c', 'm'),
        'component': ('c', 'comp'),
        'class': ('c', 'class'),
        'nested-class': ('c', 'nested'),
        'directory': ('f', 'd'),
        'file': ('f', 'file'),
        'other': ('o', None)
    }
    
    segment, subtype = type_mapping.get(node_type, ('o', None))
    
    if subtype:
        return f"g:v:{segment}:{subtype}"
    else:
        return "g:v:o"
```

### Фронтенд: Применение стилей

```javascript
// utils/visualization.js
import vertexStyles from '@/config/vertex_styles.json'

export function getVertexTypeKey(nodeKey, nodeType) {
  // Маппинг типа узла на ключ визуализации
  const typeMapping = {
    'concept': 'g:v:a:c',
    'technology': 'g:v:a:t',
    'version': 'g:v:a:v',
    'module': 'g:v:c:m',
    'component': 'g:v:c:comp',
    'class': 'g:v:c:class',
    'nested-class': 'g:v:c:nested',
    'directory': 'g:v:f:d',
    'file': 'g:v:f:file',
    'other': 'g:v:o'
  }
  
  return typeMapping[nodeType] || 'g:v:o'
}

export function applyNodeVisualization(node, theme = 'light') {
  const nodeType = node.node_type || inferNodeType(node.key)
  const typeKey = getVertexTypeKey(node.key, nodeType)
  const style = vertexStyles[typeKey]?.[theme] || vertexStyles['g:v:o'][theme]
  
  return {
    ...node,
    ...style,
    // Применить размеры в зависимости от формы
    ...(style.shape === 'box' && style.size?.width && style.size?.height ? {
      width: style.size.width,
      height: style.size.height,
      borderRadius: style.size.borderRadius
    } : {}),
    ...(style.shape === 'circle' && style.size?.size ? {
      size: style.size.size
    } : {}),
    ...(style.shape === 'diamond' && style.size?.size ? {
      size: style.size.size
    } : {})
  }
}
```

---

## Преимущества упрощённого подхода

✅ **Простота**: Нет сложной иерархии классов  
✅ **Единый источник стилей**: Всё в одном JSON файле  
✅ **Легко добавлять типы**: Просто добавить запись в JSON  
✅ **Нет зависимости от классов**: Работает с любыми узлами  
✅ **Производительность**: Прямой доступ к стилям по ключу  
✅ **Простое тестирование**: Легко проверить визуализацию  

---

## Что НЕ решается упрощённым подходом

### 1. Валидация префиксов ключей

**Текущая система**:
```python
def validate_node_key(node_key: str, node_type: str) -> bool:
    if node_type == 'concept' and not node_key.startswith('c:'):
        return False
    # ...
```

**Упрощённая система**:
- Нужно парсить строку `g:v:a:c` и проверять соответствие
- Или хранить маппинг `node_type → prefix` отдельно

**Решение**: Добавить маппинг в конфиг:
```json
{
  "validation": {
    "concept": {"prefix": "c:", "type_key": "g:v:a:c"},
    "technology": {"prefix": "t:", "type_key": "g:v:a:t"},
    ...
  }
}
```

### 2. Бизнес-логика для разных типов

**Текущая система**:
- Классы могут иметь специфичные методы
- Например, `TechnologyVertex.validate_version()`

**Упрощённая система**:
- Нет классов, значит нет специфичных методов
- Вся логика должна быть в общих функциях

**Решение**: Если нужна специфичная логика, использовать паттерн Strategy:
```python
# utils/vertex_handlers.py
class ConceptHandler:
    def validate(self, node_key, properties):
        # Специфичная валидация для концептов
        pass

class TechnologyHandler:
    def validate(self, node_key, properties):
        # Специфичная валидация для технологий
        if 'version' in properties:
            validate_version_format(properties['version'])
        pass

# Реестр обработчиков
HANDLERS = {
    'concept': ConceptHandler(),
    'technology': TechnologyHandler(),
    # ...
}
```

### 3. Типобезопасность

**Текущая система**:
- Классы обеспечивают типобезопасность
- IDE может подсказывать методы

**Упрощённая система**:
- Нет классов, нет типобезопасности
- Всё через строки и словари

**Решение**: Если типобезопасность критична, можно использовать TypedDict (Python) или TypeScript (JavaScript).

### 4. Расширяемость через наследование

**Текущая система**:
- Новые типы могут наследовать от базовых классов
- Переиспользование кода

**Упрощённая система**:
- Нет наследования
- Дублирование логики

**Решение**: Использовать композицию вместо наследования:
```python
# Базовые функции
def validate_base(node_key, properties):
    # Общая валидация
    pass

# Специфичные функции
def validate_concept(node_key, properties):
    validate_base(node_key, properties)
    # Дополнительная валидация
    pass
```

### 5. Автоматическая генерация кода

**Текущая система**:
- Можно генерировать классы из метаданных в графе

**Упрощённая система**:
- Нет классов для генерации
- Генерация не нужна

**Решение**: Если генерация не нужна, это не проблема.

---

## Сравнение подходов

| Задача | Сложная система | Упрощённая система |
|--------|----------------|-------------------|
| Визуализация | ✅ Классы + метаданные | ✅ JSON конфиг |
| Валидация префиксов | ✅ В классах | ⚠️ Нужен маппинг |
| Бизнес-логика | ✅ Методы классов | ⚠️ Отдельные обработчики |
| Типобезопасность | ✅ Классы | ❌ Нет |
| Расширяемость | ✅ Наследование | ⚠️ Композиция |
| Простота | ❌ Сложно | ✅ Просто |
| Производительность | ⚠️ Создание объектов | ✅ Прямой доступ |
| Добавление типов | ⚠️ Класс + регистрация | ✅ JSON запись |

---

## Рекомендация

**Использовать упрощённый подход**, если:
- ✅ Основная задача — визуализация
- ✅ Нет сложной бизнес-логики для разных типов
- ✅ Типобезопасность не критична
- ✅ Нужна простота и скорость разработки

**Добавить обработчики для специфичной логики**, если:
- ⚠️ Нужна валидация префиксов
- ⚠️ Есть специфичная бизнес-логика для типов

---

## Итоговая структура

```
config/
  └── vertex_styles.json          # Стили визуализации
  └── vertex_validation.json      # Маппинг типов на префиксы (опционально)

utils/
  └── vertex_type.py              # Определение типа по ключу
  └── vertex_handlers.py          # Обработчики для специфичной логики (опционально)

frontend/
  └── utils/
      └── visualization.js        # Применение стилей из JSON
```

---

**Дата создания**: 2025-11-05  
**Автор**: Александр  
**Версия**: 1.0

