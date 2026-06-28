"""Russian festival EDM party body — Verse 2 onward (Verse 1 stays English HB)."""

from __future__ import annotations

CELEBRATEVIBES_V2_RUSSIA_CAPTION_SUFFIX = (
    "Verse 2 onward party lyrics are Russian only. Keep festival EDM production — "
    "same commercial dance-pop energy as the English birthday anthem."
)

CELEBRATEVIBES_V2_RUSSIA_INSTRUCTION_SUFFIX = (
    "After Verse 1, sing the supplied Russian Cyrillic lyrics with clear native diction. "
    "Same energetic festival vocal throughout. Pronounce the birthday name correctly."
)


def build_russian_body_lyrics(name: str, *, variant: int = 0, native_name: str = "") -> str:
    """Return Russian party body with rotating templates for batch uniqueness."""
    nm = (native_name or name).strip()
    variant = variant % 4

    if variant == 0:
        verse2 = """Сегодня ночь сияет для тебя
Мечты летят в небеса
Каждый улыбается сейчас
Все поют вместе для нас"""
        chorus = f"""О... о... о...
{nm}!
Сегодня ночь твоя
Все поют вместе
С днём рождения!
О... о... о...
{nm}!
Пусть звучит везде
С днём рождения!"""
    elif variant == 1:
        verse2 = """Бас гремит, огни горят
Танцпол зовёт тебя
Друзья рядом, смех звучит
Эта ночь — твоя, друзья"""
        chorus = f"""Эй! Эй! {nm}!
Поднимай руки в небо
С днём рождения, {nm}!
Танцуем до утра
Эй! Эй! {nm}!
Праздник для тебя
С днём рождения!"""
    elif variant == 2:
        verse2 = """Звёзды ярко над тобой
Счастье рядом, ты — герой
Пусть мечты сбываются
Пусть радость не кончается"""
        chorus = f"""О... о... о...
{nm}!
Сегодня только ты
Все вместе поют
С днём рождения!
О... о... о...
{nm}!
Сердца поют в такт
С днём рождения!"""
    else:
        verse2 = """Неон, ритм, огонь в глазах
Праздник — это ты сейчас
Смех и музыка вокруг
Танцуй, пока играет звук"""
        chorus = f"""О... о... о...
{nm}!
Ночь принадлежит тебе
Все кричат вместе
С днём рождения!
О... о... о...
{nm}!
Пусть звучит громко
С днём рождения!"""

    verse3 = """Пусть удача будет рядом
Пусть мечты сбываются
Каждый день — как праздник
Счастье не кончается"""
    verse4 = """Пусть все цели будут близко
Пусть успех идёт с тобой
Пусть каждый миг — веселье
Мир поёт с тобой"""
    final_chorus = f"""О... о... о...
{nm}!
Сегодня ночь твоя
Все вместе поют
С днём рождения!
С днём рождения!
С днём рождения!
{nm}!"""

    return f"""[Verse 2]
{verse2}

[Chorus]
{chorus}

[Verse 3]
{verse3}

[Verse 4]
{verse4}

[Final Chorus]
{final_chorus}"""
