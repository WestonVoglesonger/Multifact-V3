import os
import re
import json
import subprocess
import tempfile
from typing import List, Optional, Dict

from backend.application.interfaces.ivalidation_service import ValidationError
from backend.application.interfaces.ivalidation_service import IValidationService, ValidationResult
from backend.domain.models import DomainCompiledMultifact
from backend.infrastructure.entities.compiled_multifact import CompiledMultifact
from backend.infrastructure.entities.ni_document import NIDocument
from backend.infrastructure.entities.ni_token import NIToken
from sqlalchemy.orm import Session
from sqlalchemy import select


class TypeScriptValidator:
    """
    Enhanced TypeScript validator for Angular code. Provides:
      - More complete stubs for @angular/core, @angular/forms, etc.
      - Filtering of common module-resolution errors (TS2307) or missing exports (TS2305).
      - Basic references for OnInit, FormGroup.valid, .value, etc.
    """

    def __init__(self, tool: str = "tsc"):
        self.tool = tool

        # Angular "stubs" to satisfy imports:
        # Add any additional items your code references (e.g. 'OnChanges', 'NgModule', etc.).
        self.angular_stubs: Dict[str, str] = {
            "@angular/core": """
                export interface OnInit {
                  ngOnInit(): void;
                }
                export const Component: any = (arg?: any) => {};
                export const Injectable: any = (arg?: any) => {};
                export const Input: any = (arg?: any) => {};
                export const Output: any = (arg?: any) => {};
                export const EventEmitter: any = class {};
                export class ChangeDetectorRef {
                  markForCheck() {}
                }
            """,
            "@angular/forms": """
                export class FormControl {
                    constructor(value?: any, validator?: any) {}
                    value: any;
                }
                export class FormGroup {
                    valid: boolean = true;
                    value: any = {};
                    constructor(controls: any) {
                        // naive placeholder
                    }
                    get(path: string): FormControl | null {
                        return new FormControl();
                    }
                }
                export class FormBuilder {
                    group(config: any): FormGroup {
                        return new FormGroup(config);
                    }
                }
                export const Validators: any = {
                    required: () => null,
                    email: () => null,
                    minLength: (n: number) => null,
                    maxLength: (n: number) => null
                };
            """,
            "@angular/router": """
                export class Router {
                  navigate(commands: any[], extras?: any) {}
                }
            """,
        }

    def run_syntax_type_check(self, code: str, strict_mode: bool = False) -> List[ValidationError]:
        """
        1) Create a temporary folder with node_modules stubs.
        2) Write the artifact code to 'artifact.ts'.
        3) Create a tsconfig.json referencing the file.
        4) Run `tsc` and parse output. Return a list of ValidationError if any.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_angular_stubs(tmpdir)

            # Write artifact code
            ts_file_path = os.path.join(tmpdir, "artifact.ts")
            with open(ts_file_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Write a minimal tsconfig
            tsconfig = self._make_tsconfig(ts_file_path, strict_mode)
            tsconfig_path = os.path.join(tmpdir, "tsconfig.json")
            with open(tsconfig_path, "w", encoding="utf-8") as f:
                json.dump(tsconfig, f, indent=2)

            # Run tsc
            cmd = [self.tool, "-p", tsconfig_path]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                return self._parse_tsc_output(result.stdout, result.stderr, filter_module_errors=not strict_mode)
            except FileNotFoundError:
                raise RuntimeError(f"`{self.tool}` not found. Ensure TypeScript is installed or in PATH.")

    def run_semantic_checks(self, code: str, expectations: Dict[str, List[str]]) -> List[ValidationError]:
        """
        Optional "semantic" checks. 
        e.g. verifying you have a @Component(...) if you expect a component named 'XYZ', etc.
        """
        errors = []

        # Check for expected components if your doc says "component named ..."
        for c in expectations.get("expected_components", []):
            # naive approach: look for "@Component" in code
            if not re.search(r"@Component\s*\(\{", code):
                errors.append(
                    ValidationError(
                        file="semantic",
                        line=0,
                        char=0,
                        message=f"TSSEM001: Expected a @Component for component '{c}', not found."
                    )
                )

        # Check for expected methods
        for m in expectations.get("expected_methods", []):
            if not re.search(rf"\b{m}\s*\(", code):
                errors.append(
                    ValidationError(
                        file="semantic",
                        line=0,
                        char=0,
                        message=f"TSSEM002: Expected method '{m}' not found in code."
                    )
                )

        return errors

    def _create_angular_stubs(self, tmpdir: str) -> None:
        """
        Build a mini 'node_modules' structure inside tmpdir for references 
        like import { Component } from '@angular/core'.
        """
        for pkg, stub_content in self.angular_stubs.items():
            parts = pkg.split("/")
            mod_dir = os.path.join(tmpdir, "node_modules", *parts)
            os.makedirs(mod_dir, exist_ok=True)
            index_dts_path = os.path.join(mod_dir, "index.d.ts")
            with open(index_dts_path, "w", encoding="utf-8") as f:
                f.write(stub_content)

    def _make_tsconfig(self, main_ts: str, strict: bool) -> dict:
        """
        Basic TSConfig. Adjust if you want noImplicitAny, skipLibCheck, etc.
        """
        return {
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "moduleResolution": "node",
                "baseUrl": ".",
                "experimentalDecorators": True,
                "emitDecoratorMetadata": True,
                "esModuleInterop": True,
                "noEmit": True,
                "skipLibCheck": True,
                "strict": strict,
            },
            "files": [main_ts],
        }

    def _parse_tsc_output(
        self,
        stdout: str,
        stderr: str,
        filter_module_errors: bool = True
    ) -> List[ValidationError]:
        """Parse tsc output lines. Filter out some common harmless errors if desired."""
        all_lines = (stdout + "\n" + stderr).splitlines()
        errors: List[ValidationError] = []

        for line in all_lines:
            line = line.strip()
            if not line or "warning" in line.lower():
                continue

            # Example: file.ts(10,5): error TS2307: Cannot find module '@angular/core'
            if "error TS" in line:
                # Optionally skip certain error codes
                if filter_module_errors:
                    # TS2307 => cannot find module
                    # TS2305 => "Module ... has no exported member 'OnInit'"
                    # TS2339 => property not found on type
                    if any(ec in line for ec in ("TS2307", "TS2305", "TS2339")):
                        continue

                # Attempt parse
                match = re.match(r"(.+?)\((\d+),(\d+)\):\s*error\s+(TS\d+):\s*(.+)", line)
                if match:
                    file_part, line_num, char_num, ts_code, message = match.groups()
                    errors.append(
                        ValidationError(
                            file=file_part.strip(),
                            line=int(line_num),
                            char=int(char_num),
                            message=f"{ts_code}: {message.strip()}"
                        )
                    )
        return errors
