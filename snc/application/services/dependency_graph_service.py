# File: backend/application/services/dependency_graph_service.py

"""Service for building and analyzing dependency graphs between tokens."""

from typing import Dict, Set, List
from collections import defaultdict, deque

from snc.domain.models import DomainToken
from snc.application.interfaces.itoken_repository import ITokenRepository


class DependencyGraphService:
    """Service for building and analyzing dependency graphs between tokens.

    Uses a token repository to build a graph of token dependencies and provides
    methods for analyzing the graph structure, including topological sorting
    to determine the correct order of token processing.
    """

    def __init__(self, token_repo: ITokenRepository):
        """Initialize the service.

        Args:
            token_repo: Repository for accessing tokens
        """
        self.token_repo = token_repo
        self.edges: Dict[int, Set[int]] = defaultdict(set)
        self.tokens: Dict[int, DomainToken] = {}

    def from_document(self, doc_id: int) -> None:
        """Build dependency graph from a document's tokens.

        Args:
            doc_id: ID of document to build graph from

        Raises:
            ValueError: If any token has None as its ID or if a cycle is detected
        """
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

        # Check for cycles using DFS
        visited = set()
        path = set()

        def has_cycle(node: int) -> bool:
            if node in path:
                return True
            if node in visited:
                return False

            visited.add(node)
            path.add(node)

            for dep in self.edges[node]:
                if has_cycle(dep):
                    return True

            path.remove(node)
            return False

        # Check each node for cycles
        for node in self.tokens:
            if node not in visited:
                if has_cycle(node):
                    raise ValueError("Cycle detected in dependency graph.")

    def topological_sort(self) -> List[int]:
        """Sort tokens in topological order based on dependencies.

        Returns:
            List of token IDs in topological order. If A depends on B, B will come before A.

        Raises:
            ValueError: If a cycle is detected in the dependency graph
        """
        # Initialize in-degree for all nodes
        in_degree = {t_id: 0 for t_id in self.tokens.keys()}

        # Count incoming edges - if A depends on B, increment A's in-degree
        for t_id in self.tokens:
            for dep_id in self.edges[t_id]:
                in_degree[t_id] += 1

        # Start with nodes that have no incoming edges (no dependencies)
        queue = deque([t for t in in_degree if in_degree[t] == 0])
        order = []

        while queue:
            node = queue.popleft()
            order.append(node)

            # For each node that depends on the current node
            for t_id in self.tokens:
                if node in self.edges[t_id]:
                    in_degree[t_id] -= 1
                    if in_degree[t_id] == 0:
                        queue.append(t_id)

        if len(order) != len(self.tokens):
            raise ValueError("Cycle detected in dependency graph.")

        return order
