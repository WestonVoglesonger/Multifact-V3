export interface NIDocument {
  id: number;
  content: string;
  version: string | null;
  created_at: string;
  updated_at: string;
}

export interface NIToken {
  id: number;
  ni_document_id: number;
  scene_name?: string;
  component_name?: string;
  order: number;
  content: string;
  hash: string;
}

export interface CompiledArtifact {
  id: number;
  ni_token_id: number;
  language: string;
  framework: string;
  code: string;
  created_at: string;
  valid: boolean;
  cache_hit: boolean;
}

// The detail endpoint might return a combined structure with tokens and artifacts:
export interface NIDocumentDetail extends NIDocument {
  tokens: NIToken[];
  artifacts: CompiledArtifact[]; // or map ni_token_id -> artifact for convenience
}
