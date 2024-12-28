# File: backend/application/services/dependency_graph_service.py

from typing import Dict, Set, List
from collections import defaultdict, deque

from snc.domain.models import DomainToken
from snc.application.interfaces.itoken_repository import ITokenRepository


class DependencyGraphService:
    """
    Builds a dependency graph using domain tokens retrieved from the token repository.
    """

    def __init__(self, token_repo: ITokenRepository):
        self.token_repo = token_repo
        self.edges: Dict[int, Set[int]] = defaultdict(set)
        self.tokens: Dict[int, DomainToken] = {}

    def from_document(self, doc_id: int):
        tokens = self.token_repo.get_all_tokens_for_document(doc_id)
        # tokens is a list of DomainToken, each possibly with dependencies
        for t in tokens:
            if t.id is None:
                raise ValueError("Token ID cannot be None")
            self.tokens[t.id] = t

        for t in tokens:
            for dep in t.dependencies:
                if t.id is None or dep.id is None:
                    raise ValueError("Token ID cannot be None")
                self.edges[t.id].add(dep.id)

    def topological_sort(self) -> List[int]:
        in_degree = {t_id: 0 for t_id in self.tokens.keys()}
        for t, deps in self.edges.items():
            for d in deps:
                in_degree[t] += 1

        queue = deque([t for t in in_degree if in_degree[t] == 0])
        order = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for t, deps in self.edges.items():
                if node in deps:
                    in_degree[t] -= 1
                    if in_degree[t] == 0:
                        queue.append(t)

        if len(order) != len(self.tokens):
            raise ValueError("Cycle detected in dependency graph.")
        return order
