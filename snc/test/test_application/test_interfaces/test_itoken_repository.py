import pytest
from typing import Optional, List, Tuple
from snc.application.interfaces.itoken_repository import ITokenRepository
from snc.domain.models import DomainToken, DomainCompiledMultifact


def test_itoken_repository_is_abstract():
    with pytest.raises(TypeError, match="Can't instantiate abstract class ITokenRepository"):
        ITokenRepository()  # type: ignore


def test_itoken_repository_minimal_subclass():
    class MinimalTokenRepo(ITokenRepository):
        def get_tokens_with_artifacts(
            self, ni_id: int
        ) -> List[Tuple[DomainToken, Optional[DomainCompiledMultifact]]]:
            return []

        def remove_tokens(
            self,
            tokens: List[DomainToken],
            artifacts: List[DomainCompiledMultifact],
        ) -> None:
            pass

        def update_changed_tokens(
            self,
            changed_data: List[Tuple[DomainToken, Optional[DomainCompiledMultifact], dict]],
        ) -> None:
            pass

        def add_new_tokens(self, ni_id: int, token_data_list: List[dict]) -> List[DomainToken]:
            return []

        def get_artifact(self, artifact_id: int) -> Optional[DomainCompiledMultifact]:
            return None

        def get_token_by_id(self, token_id: int) -> Optional[DomainToken]:
            return None

        def get_doc_id_for_token_uuid(self, token_uuid: str) -> Optional[int]:
            return None

        def get_all_tokens_for_document(self, doc_id: int) -> List[DomainToken]:
            return []

        def create_token(
            self,
            doc_id: int,
            token_type: str,
            token_name: str,
            scene_name: Optional[str],
            component_name: Optional[str],
            function_name: Optional[str],
            content: str,
        ) -> DomainToken:
            import uuid

            return DomainToken(
                id=1,
                token_uuid=str(uuid.uuid4()),
                token_type=token_type,
                token_name=token_name,
                scene_name=scene_name,
                component_name=component_name,
                function_name=function_name,
                content=content,
                hash="test-hash",
            )

    repo = MinimalTokenRepo()
    assert repo is not None
