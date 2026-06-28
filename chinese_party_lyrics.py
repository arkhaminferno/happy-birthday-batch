"""Chinese festival EDM party body — Verse 2 onward (Verse 1 stays English HB)."""

from __future__ import annotations

CELEBRATEVIBES_V2_CHINA_CAPTION_SUFFIX = (
    "Verse 2 onward party lyrics are Mandarin Chinese only. Keep festival EDM production — "
    "same commercial dance-pop energy as the English birthday anthem."
)

CELEBRATEVIBES_V2_CHINA_INSTRUCTION_SUFFIX = (
    "After Verse 1, sing the supplied Mandarin Chinese lyrics with clear native diction. "
    "Same energetic festival vocal throughout. Pronounce the birthday name correctly."
)


def build_chinese_body_lyrics(name: str, *, variant: int = 0, native_name: str = "") -> str:
    """Return Chinese party body with rotating templates for batch uniqueness."""
    nm = (native_name or name).strip()
    variant = variant % 4

    if variant == 0:
        verse2 = """今晚是属于你的夜晚
梦想飞向远方
每张笑脸都闪耀
大家一起把歌唱"""
        chorus = f"""哦... 哦... 哦...
{nm}!
今晚属于你
大家一起唱
生日快乐!
哦... 哦... 哦...
{nm}!
心声在回响
生日快乐!"""
    elif variant == 1:
        verse2 = """节拍响起灯光闪耀
派对因你而热闹
朋友围绕笑声不断
这夜晚属于你知道"""
        chorus = f"""嘿! 嘿! {nm}!
把手举向天空
生日快乐 {nm}!
一起跳舞到天明
嘿! 嘿! {nm}!
这是你的庆典
生日快乐!"""
    elif variant == 2:
        verse2 = """星光为你而明亮
快乐就在身旁
愿你梦想都实现
幸福永远绵长"""
        chorus = f"""哦... 哦... 哦...
{nm}!
今天你是主角
大家一起唱
生日快乐!
哦... 哦... 哦...
{nm}!
心跳跟着节拍
生日快乐!"""
    else:
        verse2 = """霓虹闪烁节奏强劲
你是今晚的明星
音乐环绕笑声阵阵
舞动起来别停"""
        chorus = f"""哦... 哦... 哦...
{nm}!
今夜为你而狂欢
大家一起喊
生日快乐!
哦... 哦... 哦...
{nm}!
让快乐传开
生日快乐!"""

    verse3 = """愿好运永远伴随
愿笑容从不离开
每个清晨都阳光
每一步都精彩"""
    verse4 = """愿梦想都能实现
愿成功就在前面
每个瞬间都庆典
世界随你旋转"""
    final_chorus = f"""哦... 哦... 哦...
{nm}!
今晚属于你
大家一起唱
生日快乐!
生日快乐!
生日快乐!
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
