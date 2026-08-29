import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MapComponent } from './map/map';
import { TimeScrubberComponent } from './time-scrubber/time-scrubber';

@Component({
  imports: [RouterOutlet, MapComponent, TimeScrubberComponent],
  selector: 'app-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {
  protected readonly title = 'World Line';
}
