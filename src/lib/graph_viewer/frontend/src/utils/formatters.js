/**
 * Утилиты форматирования для Graph Viewer
 */

/**
 * Сокращает имя коллекции для компактного отображения
 * Например: "canonical_nodes" -> "can.s"
 */
export const shortenCollectionName = (collName) => {
  if (!collName || typeof collName !== 'string') return collName
  if (collName.length <= 4) return collName
  return `${collName.substring(0, 3)}.${collName.charAt(collName.length - 1)}`
}

/**
 * Форматирует ID документа для отображения
 * Преобразует "canonical_nodes/123" в "can.s/123"
 */
export const formatDocumentId = (docId) => {
  if (!docId || typeof docId !== 'string') return docId
  
  const parts = docId.split('/')
  if (parts.length !== 2) return docId
  
  const [collection, key] = parts
  const shortColl = shortenCollectionName(collection)
  return `${shortColl}/${key}`
}

/**
 * Проверяет, является ли строка ссылкой на документ ArangoDB
 * Формат: "collection_name/document_key"
 */
export const isDocumentRef = (str) => {
  if (typeof str !== 'string') return false
  return /^[a-z_]+\/[a-z0-9:_-]+$/i.test(str)
}

/**
 * Экранирует HTML для безопасного отображения
 */
export const escapeHtml = (text) => {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

/**
 * Обрезает длинный текст с добавлением многоточия
 */
export const truncateText = (text, maxLength = 100) => {
  if (!text || typeof text !== 'string') return text
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

/**
 * Определяет тип значения для JSON отображения
 */
export const getValueType = (value) => {
  if (value === null) return 'null'
  if (Array.isArray(value)) return 'array'
  return typeof value
}

/**
 * Форматирует значение для отображения в JSON дереве
 */
export const formatValue = (value, maxLength = 100) => {
  const type = getValueType(value)
  
  switch (type) {
    case 'string':
      const truncated = truncateText(value, maxLength)
      return `"${truncated}"`
    case 'number':
    case 'boolean':
      return String(value)
    case 'null':
      return 'null'
    case 'array':
      return `Array(${value.length})`
    case 'object':
      return `Object(${Object.keys(value).length})`
    default:
      return String(value)
  }
}

