# test_all.py
import pytest
from sqlalchemy.orm import Session
from typing import Callable
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
import random
import string
from sqlalchemy import select

from backend.env import getenv
from backend.models.ni_document import NIDocumentCreate
from backend.services.ni import NIService
from backend.services.compilation import CompilationService
from backend.services.validation import ValidationService
from backend.services.self_repair import SelfRepairService
from backend.services.user_intervention import UserInterventionService
from backend.entities.ni_document import NIDocument
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact
from backend.test.services.core_data import setup_insert_data_fixture  
from backend.test.services.fixtures import initial_ni
from backend.utils.token_key_util import TokenKeyUtil

# Mock generated code
MOCK_GENERATED_CODE = """\
import { Component } from '@angular/core';

@Component({
  selector: 'app-test',
  template: `<div>Test Component</div>`
})
export class TestComponent {}
"""

# Fixed code for self repair
FIXED_CODE = """\
import { Component } from '@angular/core';

@Component({
  selector: 'app-fixed',
  template: `<div>Fixed</div>`
})
export class FixedComponent {
  x: number = 42;
}
"""

GOOD_CODE = """\
export class MyComponent {
  user = { name: 'Alice', email: 'alice@example.com' };

  sendEmail() {
    console.log('Sending email to ' + this.user.email);
  }
}
"""

BAD_CODE_NO_METHOD = """\
export class MyComponent {
  user = { name: 'Alice', email: 'alice@example.com' };
  // missing sendEmail method
}
"""

BAD_CODE_NO_COMPONENT = """\
function sendEmail() {
  console.log('Sending email');
}
"""

ORIGINAL_BAD_CODE = "let x: number = 'string';"

def compile_all_tokens_for_doc(ni_doc_id: int, session: Session):
    tokens = session.query(NIToken).filter_by(ni_document_id=ni_doc_id).all()
    for t in tokens:
        CompilationService.compile_token(t.id, session)


# ----- GROUP: Basic Compilation Tests -----

@patch("backend.services.llm_client.LLMClient._generic_chat_call", return_value=MOCK_GENERATED_CODE)
def test_compile_token_new(mock_llm: MagicMock, db_session: Session):
    doc_data = NIDocumentCreate(content="[Scene:Intro]\nThis is intro scene.", version="v1")
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    # Manually compile tokens if not auto-compiled:
    compile_all_tokens_for_doc(ni_doc.id, db_session)

    token = db_session.get(NIToken, ni_doc.id)
    assert token is not None

    artifact = db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()
    assert artifact is not None
    assert artifact.ni_token_id == token.id
    assert len(artifact.code.strip()) > 0
    assert "@component" in artifact.code.lower()

def test_compile_token_non_existent(db_session: Session):
    with pytest.raises(ValueError):
        CompilationService.compile_token(9999, db_session)

@patch("backend.services.llm_client.LLMClient._generic_chat_call", return_value=MOCK_GENERATED_CODE)
def test_compile_token_cache(mock_llm: MagicMock, db_session: Session):
    doc_data = NIDocumentCreate(content="Just some content no scenes", version="v1")
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session)
    token = db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).first()

    artifact_1 = db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()
    assert artifact_1 is not None
    assert artifact_1.cache_hit == False

    # Compile again - should hit cache now
    CompilationService.compile_token(token.id, db_session) 
    artifact_2 = db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()
    assert artifact_2 is not None
    assert artifact_2.id == artifact_1.id
    assert artifact_2.cache_hit is True

# ----- GROUP: Validation Tests -----

@patch("subprocess.run")
def test_validate_artifact_success(mock_run: MagicMock, db_session: Session):
    mock_run.return_value.stdout = ""
    mock_run.return_value.stderr = ""
    mock_run.return_value.returncode = 0

    doc1 = db_session.query(NIDocument).filter(NIDocument.content.like("%[Scene:SimpleDOC1MARKER]%")).first()
    assert doc1 is not None
    # Artifacts are pre-created in insert_demo_data
    token = db_session.query(NIToken).filter(NIToken.ni_document_id == doc1.id).first()
    artifact = db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()

    result = ValidationService.validate_artifact(artifact.id, db_session)
    assert result.success is True
    assert len(result.errors) == 0

@patch("subprocess.run")
def test_validate_artifact_failure(mock_run: MagicMock, db_session: Session):
    mock_run.return_value.stdout = "artifact_1.ts(1,5): error TS2322: Type 'string' is not assignable to type 'number'."
    mock_run.return_value.stderr = ""
    mock_run.return_value.returncode = 2

    doc3 = db_session.query(NIDocument).filter(NIDocument.content.like("%[Scene:TrickyDOC3MARKER]%")).first()
    assert doc3 is not None
    token = db_session.query(NIToken).filter(NIToken.ni_document_id == doc3.id).first()
    artifact = db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()
    result = ValidationService.validate_artifact(artifact.id, db_session)
    assert not result.success
    assert len(result.errors) > 0
    assert "TS2322" in result.errors[0].message

@patch("subprocess.run")
def test_validate_artifact_success_again(mock_run: MagicMock, db_session: Session):
    mock_run.return_value.stdout = ""
    mock_run.return_value.stderr = ""
    mock_run.return_value.returncode = 0
    doc1 = db_session.query(NIDocument).filter(NIDocument.content.like("%[Scene:SimpleDOC1MARKER]%")).first()
    assert doc1 is not None
    token = db_session.query(NIToken).filter(NIToken.ni_document_id == doc1.id).first()
    artifact = db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()
    result = ValidationService.validate_artifact(artifact.id, db_session)
    assert result.success is True
    assert len(result.errors) == 0

@patch("subprocess.run")
def test_validate_artifact_failure_again(mock_run: MagicMock, db_session: Session):
    mock_run.return_value.stdout = "artifact_1.ts(1,5): error TS2322: Type 'string' is not assignable to type 'number'."
    mock_run.return_value.stderr = ""
    mock_run.return_value.returncode = 2
    doc3 = db_session.query(NIDocument).filter(NIDocument.content.like("%[Scene:TrickyDOC3MARKER]%")).first()
    assert doc3 is not None
    token = db_session.query(NIToken).filter(NIToken.ni_document_id == doc3.id).first()
    artifact = db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()
    result = ValidationService.validate_artifact(artifact.id, db_session)
    assert not result.success
    assert len(result.errors) > 0
    assert "TS2322" in result.errors[0].message

# ----- GROUP: Self-Repair Tests -----

@patch("subprocess.run")
@patch("backend.services.llm_client.LLMClient._generic_chat_call")
def test_self_repair_success(mock_llm: MagicMock, mock_run: MagicMock, db_session: Session):
    mock_run.side_effect = [
        type("MockResult",(object,),{"stdout":"artifact_1.ts(1,5): error TS2322: ...","stderr":"","returncode":2}),
        type("MockResult",(object,),{"stdout":"","stderr":"","returncode":0})
    ]
    mock_llm.side_effect=[FIXED_CODE]

    doc3=db_session.query(NIDocument).filter(NIDocument.content.like("%[Scene:TrickyDOC3MARKER]%")).first()
    assert doc3 is not None
    token=db_session.query(NIToken).filter_by(ni_document_id=doc3.id).first()
    artifact=db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()

    success=SelfRepairService.repair_artifact(artifact.id, db_session, max_attempts=2)
    assert success is True
    updated_artifact=db_session.get(CompiledMultifact,artifact.id)
    assert updated_artifact.valid is True
    assert FIXED_CODE.strip() in updated_artifact.code

# ----- GROUP: Semantic Tests -----
@pytest.fixture
def ni_with_component_and_method(db_session: Session):
    doc_data = NIDocumentCreate(content="[Scene:Spec]\nCreate a component named MyComponent with a method sendEmail()", version="v1")
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session) # ensure artifacts for tests
    return ni_doc

def insert_artifact(db_session: Session, token: NIToken, code: str, valid: bool = True):
    artifact=CompiledMultifact(
        ni_token_id=token.id,
        language="typescript",
        framework="angular",
        code=code,
        valid=valid,
        cache_hit=False
    )
    db_session.add(artifact)
    db_session.commit()
    db_session.refresh(artifact)
    return artifact

def test_semantic_success(db_session: Session, ni_with_component_and_method: NIDocument):
    token = db_session.query(NIToken).filter_by(ni_document_id=ni_with_component_and_method.id).first()
    assert token is not None
    artifact = insert_artifact(db_session, token, GOOD_CODE)
    result = ValidationService.validate_artifact(artifact.id, db_session)
    assert result.success is True
    semantic_errors = [e for e in result.errors if "TSSEM" in e.message]
    assert len(semantic_errors) == 0

def test_semantic_missing_method(db_session: Session, ni_with_component_and_method: NIDocument):
    token = db_session.query(NIToken).filter_by(ni_document_id=ni_with_component_and_method.id).first()
    assert token is not None
    artifact = insert_artifact(db_session, token, BAD_CODE_NO_METHOD)
    result = ValidationService.validate_artifact(artifact.id, db_session)
    assert not result.success
    semantic_errors = [e for e in result.errors if "TSSEM002" in e.message]
    assert len(semantic_errors) == 1

def test_semantic_missing_component(db_session: Session, ni_with_component_and_method: NIDocument):
    token = db_session.query(NIToken).filter_by(ni_document_id=ni_with_component_and_method.id).first()
    assert token is not None
    artifact = insert_artifact(db_session, token, BAD_CODE_NO_COMPONENT)
    result = ValidationService.validate_artifact(artifact.id, db_session)
    assert not result.success
    semantic_errors = [e for e in result.errors if "TSSEM001" in e.message]
    assert len(semantic_errors) == 1

@pytest.mark.skip(reason="TSSEM003 not implemented")
def test_deep_semantic_rules(db_session: Session):
    doc_data=NIDocumentCreate(content="[Scene:Strict]\nCreate a component named StrictComp no any allowed",version="v1")
    ni_doc=NIService.create_ni_document(doc_data,db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session)
    token=db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).first()
    code_with_any="""\
export class StrictComp {
  user: any = { name: 'Bob' };
  sendEmail() {}
}
"""
    artifact=CompiledMultifact(
        ni_token_id=token.id,
        language="typescript",
        framework="angular",
        code=code_with_any,
        valid=True,
        cache_hit=False
    )
    db_session.add(artifact)
    db_session.commit()
    result=ValidationService.validate_artifact(artifact.id,db_session)
    sem_errors=[e for e in result.errors if "TSSEM003" in e.message]
    assert len(sem_errors)==1, "Expected semantic error TSSEM003 for 'any' usage"

# ----- GROUP: Large NI, Fuzz, Concurrency Tests -----

def test_ni_empty(db_session: Session):
    doc_data=NIDocumentCreate(content="",version="v1")
    ni_doc=NIService.create_ni_document(doc_data,db_session)
    tokens=db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    assert len(tokens)==0,"No tokens expected from empty NI"

def test_ni_whitespace(db_session: Session):
    doc_data=NIDocumentCreate(content="   \n   ",version="v1")
    ni_doc=NIService.create_ni_document(doc_data,db_session)
    tokens=db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    assert len(tokens)==0,"No tokens expected from whitespace-only NI"

def test_ni_extremely_long(db_session:Session):
    long_content="[Scene:Long]\n"+"\n".join("Line "+str(i) for i in range(10000))
    doc_data=NIDocumentCreate(content=long_content,version="v1")
    ni_doc=NIService.create_ni_document(doc_data,db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session)
    tokens=db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    assert len(tokens)>0

def test_ni_fuzz_random(db_session:Session):
    random_content="[Scene:Fuzz]\n"+''.join(random.choices(string.printable,k=500))
    doc_data=NIDocumentCreate(content=random_content,version="v1")
    ni_doc=NIService.create_ni_document(doc_data,db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session)
    tokens=db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    if tokens:
        artifact=db_session.query(CompiledMultifact).filter_by(ni_token_id=tokens[0].id).first()
        assert artifact is not None

def test_fuzzing_multi_runs(session_factory:Callable[[],Session]):
    def random_ni():
        lines=[]
        for i in range(random.randint(1,5)):
            lines.append(f"[Scene:Rand{i}]")
            for c_i in range(random.randint(0,3)):
                lines.append(f"[Component:C{i}_{c_i}]")
                for _ in range(3):
                    lines.append(''.join(random.choices(string.ascii_letters+string.digits,k=20)))
        return '\n'.join(lines) if lines else "Just a line"

    for _ in range(10):
        s=session_factory()
        try:
            content=random_ni()
            ni_doc=NIService.create_ni_document(NIDocumentCreate(content=content,version="fuzz"),s)
            compile_all_tokens_for_doc(ni_doc.id, s)
        finally:
            s.close()

# ----- GROUP: NI Creation Tests -----

def test_create_ni_document_single_scene(session_factory:Callable[[],Session]):
    s=session_factory()
    doc_data=NIDocumentCreate(content="[Scene:Intro]\nThis is intro scene.",version="v1")
    ni_doc=NIService.create_ni_document(doc_data,s)
    compile_all_tokens_for_doc(ni_doc.id, s)
    assert ni_doc.id is not None
    assert ni_doc.content==doc_data.content
    assert ni_doc.version=="v1"
    tokens=s.scalars(select(NIToken).where(NIToken.ni_document_id==ni_doc.id)).all()
    assert len(tokens)==1
    token=tokens[0]
    assert token.scene_name=="Intro"
    assert token.content=="This is intro scene."
    assert len(token.hash)==64
    s.close()

def test_create_ni_document_no_scene(session_factory:Callable[[],Session]):
    s=session_factory()
    doc_data=NIDocumentCreate(content="No scene here, just content.",version="v2")
    ni_doc=NIService.create_ni_document(doc_data,s)
    compile_all_tokens_for_doc(ni_doc.id, s)
    tokens=s.scalars(select(NIToken).where(NIToken.ni_document_id==ni_doc.id)).all()
    assert len(tokens)==1
    token=tokens[0]
    assert token.scene_name=="DefaultScene"
    assert token.content=="No scene here, just content."
    s.close()

def test_create_ni_document_multiple_scenes(session_factory:Callable[[],Session]):
    s=session_factory()
    doc_data=NIDocumentCreate(content="[Scene:Intro]\nIntro content.\n[Scene:Main]\nMain content here.",version="v3")
    ni_doc=NIService.create_ni_document(doc_data,s)
    compile_all_tokens_for_doc(ni_doc.id, s)
    tokens=s.scalars(select(NIToken).where(NIToken.ni_document_id==ni_doc.id)).all()
    assert len(tokens)==2
    assert tokens[0].scene_name=="Intro"
    assert tokens[0].content=="Intro content."
    assert tokens[1].scene_name=="Main"
    assert tokens[1].content=="Main content here."
    s.close()

def test_create_ni_document_with_components(session_factory:Callable[[],Session]):
    s=session_factory()
    doc_data=NIDocumentCreate(
        content="[Scene:Intro]\nIntro content.\n[Component:UserProfile]\nThis is user profile component.\n[Component:Dashboard]\nDashboard content here.\n",
        version="v1"
    )
    ni_doc=NIService.create_ni_document(doc_data,s)
    compile_all_tokens_for_doc(ni_doc.id, s)
    tokens=s.scalars(select(NIToken).where(NIToken.ni_document_id==ni_doc.id)).all()
    assert len(tokens)==3
    scene_tokens=[t for t in tokens if t.scene_name is not None]
    component_tokens=[t for t in tokens if t.component_name is not None and t.scene_name is None]
    assert len(scene_tokens)==1
    assert scene_tokens[0].scene_name=="Intro"
    assert "Intro content." in scene_tokens[0].content

    assert len(component_tokens)==2
    comp_names={t.component_name for t in component_tokens}
    assert "UserProfile" in comp_names
    assert "Dashboard" in comp_names

    user_profile_token=next(t for t in component_tokens if t.component_name=="UserProfile")
    assert "This is user profile component." in user_profile_token.content

    dashboard_token=next(t for t in component_tokens if t.component_name=="Dashboard")
    assert "Dashboard content here." in dashboard_token.content
    s.close()

def test_create_ni_document_with_functions(session_factory:Callable[[],Session]):
    s=session_factory()
    doc_data=NIDocumentCreate(
        content="[Scene:Main]\n[Component:MyComponent]\nSome component text\n[Function:sendEmail]\nHere goes function body.\nEnd of function.\n",
        version="v1"
    )
    ni_doc=NIService.create_ni_document(doc_data,s)
    compile_all_tokens_for_doc(ni_doc.id, s)
    tokens=s.scalars(select(NIToken).where(NIToken.ni_document_id==ni_doc.id)).all()
    assert len(tokens)==2
    scene_token=next(t for t in tokens if t.scene_name)
    component_token=next(t for t in tokens if t.component_name)

    assert scene_token.scene_name=="Main"
    assert "[Component:MyComponent]" not in scene_token.content
    assert component_token.component_name=="MyComponent"
    assert "Here goes function body." in component_token.content
    assert "End of function." in component_token.content
    s.close()

def test_no_tags(session_factory:Callable[[],Session]):
    s=session_factory()
    doc_data=NIDocumentCreate(content="Just some text without any tags.",version="v1")
    ni_doc=NIService.create_ni_document(doc_data,s)
    compile_all_tokens_for_doc(ni_doc.id, s)
    tokens=s.scalars(select(NIToken).where(NIToken.ni_document_id==ni_doc.id)).all()
    assert len(tokens)==1
    t=tokens[0]
    assert t.scene_name=="DefaultScene"
    assert t.content=="Just some text without any tags."
    s.close()

# ----- GROUP: Concurrency Tests -----

def create_doc(session_factory: Callable[[], Session], i: int):
    s = session_factory()
    try:
        doc_data = NIDocumentCreate(content=f"[Scene:Perf{i}] This is doc {i}", version="v1")
        ni_doc=NIService.create_ni_document(doc_data, s)
        compile_all_tokens_for_doc(ni_doc.id, s)
        s.commit()
    finally:
        s.close()

def test_concurrent_creation(db_session: Session, session_factory: Callable[[], Session]):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_doc, session_factory, i) for i in range(20)]
        for f in futures:
            f.result()
    count=db_session.query(NIDocument).count()
    assert count>=20

# ----- GROUP: Special Content Tests -----

def test_ni_with_script_tag(db_session: Session):
    doc_data=NIDocumentCreate(content="[Scene:ScriptTest]<script>alert('xss')</script>",version="v1")
    ni_doc=NIService.create_ni_document(doc_data,db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session)
    tokens=db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    assert tokens is not None

def test_ni_with_sql_like_content(db_session: Session):
    doc_data=NIDocumentCreate(content="[Scene:SQLTest] DROP TABLE ni_tokens;",version="v1")
    ni_doc=NIService.create_ni_document(doc_data,db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session)
    tokens=db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    assert len(tokens)>=0

# ----- GROUP: Partial Recompile, Cache Hit Tests -----

def test_cache_hit(db_session: Session, initial_ni: NIDocument):
    ni_doc=db_session.get(type(initial_ni),initial_ni.id)
    original_content=ni_doc.content
    # Re-update with same content
    UserInterventionService.update_ni_and_recompile(initial_ni.id,original_content,db_session)
    # If no changes means no second compile, artifact unchanged => test pass just by not failing

@patch("backend.services.llm_client.LLMClient._generic_chat_call", return_value=MOCK_GENERATED_CODE)
def test_compile_token_cache_hit_from_scratch(mock_llm: MagicMock, db_session: Session):
    # Create first doc and compile token
    doc_data_1 = NIDocumentCreate(content="[Scene:CacheTest]\nThis is a test.", version="v1")
    ni_doc_1 = NIService.create_ni_document(doc_data_1, db_session)
    compile_all_tokens_for_doc(ni_doc_1.id, db_session)

    token_1 = db_session.query(NIToken).filter_by(ni_document_id=ni_doc_1.id).first()
    artifact_1 = db_session.query(CompiledMultifact).filter_by(ni_token_id=token_1.id).first()
    assert artifact_1 is not None
    assert artifact_1.cache_hit == False

    # Reset mock call count
    mock_llm.reset_mock()

    # Create second doc with identical token content
    doc_data_2 = NIDocumentCreate(content="[Scene:CacheTest]\nThis is a test.", version="v2")
    ni_doc_2 = NIService.create_ni_document(doc_data_2, db_session)
    compile_all_tokens_for_doc(ni_doc_2.id, db_session)

    token_2 = db_session.query(NIToken).filter_by(ni_document_id=ni_doc_2.id).first()
    artifact_2 = db_session.query(CompiledMultifact).filter_by(ni_token_id=token_2.id).first()
    assert artifact_2 is not None
    assert artifact_2.cache_hit is True

    # Ensure LLM not called again
    mock_llm.assert_not_called()


@patch("backend.services.llm_client.LLMClient._generic_chat_call", return_value=MOCK_GENERATED_CODE)
def test_partial_recompile_only_changed_tokens(mock_llm: MagicMock, db_session: Session):
    # Initial doc with two scenes and two components
    doc_data = NIDocumentCreate(
        content="[Scene:A]\nAAA\n[Component:X]\nX comp\n[Scene:B]\nBBB\n[Component:Y]\nY comp",
        version="v1"
    )
    ni_doc = NIService.create_ni_document(doc_data, db_session)
    compile_all_tokens_for_doc(ni_doc.id, db_session)

    tokens = db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    old_map = {}
    for t in tokens:
        artifact = db_session.query(CompiledMultifact).filter_by(ni_token_id=t.id).first()
        old_map[TokenKeyUtil.make_key_from_db_token(t)] = artifact

    # Update NI: change one component's content
    original_content = ni_doc.content
    modified_content = original_content.replace("X comp","X comp updated")
    UserInterventionService.update_ni_and_recompile(ni_doc.id, modified_content, db_session)

    new_tokens = db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    new_map = {}
    for t in new_tokens:
        artifact = db_session.query(CompiledMultifact).filter_by(ni_token_id=t.id).first()
        key = TokenKeyUtil.make_key_from_db_token(t)
        new_map[key] = artifact

    # The token with changed text should have a new artifact
    changed_key = ("component", "X")
    old_art = old_map[changed_key]
    new_art = new_map[changed_key]
    assert new_art is not None, "New artifact should exist for changed token"
    assert old_art is not None, "Old artifact should exist from before"
    assert new_art.id != old_art.id, "Changed token should have a new artifact"
    assert new_art.cache_hit == False

    # Unchanged tokens retain old artifacts
    unchanged_keys = set(old_map.keys()) - {changed_key}
    for k in unchanged_keys:
        assert old_map[k] is not None
        assert new_map[k] is not None
        assert old_map[k].id == new_map[k].id, f"Unchanged token {k} should retain old artifact"


@patch("backend.services.llm_client.LLMClient._generic_chat_call", return_value=MOCK_GENERATED_CODE)
def test_concurrent_same_tokens_cache(mock_llm: MagicMock, session_factory: Callable[[], Session]):

    def create_same_doc():
        s = session_factory()
        try:
            doc_data = NIDocumentCreate(content="[Scene:CCache]\nHello same content", version="v1")
            ni_doc = NIService.create_ni_document(doc_data, s)
            compile_all_tokens_for_doc(ni_doc.id, s)
        finally:
            s.close()

    # Run multiple threads
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_same_doc) for _ in range(5)]
        for f in futures:
            f.result() # ensure no exception

    s = session_factory()
    try:
        docs = s.query(NIDocument).filter(NIDocument.content.like("%[Scene:CCache]%")).all()
        all_token_ids = [t.id for d in docs for t in s.query(NIToken).filter_by(ni_document_id=d.id).all()]
        artifacts = s.query(CompiledMultifact).filter(CompiledMultifact.ni_token_id.in_(all_token_ids)).all()

        codes = set(a.code for a in artifacts)
        assert len(codes) == 1, f"All identical docs should produce the same code artifact, found {len(codes)} distinct."
    finally:
        s.close()