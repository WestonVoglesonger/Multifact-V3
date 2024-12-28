from typing import Optional, Dict, Any
from snc.infrastructure.llm.base_llm_client import BaseLLMClient


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing."""

    def __init__(self):
        pass

    def generate_code(self, prompt: str) -> str:
        """Generate mock code based on the token type."""
        if "[Scene:" in prompt:
            return self._generate_scene_code(prompt)
        elif "[Component:" in prompt:
            return self._generate_component_code(prompt)
        elif "[Service:" in prompt:
            return self._generate_service_code(prompt)
        elif "[Interface:" in prompt:
            return self._generate_interface_code(prompt)
        elif "[Type:" in prompt:
            return self._generate_type_code(prompt)
        else:
            return "// Mock code for unknown token type"

    def _generate_scene_code(self, prompt: str) -> str:
        return """
import { Component, OnInit } from '@angular/core';
import { Store } from '@ngrx/store';

@Component({
  selector: 'app-dashboard-scene',
  template: `
    <div class="dashboard-scene">
      <app-data-grid></app-data-grid>
      <app-filter-panel></app-filter-panel>
      <app-chart></app-chart>
    </div>
  `,
  styleUrls: ['./dashboard-scene.component.scss']
})
export class DashboardSceneComponent implements OnInit {
  constructor(private store: Store) {}

  ngOnInit(): void {
    // Initialize dashboard
  }
}
"""

    def _generate_component_code(self, prompt: str) -> str:
        return """
import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'app-mock-component',
  template: '<div>Mock Component</div>',
  styleUrls: ['./mock.component.scss']
})
export class MockComponent implements OnInit {
  constructor() {}

  ngOnInit(): void {
    // Initialize component
  }
}
"""

    def _generate_service_code(self, prompt: str) -> str:
        return """
import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class MockService {
  constructor() {}

  getData(): Observable<any> {
    return of({ data: 'mock data' });
  }
}
"""

    def _generate_interface_code(self, prompt: str) -> str:
        return """
export interface MockInterface {
  id: string;
  name: string;
  value: any;
}
"""

    def _generate_type_code(self, prompt: str) -> str:
        return """
export type MockType = {
  id: string;
  type: string;
  config: {
    enabled: boolean;
    options: string[];
  };
};
"""
