<template>
  <div class="object-tree">
    <ObjectNode
      v-for="(value, key) in object"
      :key="key"
      :name="key"
      :value="value"
      :level="0"
      :parent-key="key"
    />
  </div>
</template>

<script setup>
import ObjectNode from './ObjectNode.vue'

defineProps({
  object: {
    type: Object,
    required: true
  }
})
</script>

<style scoped>
.object-tree {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.8;
  color: #e0e0e0;
}
</style>

