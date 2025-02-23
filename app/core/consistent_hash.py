import hashlib
from typing import List, Dict, Any, Optional, Set
from bisect import bisect
from ..core.config import settings

class ConsistentHash:
    def __init__(self, nodes: List[str], virtual_nodes: int = settings.VIRTUAL_NODES):
        """
        Initialize the consistent hash ring

        Args:
            nodes: List of node identifiers
            virtual_nodes: Number of virtual nodes per physical node
        """
        self.virtual_nodes = virtual_nodes
        self.hash_ring: Dict[int, str] = {}
        self.sorted_keys: List[int] = []
        self.nodes: Set[str] = set()

        for node in nodes:
            self.add_node(node)

    def _get_hash(self, key: str) -> int:
        """
        Calculate hash for a key using MD5

        Args:
            key: The key to hash

        Returns:
            Integer hash value
        """
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_node(self, node: str) -> None:
        """
        Add a node to the hash ring

        Args:
            node: Node identifier to add
        """
        if node in self.nodes:
            return

        self.nodes.add(node)
        
        for i in range(self.virtual_nodes):
            virtual_node_key = f"{node}_{i}"
            hash_key = self._get_hash(virtual_node_key)
            
            while hash_key in self.hash_ring:
                virtual_node_key = f"{virtual_node_key}_collision"
                hash_key = self._get_hash(virtual_node_key)
                
            self.hash_ring[hash_key] = node

        self.sorted_keys = sorted(self.hash_ring.keys())

    def remove_node(self, node: str) -> None:
        """
        Remove a node from the hash ring

        Args:
            node: Node identifier to remove

        Raises:
            ValueError: If node doesn't exist in the ring
        """
        if node not in self.nodes:
            raise ValueError(f"Node {node} not found in hash ring")

        self.nodes.remove(node)
        keys_to_remove = []

        for i in range(self.virtual_nodes):
            virtual_node_key = f"{node}_{i}"
            hash_key = self._get_hash(virtual_node_key)
            keys_to_remove.append(hash_key)

        for key in keys_to_remove:
            self.hash_ring.pop(key, None)

        self.sorted_keys = sorted(self.hash_ring.keys())

    def get_node(self, key: str) -> str:
        """
        Get the node responsible for the given key

        Args:
            key: The key to look up

        Returns:
            The node responsible for the key

        Raises:
            Exception: If hash ring is empty
        """
        if not self.hash_ring:
            raise Exception("Hash ring is empty")

        key_hash = self._get_hash(key)

        idx = bisect(self.sorted_keys, key_hash)
        if idx == len(self.sorted_keys):
            idx = 0

        return self.hash_ring[self.sorted_keys[idx]]

    def get_all_nodes(self) -> Set[str]:
        """
        Get all physical nodes in the ring

        Returns:
            Set of all node identifiers
        """
        return self.nodes.copy()

    def get_node_distribution(self) -> Dict[str, int]:
        """
        Get distribution of keys across nodes

        Returns:
            Dictionary mapping nodes to their key count
        """
        distribution = {}
        for node in self.nodes:
            distribution[node] = sum(1 for n in self.hash_ring.values() if n == node)
        return distribution

    def is_empty(self) -> bool:
        """
        Check if hash ring is empty

        Returns:
            True if ring is empty, False otherwise
        """
        return len(self.hash_ring) == 0

    def clear(self) -> None:
        """Clear the hash ring"""
        self.hash_ring.clear()
        self.sorted_keys.clear()
        self.nodes.clear()