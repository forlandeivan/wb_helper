from __future__ import annotations

from wb_helper.parsers.articles import parse_article_candidates


def test_parse_marketplace_specific_articles() -> None:
    text = "WB 12345678, Ozon 99887766"

    candidates = parse_article_candidates(text)

    assert [(item.marketplace_hint, item.normalized_value) for item in candidates] == [
        ("wb", "12345678"),
        ("ozon", "99887766"),
    ]


def test_parse_generic_article_marker() -> None:
    text = "арт. 12345678"

    candidates = parse_article_candidates(text)

    assert len(candidates) == 1
    assert candidates[0].marketplace_hint == "generic"
    assert candidates[0].confidence == "medium"


def test_deduplicates_same_marketplace_and_article() -> None:
    text = "WB 12345678 и wb 12345678"

    candidates = parse_article_candidates(text)

    assert len(candidates) == 1


def test_does_not_parse_bare_numbers() -> None:
    text = "Смотрите 12345678 и 87654321 без подписи"

    assert parse_article_candidates(text) == []


def test_parses_article_section_with_bullets_and_trailing_numbers() -> None:
    text = (
        "Артикулы ⤵️\n"
        "Рост 186см Вес 83кг\n\n"
        "Коричневый с лампасами ⤵️\n"
        "• 464532320\n"
        "Черный ⤵️\n"
        "• 368755486\n"
        "Коричневый с полузамком ⤵️\n"
        "• 786044878\n\n"
        "• Футболка бел. 28515518\n"
        "• Кроссовки бел. 198244837\n"
        "• Кепка черн. 215841244\n"
        "• Очки кор. 209422236\n"
        "• Очки черн. 62627742\n"
    )

    candidates = parse_article_candidates(text)

    assert [item.normalized_value for item in candidates] == [
        "464532320",
        "368755486",
        "786044878",
        "28515518",
        "198244837",
        "215841244",
        "209422236",
        "62627742",
    ]
    assert all(item.marketplace_hint == "generic" for item in candidates)


def test_prefers_explicit_marketplace_over_generic_context_parse() -> None:
    text = "Артикулы\n• WB 12345678"

    candidates = parse_article_candidates(text)

    assert [(item.marketplace_hint, item.normalized_value) for item in candidates] == [("wb", "12345678")]


def test_applies_single_global_marketplace_context() -> None:
    text = "Все артикулы на WB\n• 12345678\n• Футболка 23456789"

    candidates = parse_article_candidates(text)

    assert [(item.marketplace_hint, item.normalized_value) for item in candidates] == [
        ("wb", "12345678"),
        ("wb", "23456789"),
    ]


def test_does_not_force_marketplace_when_both_are_mentioned() -> None:
    text = "WB и Ozon\n• 12345678"

    candidates = parse_article_candidates(text)

    assert [(item.marketplace_hint, item.normalized_value) for item in candidates] == [
        ("generic", "12345678"),
    ]


def test_parses_numbered_hash_article_list_with_global_marketplace() -> None:
    text = (
        "Подборка джинс в синем цвете\n\n"
        "WB\n"
        "1 джинсы #789076262\n"
        "2 джинсы #789266180\n"
        "3 джинсы #731674372\n"
    )

    candidates = parse_article_candidates(text)

    assert [(item.marketplace_hint, item.normalized_value) for item in candidates] == [
        ("wb", "789076262"),
        ("wb", "789266180"),
        ("wb", "731674372"),
    ]
