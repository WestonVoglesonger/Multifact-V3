import { Component, OnChanges, Input } from "@angular/core";
import { NIService } from "../services/ni.service";
import { NIDocumentDetail } from "../models/ni-document.model";

@Component({
  selector: "app-document-detail",
  templateUrl: "./document-detail.component.html",
})
export class DocumentDetailComponent implements OnChanges {
  @Input() niId: number | null = null;
  detail: NIDocumentDetail | null = null;
  editableContent: string = "";
  loading: boolean = false;
  error: string = "";
  recompiling: boolean = false; // To show loader during recompilation

  constructor(private niService: NIService) {}

  ngOnChanges() {
    if (this.niId) {
      this.loadDetail();
    } else {
      this.detail = null;
    }
  }

  loadDetail() {
    this.loading = true;
    this.error = "";
    this.niService.getDocumentDetail(this.niId!).subscribe({
      next: (d) => {
        this.detail = d;
        this.editableContent = d.content;
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.error = "Failed to load document details.";
        this.loading = false;
      },
    });
  }

  updateDocument() {
    if (!this.niId) return;
    this.loading = true;
    this.error = "";
    this.niService.updateDocument(this.niId, this.editableContent).subscribe({
      next: () => {
        this.loadDetail();
      },
      error: (err) => {
        console.error(err);
        this.error = "Failed to update document.";
        this.loading = false;
      },
    });
  }

  recompileDocument() {
    if (!this.niId) return;
    this.recompiling = true;
    this.error = "";
    this.niService.recompileDocument(this.niId).subscribe({
      next: () => {
        // After recompile, reload detail
        this.loadDetail();
        this.recompiling = false;
      },
      error: (err: any) => {
        console.error(err);
        this.error = "Failed to recompile document.";
        this.recompiling = false;
      },
    });
  }
}
