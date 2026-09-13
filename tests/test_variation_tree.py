from xiangqi_tutor.board import Position
from xiangqi_tutor.models.core import Move
from xiangqi_tutor.services import VariationTree


def test_variation_tree_keeps_multiple_branches_and_exact_fens() -> None:
    start = Position.initial()
    tree = VariationTree(start)
    root = tree.current.node_id
    branch_a = tree.play(Move.from_engine("h2e2"))
    expected_a = start.apply_move(Move.from_engine("h2e2")).to_fen()
    assert branch_a.fen == expected_a
    tree.goto(root)
    branch_b = tree.play(Move.from_engine("h0g2"))
    assert branch_b.node_id != branch_a.node_id
    assert len(tree.nodes[root].children) == 2
    tree.goto(branch_a.node_id)
    assert tree.position.to_fen() == expected_a
    assert tree.parent().node_id == root


def test_replaying_existing_branch_does_not_duplicate_it() -> None:
    tree = VariationTree(Position.initial())
    root = tree.root_id
    first = tree.play(Move.from_engine("c3c4"))
    tree.goto(root)
    again = tree.play(Move.from_engine("c3c4"))
    assert first.node_id == again.node_id and len(tree.nodes[root].children) == 1
