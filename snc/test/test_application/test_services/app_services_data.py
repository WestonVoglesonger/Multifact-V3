import uuid
import pytest
import hashlib
import random
from datetime import datetime
from sqlalchemy.orm import Session
from snc.domain.models import DomainDocument, DomainToken, DomainCompiledMultifact
from snc.infrastructure.entities.ni_document import NIDocument
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def insert_fake_data(session: Session) -> None:
    """
    Inserts demo data for testing the application services:
    - DependencyGraphService
    - DocumentUpdater
    - SelfRepairService
    - TokenDiffService
    - TokenCompiler
    - UserInterventionService
    """

    # --- 1) Document for DependencyGraphService (S -> C -> F) ---
    dep_doc = NIDocument(
        content="[Scene:S]\nREF:C\n[Component:C]\nREF:F\n[Function:F]\n", version="v1"
    )
    session.add(dep_doc)
    session.commit()

    # Create tokens: S -> depends on C, C -> depends on F
    s_token = NIToken(
        ni_document_id=dep_doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="scene",
        token_name="S",
        scene_name="S",
        component_name=None,
        order=0,
        content="S content\nREF:C",
        hash=compute_hash("S content\nREF:C"),
    )
    session.add(s_token)
    session.commit()

    c_token = NIToken(
        ni_document_id=dep_doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="component",
        token_name="C",
        scene_name=None,
        component_name="C",
        order=1,
        content="C content\nREF:F",
        hash=compute_hash("C content\nREF:F"),
    )
    session.add(c_token)
    session.commit()

    f_token = NIToken(
        ni_document_id=dep_doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="function",
        token_name="F",
        scene_name=None,
        component_name=None,
        order=2,
        content="F content",
        hash=compute_hash("F content"),
    )
    session.add(f_token)
    session.commit()

    # Link dependencies
    s_token.dependencies.append(c_token)
    c_token.dependencies.append(f_token)
    session.commit()

    # --- 2) Document for DocumentUpdater and TokenDiffService ---
    # We'll create a doc with two tokens. We'll want to remove one and add a new one in tests.
    updater_doc = NIDocument(
        content="[Scene:Updater]\nThis is updater scene.\n[Component:UpdaterComp]\nUpdaterComp content.",
        version="v1",
    )
    session.add(updater_doc)
    session.commit()

    updater_scene_token = NIToken(
        ni_document_id=updater_doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="scene",
        token_name="Updater",
        scene_name="Updater",
        component_name=None,
        order=0,
        content="Updater scene content.",
        hash=compute_hash("Updater scene content."),
    )
    updater_comp_token = NIToken(
        ni_document_id=updater_doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="component",
        token_name="UpdaterComp",
        scene_name=None,
        component_name="UpdaterComp",
        order=1,
        content="UpdaterComp content.",
        hash=compute_hash("UpdaterComp content."),
    )
    session.add_all([updater_scene_token, updater_comp_token])
    session.commit()

    # --- 3) Document for SelfRepairService (invalid artifacts) ---
    repair_doc = NIDocument(
        content="[Scene:RepairDoc]\nScene needing repair.", version="v1"
    )
    session.add(repair_doc)
    session.commit()

    repair_token = NIToken(
        ni_document_id=repair_doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="scene",
        token_name="RepairDoc",
        scene_name="RepairDoc",
        component_name=None,
        order=0,
        content="Repair doc content",
        hash=compute_hash("Repair doc content"),
    )
    session.add(repair_token)
    session.commit()

    # Insert an artifact that is invalid
    invalid_artifact = CompiledMultifact(
        ni_token_id=repair_token.id,
        language="typescript",
        framework="angular",
        code="Some code with errors",
        valid=False,  # invalid
        cache_hit=False,
        token_hash=repair_token.hash,
    )
    session.add(invalid_artifact)
    session.commit()

    # Another artifact that is valid and cached
    valid_artifact = CompiledMultifact(
        ni_token_id=repair_token.id,
        language="typescript",
        framework="angular",
        code="""
        export class MyAlreadyValidComponent {
        greeting: string = "Hello";
        constructor() { console.log(this.greeting); }
        }
        """.strip(),
        valid=True,
        cache_hit=True,  # This one is cached
        token_hash=repair_token.hash,
    )
    session.add(valid_artifact)
    session.commit()

    # --- 4) Document for TokenCompiler with both valid/invalid tokens ---
    compiler_doc = NIDocument(
        content="[Scene:Compiler]\nCompiler doc content.\n[Function:ShouldCompile]\nShould compile content.\n[Function:WillFail]\nWill fail content.",
        version="v1",
    )
    session.add(compiler_doc)
    session.commit()

    compiler_scene_token = NIToken(
        ni_document_id=compiler_doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="scene",
        token_name="Compiler",
        scene_name="Compiler",
        component_name=None,
        order=0,
        content="Compiler doc content.",
        hash=compute_hash("Compiler doc content."),
    )
    should_compile_token = NIToken(
        ni_document_id=compiler_doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="function",
        token_name="ShouldCompile",
        scene_name=None,
        component_name=None,
        order=1,
        content="Should compile content.",
        hash=compute_hash("Should compile content."),
    )
    will_fail_token = NIToken(
        ni_document_id=compiler_doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="function",
        token_name="WillFail",
        scene_name=None,
        component_name=None,
        order=2,
        content="Will fail content.",
        hash=compute_hash("Will fail content."),
    )
    session.add_all([compiler_scene_token, should_compile_token, will_fail_token])
    session.commit()

    # --- 5) Document for UserInterventionService ---
    # Reuse some of the above or create a new doc that can be updated
    intervention_doc = NIDocument(
        content="[Scene:Intervention]\nIntervention doc content.\n", version="v1"
    )
    session.add(intervention_doc)
    session.commit()

    intervention_token = NIToken(
        ni_document_id=intervention_doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="scene",
        token_name="Intervention",
        scene_name="Intervention",
        component_name=None,
        order=0,
        content="Intervention content",
        hash=compute_hash("Intervention content"),
    )
    session.add(intervention_token)
    session.commit()

    # Final commit
    session.commit()


@pytest.fixture(scope="session", autouse=True)
def fake_data_fixture(session: Session):
    insert_fake_data(session)
    session.commit()
    yield
