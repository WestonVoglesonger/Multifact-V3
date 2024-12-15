import subprocess
import tempfile
import os
from typing import List
from sqlalchemy.orm import Session
from backend.entities.compiled_multifact import CompiledMultifact

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
        artifact = session.query(CompiledMultifact).filter(CompiledMultifact.id == artifact_id).first()
        if not artifact:
            raise ValueError(f"Artifact with id {artifact_id} not found.")

        code = artifact.code
        if not code.strip():
            # Let tsc handle empty code scenario
            pass

        with tempfile.TemporaryDirectory() as tmpdir:
            ts_file_path = os.path.join(tmpdir, f"artifact_{artifact_id}.ts")
            with open(ts_file_path, 'w', encoding='utf-8') as f:
                f.write(code)

            cmd = ["tsc", "--strict", "--noEmit", ts_file_path]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            except FileNotFoundError:
                raise RuntimeError("`tsc` not found. Ensure TypeScript is installed globally.")

            errors = ValidationService._parse_tsc_output(result.stdout, result.stderr)
            success = (len(errors) == 0)

            artifact.valid = success
            session.commit()

            return ValidationResult(success=success, errors=errors)

    @staticmethod
    def _parse_tsc_output(stdout: str, stderr: str) -> List[ValidationError]:
        errors = []
        output = stdout + "\n" + stderr
        for line in output.splitlines():
            line = line.strip()
            # Example: artifact_1.ts(1,5): error TS2322: Type 'string' is not assignable to type 'number'.
            # We can look for "):" and "error TS"
            if "error TS" in line:
                # Split at first occurence of ': error TS' to separate location from message
                loc_part, msg_part = line.split(": error TS", 1)
                # loc_part example: "artifact_1.ts(1,5)"
                # msg_part example: "2322: Type 'string' is not assignable to type 'number'."

                # Extract file, line, char
                # loc_part might look like: artifact_1.ts(1,5)
                # Separate file from (line,char)
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

                    # msg_part might be like "2322: Type 'string'..."
                    # Extract the code and the message after the code
                    msg_part = msg_part.strip()
                    space_index = msg_part.find(" ")
                    ts_code = "TS" + msg_part[:space_index] if space_index != -1 else msg_part
                    error_message = msg_part[space_index+1:].strip() if space_index != -1 else msg_part

                    full_message = f"{ts_code} {error_message}".strip()
                    errors.append(ValidationError(file=file, line=line_num, char=char_num, message=full_message))

        return errors