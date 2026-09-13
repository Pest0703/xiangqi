from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from xiangqi_tutor.board import Position
from xiangqi_tutor.models.core import Move
from xiangqi_tutor.models.engine import AnalysisResult


@dataclass(slots=True)
class VariationNode:
    node_id: str
    parent_id: str | None
    move: str | None
    fen: str
    children: list[str] = field(default_factory=list)
    analysis: AnalysisResult | None = None
    annotations: dict[str, str] = field(default_factory=dict)
    source: str = "sandbox"


class VariationTree:
    """独立于 GameService undo/redo 的非破坏性沙盘树。"""

    def __init__(self, position: Position, *, source: str = "main") -> None:
        root = VariationNode(str(uuid4()), None, None, position.to_fen(), source=source)
        self.nodes: dict[str, VariationNode] = {root.node_id: root}
        self.root_id = root.node_id
        self.current_id = root.node_id

    @property
    def current(self) -> VariationNode:
        return self.nodes[self.current_id]

    @property
    def position(self) -> Position:
        return Position.from_fen(self.current.fen)

    def play(self, move: Move, *, source: str = "sandbox") -> VariationNode:
        for child_id in self.current.children:
            child = self.nodes[child_id]
            if child.move == move.engine:
                self.current_id = child_id
                return child
        after = self.position.apply_move(move)
        node = VariationNode(str(uuid4()), self.current_id, move.engine, after.to_fen(), source=source)
        self.nodes[node.node_id] = node
        self.current.children.append(node.node_id)
        self.current_id = node.node_id
        return node

    def goto(self, node_id: str) -> VariationNode:
        if node_id not in self.nodes:
            raise KeyError("沙盘节点不存在")
        self.current_id = node_id
        return self.current

    def parent(self) -> VariationNode:
        parent_id = self.current.parent_id
        if parent_id is not None:
            self.current_id = parent_id
        return self.current

    def attach_analysis(self, analysis: AnalysisResult) -> None:
        if analysis.fen != self.current.fen:
            raise ValueError("分析结果不属于当前沙盘节点")
        self.current.analysis = analysis
