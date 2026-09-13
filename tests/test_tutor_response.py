from xiangqi_tutor.tutor import TutorResponse


def test_tutor_response_drops_invalid_visual_coordinates() -> None:
    response = TutorResponse.from_payload(
        {
            "summary": "关注中路",
            "arrows": [
                {"source": "h2", "target": "e2", "type": "recommended"},
                {"source": "z9", "target": "e2", "type": "danger"},
            ],
            "highlights": [{"square": "e4", "type": "key"}, {"square": "a10", "type": "danger"}],
            "key_squares": ["e4", "z2"],
        }
    )
    assert len(response.arrows) == 1 and response.arrows[0].source == "h2"
    assert len(response.highlights) == 1 and response.key_squares == ["e4"]


def test_plain_text_response_remains_usable() -> None:
    response = TutorResponse.parse_text("从当前引擎数据暂时无法确定这一点。")
    assert response.summary.startswith("从当前")
