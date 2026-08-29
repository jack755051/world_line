import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    // 打後端 API 用——目前只有 GET，走相對路徑 `/api/v1/...`，由 nginx.conf 的
    // `location /api/` proxy 轉發到 backend container，開發/生產環境用同一套相對路徑，
    // 不需要另外維護一份環境變數切換 base URL（見 app/nginx.conf）。
    provideHttpClient(),
  ]
};
