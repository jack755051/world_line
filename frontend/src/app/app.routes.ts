import { Routes } from '@angular/router';

// 第一階段只有一頁（DESIGN.md：One page only `/`）；其餘路徑進 not-found（PRD §8.11）。
export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    title: 'World Line',
    loadComponent: () => import('./pages/atlas/atlas.page').then((m) => m.AtlasPage),
  },
  {
    path: '**',
    title: '找不到頁面｜World Line',
    loadComponent: () => import('./pages/not-found/not-found.page').then((m) => m.NotFoundPage),
  },
];
