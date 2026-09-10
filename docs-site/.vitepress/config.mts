// SPDX-License-Identifier: MIT
import { defineConfig } from 'vitepress';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { notices } from '../scripts/notices.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const catalog = JSON.parse(readFileSync(root + '.local/docs-site/catalogue.json', 'utf8'));
const repository = 'https://github.com/novelKR/docs-actions';
function locale(ko: boolean) {
  const prefix = ko ? '/ko' : '';
  return {
    label: ko ? '한국어' : 'English', lang: ko ? 'ko-KR' : 'en-US', link: prefix + '/',
    description: ko ? '빌드와 권한을 각 저장소에 남기는 공통 Pages 배포' : 'Shared Pages deployment, owned by each caller',
    themeConfig: {
      nav: [
        { text: ko ? '문서' : 'Docs', link: prefix + '/guide/getting-started' },
        { text: ko ? '사이트 운영' : 'Site operations', link: prefix + '/guide/site' },
        { text: 'GitHub', link: repository },
      ],
      sidebar: [{ text: ko ? '가이드' : 'Guides', items: catalog.pages
        .filter((p: any) => p.locale === (ko ? 'ko' : 'en')).map((p: any) => ({ text: p.title, link: p.route })) }],
      outline: { level: [2, 3], label: ko ? '이 페이지에서' : 'On this page' },
      docFooter: { prev: ko ? '이전' : 'Previous', next: ko ? '다음' : 'Next' },
      sidebarMenuLabel: ko ? '메뉴' : 'Menu', returnToTopLabel: ko ? '맨 위로' : 'Return to top',
      darkModeSwitchLabel: ko ? '테마' : 'Appearance', langMenuLabel: ko ? '언어' : 'Language',
      skipToContentLabel: ko ? '본문으로 건너뛰기' : 'Skip to content',
      notFound: { title: ko ? '페이지를 찾을 수 없습니다' : 'PAGE NOT FOUND',
        quote: ko ? '메뉴 또는 검색에서 문서를 찾아보세요.' : 'Find a document using navigation or search.',
        linkText: ko ? '홈으로 돌아가기' : 'Take me home', linkLabel: ko ? '홈' : 'Home' },
    },
  };
}
export default defineConfig({
  title: 'docs-actions', base: '/docs-actions/',
  srcDir: '../.local/docs-site/source', srcExclude: ['public/**'], outDir: '../.local/docs-site/dist',
  cacheDir: '../.local/docs-site/cache', cleanUrls: true, buildConcurrency: 1,
  locales: { root: locale(false), ko: locale(true) },
  themeConfig: {
    footer: { message: '<a href="/docs-actions/LICENSE.txt">MIT</a> · <a href="/docs-actions/web-notices.txt">Web notices</a>', copyright: 'Source · ' + catalog.source_commit.slice(0, 12) },
    search: { provider: 'local', options: { locales: { ko: { translations: {
      button: { buttonText: '검색', buttonAriaLabel: '문서 검색' },
      modal: { noResultsText: '검색 결과가 없습니다', resetButtonTitle: '검색 초기화',
        footer: { selectText: '선택', navigateText: '이동', closeText: '닫기' } },
    } } } } },
  },
  vite: { resolve: { alias: [
    { find: /^vue$/, replacement: root + 'docs-site/node_modules/vue/dist/vue.runtime.esm-bundler.js' },
    { find: /^vue\/server-renderer$/, replacement: root + 'docs-site/node_modules/vue/server-renderer/index.mjs' },
  ] }, plugins: [notices(root)], build: { sourcemap: false } },
});
