<template>
  <div class="object-node">
    <!-- Кнопка сворачивания для объектов/массивов -->
    <span 
      v-if="isExpandable" 
      class="collapse-btn"
      @click="toggleCollapse"
    >
      {{ isCollapsed ? '▶' : '▼' }}
    </span>
    
    <!-- Имя ключа -->
    <span class="json-key">{{ displayKey }}:</span>
    
    <!-- Примитивные значения -->
    <span v-if="isPrimitive && !hasGuessedDocRef" :class="valueClass">
      {{ displayValue }}
    </span>
    
    <!-- Угаданная ссылка на документ (для строк в контексте) -->
    <template v-else-if="hasGuessedDocRef">
      <!-- Узел графа: ссылка + кнопка "Показать" -->
      <template v-if="isGraphNode">
        <span 
          class="doc-link" 
          :title="guessedDocRef"
          @click="onFocusNode"
        >
          {{ formattedDocId }}
        </span>
        <button 
          class="show-on-graph-btn" 
          @click="onFocusNode"
          title="Показать на графе"
        >
          📍 Показать
        </button>
      </template>
      
      <!-- Связанный документ: кнопка разворачивания -->
      <template v-else-if="isExpandableDoc">
        <span 
          class="collapse-btn doc-expand-btn"
          @click="toggleExpandDoc"
        >
          {{ isDocExpanded ? '▼' : '▶' }}
        </span>
        <span 
          class="doc-link-readonly" 
          :title="guessedDocRef"
        >
          {{ formattedDocId }}
        </span>
        
        <!-- Разворачиваемое содержимое документа -->
        <div v-if="isDocExpanded" class="expanded-doc nested">
          <div v-if="isLoadingDoc" class="loading">⏳ Загрузка...</div>
          <div v-else-if="docLoadError" class="error">{{ docLoadError }}</div>
          <ObjectNode
            v-else-if="expandedDoc"
            v-for="(val, key) in expandedDoc"
            :key="key"
            :name="key"
            :value="val"
            :level="level + 1"
            :parent-key="key"
          />
        </div>
      </template>
    </template>
    
    <!-- Ссылка на документ -->
    <template v-else-if="isDocRef">
      <!-- Узел графа: ссылка + кнопка "Показать" -->
      <template v-if="isGraphNode">
        <span 
          class="doc-link" 
          :title="value"
          @click="onFocusNode"
        >
          {{ formattedDocId }}
        </span>
        <button 
          class="show-on-graph-btn" 
          @click="onFocusNode"
          title="Показать на графе"
        >
          📍 Показать
        </button>
      </template>
      
      <!-- Связанный документ: кнопка разворачивания -->
      <template v-else-if="isExpandableDoc">
        <span 
          class="collapse-btn doc-expand-btn"
          @click="toggleExpandDoc"
        >
          {{ isDocExpanded ? '▼' : '▶' }}
        </span>
        <span 
          class="doc-link-readonly" 
          :title="value"
        >
          {{ formattedDocId }}
        </span>
        
        <!-- Разворачиваемое содержимое документа -->
        <div v-if="isDocExpanded" class="expanded-doc nested">
          <div v-if="isLoadingDoc" class="loading">⏳ Загрузка...</div>
          <div v-else-if="docLoadError" class="error">{{ docLoadError }}</div>
          <ObjectNode
            v-else-if="expandedDoc"
            v-for="(val, key) in expandedDoc"
            :key="key"
            :name="key"
            :value="val"
            :level="level + 1"
            :parent-key="key"
          />
        </div>
      </template>
    </template>
    
    <!-- Кнопка "Показать полный текст" для длинных строк -->
    <button
      v-if="isTruncatedString"
      @click="onShowFullText"
      class="show-full-text-btn"
      title="Показать полный текст"
    >
      📄
    </button>
    
    <!-- Вложенный объект/массив -->
    <div v-if="isExpandable && !isCollapsed" class="nested">
      <div v-if="isArray" class="array-items">
        <ObjectNode
          v-for="(item, index) in value"
          :key="index"
          :name="index"
          :value="item"
          :level="level + 1"
          :parent-key="parentKey"
        />
      </div>
      <div v-else class="object-items">
        <ObjectNode
          v-for="(val, key) in value"
          :key="key"
          :name="key"
          :value="val"
          :level="level + 1"
          :parent-key="key"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useGraphStore } from '@/stores/graph'
import { 
  formatDocumentId, 
  isDocumentRef, 
  truncateText 
} from '@/utils/formatters'

const props = defineProps({
  name: {
    type: [String, Number],
    required: true
  },
  value: {
    required: true
  },
  level: {
    type: Number,
    default: 0
  },
  parentKey: {
    type: String,
    default: ''
  }
})

const store = useGraphStore()
const isCollapsed = ref(true)
const isDocExpanded = ref(false)
const expandedDoc = ref(null)
const isLoadingDoc = ref(false)
const docLoadError = ref(null)

// ========== FUNCTIONS ==========

/**
 * Угадать коллекцию по контексту
 */
const guessCollectionRef = (name, parentKey) => {
  const knownCollections = {
    'projects': 'projects',
    'rules': 'rules', 
    'templates': 'templates',
    'tasks': 'tasks'
  }
  
  const parentLower = (parentKey || '').toLowerCase()
  for (const [hint, collection] of Object.entries(knownCollections)) {
    if (parentLower.includes(hint)) {
      return `${collection}/${name}`
    }
  }
  
  return null
}

// ========== COMPUTED ==========

const displayKey = computed(() => {
  return typeof props.name === 'number' ? `[${props.name}]` : props.name
})

const isPrimitive = computed(() => {
  const type = typeof props.value
  return ['string', 'number', 'boolean'].includes(type) || props.value === null
})

const isExpandable = computed(() => {
  return typeof props.value === 'object' && props.value !== null
})

const isArray = computed(() => {
  return Array.isArray(props.value)
})

const isDocRef = computed(() => {
  return typeof props.value === 'string' && isDocumentRef(props.value)
})

const guessedDocRef = computed(() => {
  if (typeof props.value !== 'string') return null
  if (isDocumentRef(props.value)) return props.value
  
  // Не угадывать ссылки для элементов массивов проектов - это может привести к путанице
  if (props.parentKey === 'projects') {
    return null
  }
  
  // Угадать коллекцию по контексту
  return guessCollectionRef(props.value, props.parentKey)
})

const isGraphNode = computed(() => {
  const docRef = isDocRef.value ? props.value : guessedDocRef.value
  return docRef && docRef.includes('canonical_nodes/')
})

const hasGuessedDocRef = computed(() => {
  return guessedDocRef.value !== null
})

const isExpandableDoc = computed(() => {
  const docRef = isDocRef.value ? props.value : guessedDocRef.value
  return docRef && !docRef.includes('canonical_nodes/')
})

const formattedDocId = computed(() => {
  const docRef = isDocRef.value ? props.value : guessedDocRef.value
  if (!docRef) return props.value
  return formatDocumentId(docRef)
})

const valueClass = computed(() => {
  const type = typeof props.value
  if (type === 'string') return 'json-string'
  if (type === 'number') return 'json-number'
  if (type === 'boolean') return 'json-boolean'
  if (props.value === null) return 'json-null'
  return ''
})

const isTruncatedString = computed(() => {
  return typeof props.value === 'string' && 
         !isDocRef.value && 
         props.value.length > 100
})

const displayValue = computed(() => {
  if (props.value === null) return 'null'
  if (props.value === undefined) return 'undefined'
  
  const type = typeof props.value
  
  if (type === 'string') {
    const truncated = truncateText(props.value, 100)
    return `"${truncated}"`
  }
  
  if (type === 'number' || type === 'boolean') {
    return String(props.value)
  }
  
  return String(props.value)
})

// ========== METHODS ==========

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const toggleExpandDoc = async () => {
  if (!isDocExpanded.value) {
    // Загружаем документ при первом раскрытии
    if (!expandedDoc.value) {
      await loadDocument()
    }
    isDocExpanded.value = true
  } else {
    isDocExpanded.value = false
  }
}

const loadDocument = async () => {
  isLoadingDoc.value = true
  docLoadError.value = null
  
  try {
    const docRef = guessedDocRef.value || props.value
    const doc = await store.loadDocumentDetails(docRef)
    expandedDoc.value = doc
  } catch (err) {
    console.error('Ошибка загрузки документа:', err)
    docLoadError.value = `Ошибка: ${err.message}`
  } finally {
    isLoadingDoc.value = false
  }
}

const onFocusNode = () => {
  const docRef = guessedDocRef.value || props.value
  store.focusNode(docRef)
}

const onShowFullText = () => {
  console.log('onShowFullText called', { name: props.name, value: props.value, isTruncated: isTruncatedString.value })
  const text = `${props.name}:\n\n${props.value}`
  
  // Если панель уже открыта с этим же текстом - закрываем
  if (store.showFullText && store.fullText === text) {
    store.closeFullText()
  } else {
    // Иначе открываем с новым текстом
    store.openFullText(text)
  }
}
</script>

<style scoped>
.object-node {
  margin: 4px 0;
  line-height: 1.8;
}

.collapse-btn {
  cursor: pointer;
  color: #888;
  margin-right: 5px;
  user-select: none;
  display: inline-block;
  width: 14px;
  font-size: 10px;
  transition: color 0.2s;
}

.collapse-btn:hover {
  color: #64B5F6;
}

.doc-expand-btn {
  color: #64B5F6;
}

.json-key {
  color: #ffffff;
  font-weight: bold;
  margin-right: 6px;
}

.json-string {
  color: #90EE90;
  word-break: break-word;
}

.json-number {
  color: #87CEEB;
}

.json-boolean {
  color: #FFA500;
}

.json-null {
  color: #999;
  font-style: italic;
}

.doc-link {
  color: #64B5F6;
  cursor: pointer;
  text-decoration: underline;
  transition: color 0.2s;
}

.doc-link:hover {
  color: #42A5F5;
}

.doc-link-readonly {
  color: #64B5F6;
  text-decoration: none;
}

.show-on-graph-btn,
.show-full-text-btn {
  background: #1976D2;
  color: #fff;
  border: none;
  padding: 2px 8px;
  margin-left: 8px;
  border-radius: 3px;
  cursor: pointer;
  font-size: 10px;
  font-family: Arial, sans-serif;
  transition: all 0.2s;
}

.show-full-text-btn {
  padding: 2px 6px;
}

.show-on-graph-btn:hover,
.show-full-text-btn:hover {
  background: #1565C0;
  transform: translateY(-1px);
}

.nested {
  margin-left: 20px;
  border-left: 1px solid #333;
  padding-left: 10px;
  margin-top: 4px;
}

.expanded-doc {
  margin-top: 8px;
}

.loading {
  color: #64B5F6;
  font-style: italic;
  font-size: 11px;
}

.error {
  color: #ff6b6b;
  font-size: 11px;
}

.array-items,
.object-items {
  /* Контейнер для дочерних элементов */
}
</style>

