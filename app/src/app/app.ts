import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ButtonDirective } from './components/ui/button';

@Component({
  imports: [RouterOutlet, ButtonDirective],
  selector: 'app-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {
  protected readonly title = 'World Line';
}
