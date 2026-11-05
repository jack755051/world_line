import { Routes } from '@angular/router';

// 第一階段只有一頁（DESIGN.md：One page only `/`）；其餘路徑進 not-found（PRD §8.11）。
export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    title: 'Sanring World Line',
    loadComponent: () => import('./pages/atlas/atlas.page').then((m) => m.AtlasPage),
  },
  {
    path: 'version',
    title: '版本｜Sanring World Line',
    loadComponent: () => import('./pages/version/version.page').then((m) => m.VersionPage),
  },
  {
    path: '**',
    title: '找不到頁面｜Sanring World Line',
    loadComponent: () => import('./pages/not-found/not-found.page').then((m) => m.NotFoundPage),
  },
];
