"""
Генерация Markdown документа из дерева обхода

MVP версия: компактный формат для AI-ассистента
"""

from datetime import datetime, timezone
from typing import Dict, List


class MarkdownGenerator:
    """Генератор Markdown документов"""
    
    def __init__(self, project_key: str):
        """
        Args:
            project_key: Ключ проекта (fedoc, fepro, femsq)
        """
        self.project_key = project_key
    
    def generate(
        self, 
        tree: Dict, 
        stats: Dict,
        start_node_key: str
    ) -> str:
        """
        Сгенерировать Markdown документ
        
        Args:
            tree: Дерево обхода от traverser
            stats: Статистика обхода
            start_node_key: Ключ стартового узла
            
        Returns:
            Markdown документ
        """
        output = []
        
        # Заголовок
        output.append(f"# Обход графа: проект {self.project_key} от узла {start_node_key}\n")
        
        # Метаданные
        output.append("**Метаданные**:")
        output.append(f"- Проект: {self.project_key}")
        output.append(f"- Стартовый узел: {start_node_key} ({tree.get('name', '')})")
        output.append(f"- Дата генерации: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
        output.append(f"- Метод: sys-001 (обход вниз по исходящим рёбрам)")
        output.append("\n---\n")
        
        # Дерево зависимостей
        output.append("## Дерево зависимостей\n")
        output.extend(self._generate_node(tree, level=3))
        
        # Статистика
        output.append("\n---\n")
        output.append("## Статистика обхода\n")
        output.append("**Граф**:")
        output.append(f"- Уникальных узлов: {stats['unique_nodes']}")
        output.append(f"- Максимальная глубина: {stats['max_depth']} уровней")
        
        if stats['multi_parent_nodes']:
            output.append("\n**Узлы с множественными родителями**:")
            for key, count in sorted(stats['multi_parent_nodes'].items()):
                output.append(f"- {key} → {count} включений")
        
        return '\n'.join(output)
    
    def _generate_node(self, node: Dict, level: int) -> List[str]:
        """
        Рекурсивная генерация Markdown для узла
        
        Args:
            node: Узел дерева
            level: Уровень вложенности (количество #)
            
        Returns:
            Список строк Markdown
        """
        lines = []
        
        # Проверка на ссылку
        if 'ref' in node:
            header = '#' * level
            lines.append(f"{header} {node['key']} — {node['name']}")
            lines.append(f"→ **См. раздел {node['ref']}** (полное описание выше)\n")
            return lines
        
        # Полное описание узла
        node_key = node.get('key', '')
        node_name = node.get('name', '')
        node_type = node.get('type', 'unknown')
        edge_type = node.get('edge_type')
        props = node.get('properties', {})
        
        # Заголовок
        header = '#' * level
        lines.append(f"{header} {node_key} — {node_name}")
        
        # Тип связи (если не корень)
        if edge_type:
            lines.append(f"**Связь**: {edge_type}")
        
        # Тип узла
        lines.append(f"**Тип**: {node_type}")
        
        # Описание
        if 'description' in props:
            lines.append(f"**Описание**: {props['description']}")
        
        # Дополнительные свойства
        for key, value in props.items():
            if key == 'description':
                continue
            
            # Форматирование значений
            if isinstance(value, list):
                value_str = ', '.join(str(v) for v in value)
            else:
                value_str = str(value)
            
            # Человекочитаемые названия
            key_names = {
                'port': 'Порт',
                'stack': 'Стек',
                'version': 'Версия',
                'status': 'Статус',
                'slug': 'Slug'
            }
            key_display = key_names.get(key, key.title())
            
            lines.append(f"**{key_display}**: {value_str}")
        
        lines.append("")  # Пустая строка после узла
        
        # Дочерние узлы
        children = node.get('children', {})
        if children:
            for child_path in sorted(children.keys()):
                child = children[child_path]
                lines.extend(self._generate_node(child, level + 1))
        
        return lines

