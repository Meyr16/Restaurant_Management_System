import random, heapq, time
from typing import Any, Dict, List, Optional, Tuple

### Stack & Queue ###
class Stack:
    def __init__(self): self.items: List[Any] = []
    def push(self, x): self.items.append(x)
    def pop(self): return self.items.pop() if self.items else None
    def peek(self): return self.items[-1] if self.items else None
    def is_empty(self): return not self.items

class Queue:
    def __init__(self): self.items: List[Any] = []
    def enqueue(self, x): self.items.append(x)
    def dequeue(self): return self.items.pop(0) if self.items else None
    def is_empty(self): return not self.items

### Linked List ###
class LLNode:
    def __init__(self, val: Any):
        self.val = val
        self.next: Optional['LLNode'] = None

class LinkedList:
    def __init__(self):
        self.head: Optional[LLNode] = None
    def append(self, val: Any):
        node = LLNode(val)
        if not self.head:
            self.head = node
        else:
            cur = self.head
            while cur.next:
                cur = cur.next
            cur.next = node
    def find(self, val: Any) -> bool:
        cur = self.head
        while cur:
            if cur.val == val:
                return True
            cur = cur.next
        return False
    def delete(self, val: Any) -> bool:
        cur = self.head
        prev = None
        while cur:
            if cur.val == val:
                if prev:
                    prev.next = cur.next
                else:
                    self.head = cur.next
                return True
            prev, cur = cur, cur.next
        return False

### Binary Search Tree ###
class BSTNode:
    def __init__(self, key: Any):
        self.key = key
        self.left: Optional['BSTNode'] = None
        self.right: Optional['BSTNode'] = None

class BST:
    def __init__(self):
        self.root: Optional[BSTNode] = None
    def insert(self, key: Any):
        def _ins(node, key):
            if not node: return BSTNode(key)
            if key < node.key:
                node.left = _ins(node.left, key)
            else:
                node.right = _ins(node.right, key)
            return node
        self.root = _ins(self.root, key)

    def search(self, key: Any) -> bool:
        cur = self.root
        while cur:
            if key == cur.key:
                return True
            cur = cur.left if key < cur.key else cur.right
        return False

### Sortier-Algorithmen ###
def bubble_sort(arr: List[Any]) -> List[Any]:
    a = arr.copy()
    for i in range(len(a)):
        for j in range(len(a)-i-1):
            if a[j] > a[j+1]:
                a[j], a[j+1] = a[j+1], a[j]
    return a

def merge_sort(arr: List[Any]) -> List[Any]:
    if len(arr) <= 1: return arr
    mid = len(arr)//2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return _merge(left, right)

def _merge(left, right):
    res = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            res.append(left[i]); i += 1
        else:
            res.append(right[j]); j += 1
    res.extend(left[i:] + right[j:])
    return res

def quick_sort(arr: List[Any]) -> List[Any]:
    if len(arr) <= 1: return arr
    pivot = arr[0]
    less = [x for x in arr[1:] if x <= pivot]
    more = [x for x in arr[1:] if x > pivot]
    return quick_sort(less) + [pivot] + quick_sort(more)

### Suchalgorithmen ###
def linear_search(arr: List[Any], target: Any) -> int:
    for i, v in enumerate(arr):
        if v == target:
            return i
    return -1

def binary_search(arr: List[Any], target: Any) -> int:
    lo, hi = 0, len(arr)-1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

### Graph & Algorithmen ###
class Graph:
    def __init__(self):
        self.adj: Dict[Any, List[Tuple[Any, float]]] = {}

    def add_edge(self, u, v, w=1.0):
        self.adj.setdefault(u, []).append((v, w))
        self.adj.setdefault(v, []).append((u, w))

    def neighbors(self, u):
        return self.adj.get(u, [])

def shortest_path(graph: Graph, src: Any) -> Dict[Any, float]:
    dist = {src: 0.0}
    pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        for v, w in graph.neighbors(u):
            nd = d + w
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist

def prim_mst(graph: Graph, start: Any) -> List[Tuple[Any, Any, float]]:
    visited = set([start])
    edges = [(w, start, v) for v, w in graph.neighbors(start)]
    heapq.heapify(edges)
    mst = []
    while edges:
        w, u, v = heapq.heappop(edges)
        if v in visited: continue
        visited.add(v)
        mst.append((u, v, w))
        for v2, w2 in graph.neighbors(v):
            if v2 not in visited:
                heapq.heappush(edges, (w2, v, v2))
    return mst

### Utility: Laufzeitmessung ###
def measure(func, *args):
    t0 = time.time()
    out = func(*args)
    return out, time.time() - t0