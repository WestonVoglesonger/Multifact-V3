import { Component, OnInit, Output, EventEmitter } from "@angular/core";
import { NIService } from "../services/ni.service"; // Adjust the path as necessary
import { NIDocument } from "../models/ni-document.model";

@Component({
  selector: "app-document-list",
  templateUrl: "./document-list.component.html",
})
export class DocumentListComponent implements OnInit {
  documents: NIDocument[] = [];
  @Output() documentSelected = new EventEmitter<number>();
  loading: boolean = false;
  error: string = "";

  constructor(private niService: NIService) {}

  ngOnInit() {
    this.fetchDocuments();
  }

  fetchDocuments() {
    this.loading = true;
    this.niService.listDocuments().subscribe({
      next: (docs) => {
        this.documents = docs;
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.error = "Failed to load documents.";
        this.loading = false;
      },
    });
  }

  selectDocument(id: number) {
    this.documentSelected.emit(id);
  }
}
