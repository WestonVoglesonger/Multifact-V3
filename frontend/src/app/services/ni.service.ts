import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";
import { NIDocument, NIDocumentDetail } from "../models/ni-document.model";

@Injectable({ providedIn: "root" })
export class NIService {
  private baseURL = "http://localhost:1461"; // Ensure this matches your backend port

  constructor(private http: HttpClient) {}

  listDocuments(): Observable<NIDocument[]> {
    return this.http.get<NIDocument[]>(`${this.baseURL}/ni/list`);
  }

  getDocumentDetail(niId: number): Observable<NIDocumentDetail> {
    return this.http.get<NIDocumentDetail>(`${this.baseURL}/ni/${niId}`);
  }

  createDocument(content: string, version?: string): Observable<NIDocument> {
    const payload = { content, version: version || null };
    return this.http.post<NIDocument>(`${this.baseURL}/ni/upload`, payload);
  }

  updateDocument(
    niId: number,
    content: string,
  ): Observable<{ status: string }> {
    return this.http.post<{ status: string }>(`${this.baseURL}/ni/update`, {
      ni_id: niId,
      content,
    });
  }

  recompileDocument(niId: number): Observable<{ status: string }> {
    return this.http.post<{ status: string }>(
      `${this.baseURL}/ni/${niId}/recompile`,
      {},
    );
  }

  updateToken(
    tokenId: number,
    content: string,
  ): Observable<{ status: string }> {
    // Endpoint to update a single token's content and recompile it
    return this.http.post<{ status: string }>(
      `${this.baseURL}/user-intervention/ni/token/update`,
      { token_id: tokenId, content },
    );
  }
}
