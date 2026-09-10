<!-- SPDX-License-Identifier: MIT -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useData, useRoute, withBase } from 'vitepress';
const { frontmatter } = useData();
const route = useRoute();
const ko = computed(() => frontmatter.value.docLocale === 'ko');
const status = ref('');
const busy = ref(false);
watch(() => route.path, () => { status.value = ''; });
async function copyPage() {
  const current = route.path;
  busy.value = true;
  try {
    const response = await fetch(withBase(frontmatter.value.copyPath));
    if (!response.ok) throw new Error('Markdown is unavailable');
    const text = await response.text();
    await navigator.clipboard.writeText(text);
    if (route.path === current) status.value = ko.value ? '원문을 복사했습니다.' : 'Original Markdown copied.';
  } catch {
    if (route.path === current) status.value = ko.value ? '복사하지 못했습니다. 브라우저 권한을 확인하세요.' : 'Copy failed. Check browser permissions.';
  } finally { busy.value = false; }
}
</script>
<template>
  <div v-if="frontmatter.copyPath" class="page-tools">
    <button type="button" :disabled="busy" @click="copyPage">{{ ko ? '페이지 원문 복사' : 'Copy page Markdown' }}</button>
    <a :href="withBase(frontmatter.copyPath)">{{ ko ? 'Markdown 원문' : 'Markdown source' }}</a>
    <a :href="'https://github.com/novelKR/docs-actions/commit/' + frontmatter.sourceCommit">{{ frontmatter.sourceCommit?.slice(0, 7) }}</a>
    <a :href="withBase('/web-notices.txt')">{{ ko ? '웹 고지' : 'Web notices' }}</a>
    <span role="status" aria-live="polite">{{ status }}</span>
  </div>
</template>
