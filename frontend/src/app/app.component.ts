import { Component } from "@angular/core";
import { NIService } from "./services/ni.service"; // Ensure correct path
import { NIDocument } from "./models/ni-document.model";
import { FormBuilder, Validators } from "@angular/forms";

@Component({
  selector: "app-root",
  templateUrl: "./app.component.html",
})
export class AppComponent {
  selectedDocumentId: number | null = null;
  docForm = this.fb.group({
    content: ["", Validators.required],
    version: [""],
  });
  loading: boolean = false;
  errorMessage: string = "";

  constructor(
    private niService: NIService,
    private fb: FormBuilder,
  ) {}

  onDocumentSelected(id: number) {
    this.selectedDocumentId = id;
  }

  addDocument() {
    if (this.docForm.invalid) return;
    this.loading = true;
    this.errorMessage = "";

    const content = this.docForm.value.content || "";
    const version = this.docForm.value.version || undefined;

    this.niService.createDocument(content, version).subscribe({
      next: () => {
        this.docForm.reset();
        this.loading = false;
        // Optionally, refresh the document list if DocumentListComponent isn't auto-updating
      },
      error: (err) => {
        console.error(err);
        this.errorMessage = "Failed to add document.";
        this.loading = false;
      },
    });
  }
}
