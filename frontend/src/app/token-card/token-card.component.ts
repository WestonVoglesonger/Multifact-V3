import { Component, Input, Output, EventEmitter, OnInit } from "@angular/core";
import { NIToken } from "../models/ni-document.model";
import { NIService } from "../services/ni.service";

@Component({
  selector: "app-token-card",
  templateUrl: "./token-card.component.html",
})
export class TokenCardComponent implements OnInit {
  @Input() token!: NIToken;
  @Output() tokenUpdated = new EventEmitter<void>();

  editing: boolean = false;
  updatedContent: string = "";
  saving: boolean = false;
  error: string = "";

  constructor(private niService: NIService) {}

  ngOnInit() {
    this.updatedContent = this.token.content;
  }

  toggleEdit() {
    this.editing = !this.editing;
    if (!this.editing) {
      // Reset content if cancelled
      this.updatedContent = this.token.content;
    }
  }

  saveToken() {
    if (!this.token.id) return;
    this.saving = true;
    this.error = "";
    // Call an endpoint to update a single token’s content
    // Assuming an endpoint: POST /user-intervention/ni/token/update { token_id, content }
    this.niService.updateToken(this.token.id, this.updatedContent).subscribe({
      next: () => {
        this.saving = false;
        this.editing = false;
        this.tokenUpdated.emit();
      },
      error: (err) => {
        console.error(err);
        this.error = "Failed to update token.";
        this.saving = false;
      },
    });
  }
}
