import { Component } from '@angular/core';
import { AppShell } from './layout/app-shell/app-shell';

@Component({
  imports: [AppShell],
  selector: 'wl-root',
  styleUrl: './app.css',
  templateUrl: './app.html',
})
export class App {}
