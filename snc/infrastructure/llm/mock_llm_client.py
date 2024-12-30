from typing import Dict, Any
from snc.application.interfaces.illm_client import ILLMClient
from snc.domain.models import Model


class MockLLMClient(ILLMClient):
    """Mock LLM client for testing."""

    def __init__(self, model: Model):
        super().__init__(model)

    def generate_code(
        self,
        token_content: str,
        additional_requirements: str = "",
        code_style: str = "",
    ) -> str:
        """Generate mock code based on the token type."""
        if "[Scene:" in token_content:
            return self._generate_scene_code(token_content)
        elif "[Component:" in token_content:
            return self._generate_component_code(token_content)
        elif "[Service:" in token_content:
            return self._generate_service_code(token_content)
        elif "[Interface:" in token_content:
            return self._generate_interface_code(token_content)
        elif "[Type:" in token_content:
            return self._generate_type_code(token_content)
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

    def parse_document(self, ni_content: str) -> Dict[str, Any]:
        return {"scenes": []}

    def fix_code(self, original_code: str, error_summary: str) -> str:
        return original_code

    def _generic_chat_call(
        self,
        system_message: Dict[str, Any],
        user_message: Dict[str, Any],
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str:
        return ""
