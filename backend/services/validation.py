import subprocess
import tempfile
import os
import re
from typing import List
from sqlalchemy.orm import Session
from backend.entities.compiled_multifact import CompiledMultifact
from backend.entities.ni_token import NIToken
from backend.entities.ni_document import NIDocument
from sqlalchemy import select

class ValidationError:
    def __init__(self, file: str, line: int, char: int, message: str):
        self.file = file
        self.line = line
        self.char = char
        self.message = message

    def __repr__(self):
        return f"ValidationError(file={self.file}, line={self.line}, char={self.char}, message={self.message})"


class ValidationResult:
    def __init__(self, success: bool, errors: List[ValidationError]):
        self.success = success
        self.errors = errors

    def __repr__(self):
        return f"ValidationResult(success={self.success}, errors={self.errors})"


class ValidationService:
    @staticmethod
    def validate_artifact(artifact_id: int, session: Session) -> ValidationResult:
        artifact = session.scalars(
            select(CompiledMultifact).where(CompiledMultifact.id == artifact_id)
        ).first()
        if not artifact:
            raise ValueError(f"Artifact with id {artifact_id} not found.")

        code = artifact.code
        if not code.strip():
            # Let tsc handle empty code scenario
            pass

        # Run TypeScript validation
        errors = ValidationService._run_tsc_check(artifact_id, code)

        # If code is syntactically correct, run semantic checks
        # (You may do it unconditionally even if tsc fails, but let's assume only if tsc passes)
        if len(errors) == 0:
            sem_errors = ValidationService._semantic_checks(artifact, session)
            errors.extend(sem_errors)

        success = (len(errors) == 0)
        artifact.valid = success
        session.commit()

        return ValidationResult(success=success, errors=errors)

    @staticmethod
    def _run_tsc_check(artifact_id: int, code: str) -> List[ValidationError]:
        with tempfile.TemporaryDirectory() as tmpdir:
            ts_file_path = os.path.join(tmpdir, f"artifact_{artifact_id}.ts")
            with open(ts_file_path, 'w', encoding='utf-8') as f:
                f.write(code)

            cmd = ["tsc", "--strict", "--noEmit", ts_file_path]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            except FileNotFoundError:
                raise RuntimeError("`tsc` not found. Ensure TypeScript is installed globally.")

            return ValidationService._parse_tsc_output(result.stdout, result.stderr)

    @staticmethod
    def _parse_tsc_output(stdout: str, stderr: str) -> List[ValidationError]:
        errors = []
        output = stdout + "\n" + stderr
        for line in output.splitlines():
            line = line.strip()
            if "error TS" in line:
                loc_part, msg_part = line.split(": error TS", 1)
                if "(" in loc_part and ")" in loc_part:
                    file_part, coords = loc_part.split("(")
                    file = file_part.strip()
                    coords = coords.rstrip(")")
                    line_char_parts = coords.split(",")
                    if len(line_char_parts) == 2:
                        try:
                            line_num = int(line_char_parts[0])
                            char_num = int(line_char_parts[1])
                        except ValueError:
                            line_num = 0
                            char_num = 0
                    else:
                        line_num = 0
                        char_num = 0

                    msg_part = msg_part.strip()
                    space_index = msg_part.find(" ")
                    ts_code = "TS" + msg_part[:space_index] if space_index != -1 else msg_part
                    error_message = msg_part[space_index+1:].strip() if space_index != -1 else msg_part

                    full_message = f"{ts_code} {error_message}".strip()
                    errors.append(ValidationError(file=file, line=line_num, char=char_num, message=full_message))

        return errors

    @staticmethod
    def _semantic_checks(artifact: CompiledMultifact, session: Session) -> List[ValidationError]:
        errors = []
        # Retrieve NI content
        token = session.get(NIToken, artifact.ni_token_id)
        ni_doc = session.get(NIDocument, token.ni_document_id)
        ni_content = ni_doc.content

        # Extract expected components and methods from NI (simple heuristic)
        # Let's say we look for lines like "Create a component named XXX"
        component_pattern = re.compile(r"component\s+named\s+(\w+)", re.IGNORECASE)
        method_pattern = re.compile(r"method\s+(\w+)", re.IGNORECASE)

        expected_components = component_pattern.findall(ni_content)
        expected_methods = method_pattern.findall(ni_content)

        code = artifact.code
        # Check each expected component as a class:
        for comp in expected_components:
            # Look for `export class {comp}`
            if not re.search(rf"export\s+class\s+{comp}\b", code):
                errors.append(ValidationError(
                    file="semantic",
                    line=0,
                    char=0,
                    message=f"TSSEM001: Expected component class {comp} not found."
                ))

        # If we have a single component scenario, we can assume methods must be in that component
        # For each expected method:
        for method in expected_methods:
            # Just look for `{method}(` in code
            if not re.search(rf"\b{method}\s*\(", code):
                errors.append(ValidationError(
                    file="semantic",
                    line=0,
                    char=0,
                    message=f"TSSEM002: Expected method {method} not found."
                ))

        # Add more semantic checks as needed:
        # For instance, if NI says "display user.name in an <h2>", look for `{{\s*user\.name\s*}}` inside <h2> tags

        return errors