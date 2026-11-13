import { inject } from '@angular/core';
import { Routes } from '@angular/router';
import { BATTLE_PROTO_ENABLED } from './core/features';

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
    // 戰役 P0 手感原型：只在 dev＋feature flag 開啟時可進；否則 canMatch 失敗 → 落到下面的 not-found
    path: 'campaigns/dunkirk-1940/proto',
    canMatch: [() => inject(BATTLE_PROTO_ENABLED)],
    title: '戰役 P0 原型（示例資料）｜Sanring World Line',
    loadComponent: () => import('./battle-proto/battle-proto.page').then((m) => m.BattleProtoPage),
  },
  {
    path: '**',
    title: '找不到頁面｜Sanring World Line',
    loadComponent: () => import('./pages/not-found/not-found.page').then((m) => m.NotFoundPage),
  },
];
