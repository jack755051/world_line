import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MapComponent } from './map/map';
import { TimeScrubberComponent } from './time-scrubber/time-scrubber';
import { RegimeFocusPanelComponent } from './regime-focus-panel/regime-focus-panel';
import { LineageSequenceComponent } from './lineage-sequence/lineage-sequence';
import { NamingViewpointSelectorComponent } from './naming-viewpoint-selector/naming-viewpoint-selector';

@Component({
  imports: [
    RouterOutlet,
    MapComponent,
    TimeScrubberComponent,
    RegimeFocusPanelComponent,
    LineageSequenceComponent,
    NamingViewpointSelectorComponent,
  ],
  selector: 'app-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {
  protected readonly title = 'World Line';
}
