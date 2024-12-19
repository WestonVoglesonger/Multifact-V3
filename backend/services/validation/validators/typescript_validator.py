# backend/services/validation/validators/typescript_validator.py
import subprocess
import tempfile
import os
import re
from typing import List
from backend.services.validation.validation_service import ValidationError
from .base import CodeValidator

class TypeScriptValidator(CodeValidator):
    def __init__(self, tool: str = "tsc"):
        self.tool = tool

    def run_syntax_type_check(self, code: str) -> List[ValidationError]:
        with tempfile.TemporaryDirectory() as tmpdir:
            ts_file_path = os.path.join(tmpdir, "artifact.ts")
            with open(ts_file_path, 'w', encoding='utf-8') as f:
                f.write(code)

            cmd = [self.tool, "--strict", "--noEmit", ts_file_path]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            except FileNotFoundError:
                raise RuntimeError(f"`{self.tool}` not found. Ensure TypeScript is installed globally.")

            return self._parse_tsc_output(result.stdout, result.stderr)

    def _parse_tsc_output(self, stdout: str, stderr: str) -> List[ValidationError]:
        errors = []
        output = stdout + "\n" + stderr
        for line in output.splitlines():
            line = line.strip()
            if "error TS" in line:
                try:
                    loc_part, msg_part = line.split(": error TS", 1)
                    if "(" in loc_part and ")" in loc_part:
                        file_part, coords = loc_part.split("(")
                        file = file_part.strip()
                        coords = coords.rstrip(")")
                        line_char_parts = coords.split(",")
                        if len(line_char_parts) == 2:
                            line_num = int(line_char_parts[0])
                            char_num = int(line_char_parts[1])
                        else:
                            line_num = 0
                            char_num = 0

                        msg_part = msg_part.strip()
                        space_index = msg_part.find(" ")
                        ts_code = "TS" + msg_part[:space_index] if space_index != -1 else msg_part
                        error_message = msg_part[space_index+1:].strip() if space_index != -1 else msg_part

                        full_message = f"{ts_code} {error_message}".strip()
                        errors.append(ValidationError(file=file, line=line_num, char=char_num, message=full_message))
                except ValueError:
                    continue
        return errors

    def run_semantic_checks(self, code: str, expectations: dict) -> List[ValidationError]:
        errors = []
        # Check for expected components
        for comp in expectations.get("expected_components", []):
            if not re.search(rf"export\s+class\s+{comp}\b", code):
                errors.append(
                    ValidationError(
                        file="semantic",
                        line=0,
                        char=0,
                        message=f"TSSEM001: Expected component class {comp} not found."
                    )
                )

        # Check for expected methods
        for method in expectations.get("expected_methods", []):
            if not re.search(rf"\b{method}\s*\(", code):
                errors.append(
                    ValidationError(
                        file="semantic",
                        line=0,
                        char=0,
                        message=f"TSSEM002: Expected method {method} not found."
                    )
                )
        return errors