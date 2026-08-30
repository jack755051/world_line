import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MapComponent } from './map/map';
import { TimeScrubberComponent } from './time-scrubber/time-scrubber';
import { RegimeFocusPanelComponent } from './regime-focus-panel/regime-focus-panel';

@Component({
  imports: [RouterOutlet, MapComponent, TimeScrubberComponent, RegimeFocusPanelComponent],
  selector: 'app-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {
  protected readonly title = 'World Line';
}
