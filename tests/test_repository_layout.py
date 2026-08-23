from audit_repository_layout import hygiene_problems


def test_repository_layout_hygiene() -> None:
    problems = hygiene_problems()
    assert not problems, "repository hygiene defects:\n- " + "\n- ".join(problems)
