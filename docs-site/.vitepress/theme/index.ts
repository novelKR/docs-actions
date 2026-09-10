// SPDX-License-Identifier: MIT
import DefaultTheme from 'vitepress/theme-without-fonts';
import { h } from 'vue';
import PageTools from './PageTools.vue';
import './tokens.css';

export default {
  extends: DefaultTheme,
  Layout: () => h(DefaultTheme.Layout, null, {
    'doc-before': () => h(PageTools),
    'home-features-after': () => h('div', { class: 'deployment-path', 'aria-label': 'Deployment stages' },
      ['01  Build', '02  Verify', '03  Artifact', '04  Pages'].map(text => h('span', text))),
  }),
};
