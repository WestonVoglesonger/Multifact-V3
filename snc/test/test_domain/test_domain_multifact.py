from datetime import datetime, timezone
from snc.domain.models import DomainCompiledMultifact


def test_domain_compiled_multifact_init():
    """
    Verify DomainCompiledMultifact holds the artifact data properly.
    """
    now = datetime.now(timezone.utc)
    artifact = DomainCompiledMultifact(
        artifact_id=99,
        ni_token_id=202,
        language="typescript",
        framework="angular",
        code="console.log('Hello');",
        valid=True,
        cache_hit=False,
        created_at=now,
    )
    assert artifact.id == 99
    assert artifact.ni_token_id == 202
    assert artifact.language == "typescript"
    assert artifact.framework == "angular"
    assert artifact.code == "console.log('Hello');"
    assert artifact.valid is True
    assert artifact.cache_hit is False
    assert artifact.created_at == now
