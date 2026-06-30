"""Build structured birthday lyrics for ACE-Step batch generation."""

from __future__ import annotations

import hashlib

from batch_birthday.hindi_party_lyrics import build_hindi_body_lyrics
from batch_birthday.native_party_lyrics import build_native_body_lyrics
from batch_birthday.name_pronunciation import resolve_pronunciation

# Maps CSV language codes to ACE-Step vocal_language values.
LANGUAGE_MAP: dict[str, str] = {
    "en": "en",
    "es": "es",
    "hi": "hi",
    "zh": "zh",
    "ja": "ja",
    "ko": "ko",
    "pt": "pt",
    "fr": "fr",
    "de": "de",
    "ar": "ar",
}

# Default tempo for classic birthday variants.
FAST_BIRTHDAY_BPM = 132
DEFAULT_BIRTHDAY_BPM = FAST_BIRTHDAY_BPM
EDM_PARTY_BPM = 128
PARTY_DANCE_BPM = 124
BIRTHDAY_ANTHEM_BPM = 118
BIRTHDAY_CLASSIC_EXTENDED_BPM = 105
BIRTHDAY_RESTAURANT_BPM = 108
BIRTHDAY_EDM_PARTY_BPM = 128
DEFAULT_TIME_SIGNATURE = "3"

# Default target length per commercial template (seconds).
GENRE_DURATION_SEC: dict[str, int] = {
    "birthday_edm_party_v1": 150,
    "birthday_edm_party_v2": 150,
    "birthday_edm_party_v3": 150,
    "birthday_edm_party_v4": 150,
    "birthday_edm_party_v5": 150,
    "birthday_edm_party_v6_restore": 165,
    "birthday_edm_party_v7": 165,
    "celebratevibes_v2": 165,
    "birthday_restaurant_party_v1": 180,
    "birthday_classic_extended": 240,
}

# Auto slug suffix when CSV slug is empty (commercial template).
ANTHEM_SLUG_SUFFIXES: dict[str, str] = {
    "birthday_anthem_female": "birthday-anthem-female",
    "birthday_anthem_male_choir": "birthday-anthem-male",
    "birthday_anthem_female_choir": "birthday-anthem-female-choir",
    "birthday_classic_extended": "birthday-classic-extended",
    "birthday_restaurant_party_v1": "birthday-restaurant-party",
    "birthday_edm_party_v1": "birthday-edm-party",
    "birthday_edm_party_v2": "birthday-edm-party",
    "birthday_edm_party_v3": "birthday-edm-party",
    "birthday_edm_party_v4": "birthday-edm-party",
    "birthday_edm_party_v5": "birthday-edm-party",
    "birthday_edm_party_v6_restore": "birthday-edm-party",
    "birthday_edm_party_v7": "birthday-edm-party",
    "celebratevibes_v2": "birthday-edm-party",
}

# Per-genre time signature (dance/party = 4/4).
GENRE_TIME_SIGNATURE: dict[str, str] = {
    "edm_party_anthem": "4",
    "party_dance": "4",
    "song_cover": "4",
    "song_guitar_cover": "4",
    "birthday_anthem_female": "4",
    "birthday_anthem_male_choir": "4",
    "birthday_anthem_female_choir": "4",
    "birthday_classic_extended": "3",
    "birthday_restaurant_party_v1": "3",
    "birthday_edm_party_v1": "4",
    "birthday_edm_party_v2": "4",
    "birthday_edm_party_v3": "4",
    "birthday_edm_party_v4": "4",
    "birthday_edm_party_v5": "4",
    "birthday_edm_party_v6_restore": "4",
    "birthday_edm_party_v7": "4",
    "celebratevibes_v2": "4",
    "happy_birthday_fast": "3",
    "user_template_cover": "3",
}

_PRODUCTION_HINT = (
    "professional studio recording, polished commercial mix, radio quality, high fidelity, "
    "full band arrangement, grand piano, orchestral strings, light drums, hand claps, "
    "NOT solo piano, NOT amateur, NOT toy keyboard, NOT instrumental only"
)

_VOCAL_HINT = (
    "lead vocalist singing lyrics clearly throughout, mature adult female singer, "
    "warm professional voice, strong clear diction, NOT child voice, NOT humming only"
)

_MELODY_HINT = (
    "traditional Happy Birthday to You melody, classic worldwide birthday tune"
)

# Cover strength when source is a vocal duet reference (balance melody + new lyrics).
USER_TEMPLATE_COVER_STRENGTH = 0.55

_DUET_VOCAL_HINT = (
    "two singers duet, male and female vocalists singing together, "
    "harmonizing, cheerful birthday party, clear lyrics, NOT instrumental only"
)

# Style-transfer strength when using user template as reference_audio (text2music).
USER_TEMPLATE_REFERENCE_STRENGTH = 0.35
SONG_COVER_STRENGTH = 0.76
# Cover mode ~50%: keep song melody/structure, swap full production for solo guitar.
GUITAR_COVER_STRENGTH = 0.50

# Bollywood / film-song cover (preserve source melody and mood).
_SONG_COVER_CAPTION = (
    "Bollywood romantic ballad cover, emotional Hindi film song, Haunted movie style, "
    "melancholic heartfelt, male vocalist singing clearly, piano and strings, "
    "atmospheric, cinematic, preserve original melody and arrangement feel, "
    "professional studio recording, NOT EDM, NOT fast dance"
)

# Same song as source — acoustic guitar cover (not a new composition).
_GUITAR_COVER_CAPTION = (
    "acoustic guitar cover of the same song, unplugged live room recording, "
    "solo fingerstyle steel-string acoustic guitar playing the original melody, "
    "male vocalist singing the same Hindi lyrics clearly, emotional romantic ballad, "
    "preserve exact song melody and vocal phrasing, same tempo and structure, "
    "NO drums, NO beat, NO percussion, NO bass, NO synth, NO piano, NO strings, "
    "NO orchestra, NOT Bollywood film production, NOT cinematic, "
    "only acoustic guitar and voice, recognizable same song"
)

GUITAR_COVER_INSTRUCTION = (
    "Acoustic guitar cover of this exact song. Preserve the original melody, vocal "
    "melody line, tempo, phrasing, and song structure from the source. Replace ALL "
    "film production (drums, beats, bass, synth, strings, orchestra) with solo "
    "fingerpicked acoustic steel-string guitar and male vocals only. "
    "It must remain the same recognizable song, not a new composition."
)

# Vocals must sit on top of the mix — fixes "lyrics not hearable".
_VOCAL_FORWARD = (
    "prominent lead female vocal upfront in the mix, vocals loud and clear, "
    "every word sung with strong diction, lyrics easy to hear and understand, "
    "NOT buried in the mix, NOT instrumental only, NOT mumbling, NOT humming"
)

# Former dance-party body (drop + party verses) — used in hybrid edit part 2.
_PARTY_DANCE_BODY_CAPTION = (
    "happy birthday party dance song, festive celebration anthem, "
    "danceable four-on-the-floor groove, upbeat energetic, people dancing, "
    f"{_VOCAL_FORWARD}, light group harmonies behind lead vocal, "
    "punchy dance drums, deep bass, bright synth lead, piano stabs, hand claps, "
    "modern pop dance production, polished club mix, high energy sing-along chorus"
)

# Intro: beat from bar one + classic melody (for cake-cutting moment).
_PARTY_DANCE_INTRO_CAPTION = (
    "birthday party dance track, full four-on-the-floor beat from the very first second, "
    "drums bass synths claps start immediately, NO slow intro, NO waltz, NO dull opening, "
    "high energy from second zero, cake cutting party vibe, "
    f"{_VOCAL_FORWARD}, "
    "singing the traditional Happy Birthday to You melody over the dance beat, "
    "classic recognizable worldwide birthday tune, hand claps, joyful sing-along"
)

# Single-pass fallback (legacy).
_PARTY_DANCE_CAPTION = _PARTY_DANCE_BODY_CAPTION

# Modern commercial birthday anthem — reusable template (text2music + LM vocals).
_BIRTHDAY_ANTHEM_BASE = (
    "modern birthday anthem, uplifting pop, piano, acoustic guitar, light strings, "
    "uplifting drums, hand claps, family celebration atmosphere, radio-quality production, "
    "emotional verses, huge singalong chorus, suitable for birthdays of all ages, "
    "memorable and heartwarming, traditional Happy Birthday intro then original song"
)

_BIRTHDAY_ANTHEM_FEMALE_CHOIR_CAPTION = (
    f"{_BIRTHDAY_ANTHEM_BASE}, warm female lead vocal, supporting mixed choir in choruses, "
    "children and adults singing together on hooks, choir swells on Happy Birthday sections"
)

_BIRTHDAY_ANTHEM_MALE_CHOIR_CAPTION = (
    f"{_BIRTHDAY_ANTHEM_BASE}, warm male lead vocal solo in verses, "
    "light mixed group choir joins in choruses and Happy Birthday hooks, NOT children's choir"
)

_BIRTHDAY_ANTHEM_FEMALE_CAPTION = (
    f"{_BIRTHDAY_ANTHEM_BASE}, warm female lead vocal, light group harmonies in chorus"
)

BIRTHDAY_ANTHEM_VOCAL_INSTRUCTION = (
    "Sing every lyric clearly and prominently. Pronounce the birthday name with strong "
    "diction. Open with the traditional Happy Birthday melody for about 25 seconds, "
    "then transition into the original anthem. Choir joins big on choruses."
)

BIRTHDAY_ANTHEM_GENRES = frozenset(
    {
        "birthday_anthem_female",
        "birthday_anthem_male_choir",
        "birthday_anthem_female_choir",
    }
)

# Melody-first: Happy Birthday tune is the song, not a pop intro.
_BIRTHDAY_CLASSIC_EXTENDED_CAPTION = (
    "Traditional Happy Birthday to You melody is the main musical theme throughout "
    "the entire song. The song repeatedly returns to the familiar Happy Birthday tune. "
    "Every verse and section derived from the classic Happy Birthday musical motif. "
    "Children's birthday party atmosphere, singalong style, memorable and playful, "
    "easy for a crowd to join, warm female lead vocal, mixed choir on refrains, "
    "piano, acoustic guitar, light hand claps, gentle waltz feel, "
    "NOT unrelated pop song, NOT generic anthem melody, NOT cinematic, NOT epic, "
    "NOT modern pop, keep the traditional birthday tune recognizable beginning to end"
)

BIRTHDAY_CLASSIC_EXTENDED_INSTRUCTION = (
    "The globally recognized Happy Birthday to You melody must remain the primary "
    "motif for the full duration. Do not transition into a new pop melody. Do not "
    "replace the birthday tune with a generic song. Return to the classic Happy "
    "Birthday melody after every short verse. Pronounce the birthday name clearly. "
    "Choir joins on every Happy Birthday refrain."
)

CLASSIC_BIRTHDAY_GENRES = frozenset(
    {"birthday_classic_extended", "birthday_restaurant_party_v1"}
)

# Busy restaurant party — crowd claps, singalong, Happy Birthday melody throughout.
_BIRTHDAY_RESTAURANT_PARTY_CAPTION = (
    "Restaurant birthday celebration song, traditional Happy Birthday to You melody "
    "recognizable throughout the entire song, busy family restaurant atmosphere, "
    "friends clapping, crowd singing along, party energy, warm female lead vocal, "
    "mixed adult choir on refrains, piano, hand claps, light drums, bass, "
    "party percussion, call-and-response crowd sections, simple singalong lyrics, "
    "NOT ballad, NOT emotional storytelling, NOT slow sections, NOT cinematic "
    "orchestration, NOT modern pop anthem, NOT unrelated melody"
)

BIRTHDAY_RESTAURANT_PARTY_INSTRUCTION = (
    "Restaurant birthday party song. The Happy Birthday to You melody must stay "
    "recognizable from start to finish. High energy, hand claps, crowd chants, "
    "call-and-response so strangers can join. Pronounce the birthday name clearly. "
    "No emotional bridge, no inspirational life-story lyrics, no slow ballad sections."
)

# EDM remix of Happy Birthday — Celebrate Today style, not a story song.
_BIRTHDAY_EDM_PARTY_CAPTION = (
    "High-energy birthday party song, 128 BPM dance-pop, electronic party music, "
    "traditional Happy Birthday to You melody is the primary vocal melody throughout "
    "the entire song, restaurant birthday celebration atmosphere, crowd claps, "
    "group singalong, birthday party chants, children and adults celebrating together, "
    "EDM build-up, festival-style drop, bright synthesizers, four-on-the-floor kick drum, "
    "party horns, confetti and celebration energy, "
    "NOT emotional verses, NOT storytelling sections, NOT pop ballad, "
    "NOT unrelated melody, keep returning to traditional Happy Birthday melody"
)

BIRTHDAY_EDM_PARTY_INSTRUCTION = (
    "EDM party remix of the traditional Happy Birthday melody only. Countdown, drop, "
    "dance beat, party chants, then Happy Birthday vocal melody again. No verses about "
    "life or emotions. No bridge. No ballad. Pronounce the birthday name clearly on "
    "every Happy Birthday line. Loop drops and chants between Happy Birthday refrains."
)

_BIRTHDAY_EDM_PARTY_V2_CAPTION = (
    "128 BPM festival EDM dance-pop, classic birthday party atmosphere. The primary vocals "
    "MUST strictly follow the traditional, globally sung Happy Birthday to You melody and "
    "rhythmic phrasing (3/4 waltz melody adapted into a powerful 4/4 electronic dance "
    "rhythm). High-energy restaurant birthday celebration, massive crowd singalong, heavy "
    "crowd hand claps, celebratory party horn blasts. 3-2-1 countdown building up into a "
    "huge, explosive four-on-the-floor kick drum festival drop. Bright uplifting "
    "synthesizers, energetic crowd hype chants Hey! Hey! Hey!, confetti explosion energy, "
    "strictly celebratory party vibes, no pop verses, no storytelling"
)

BIRTHDAY_EDM_PARTY_V2_INSTRUCTION = (
    "Adapt the globally sung Happy Birthday to You melody and its dotted rhythmic phrasing "
    "into the 128 BPM four-on-the-floor EDM grid. Do NOT invent a new pop hook. Countdown, "
    "explosive drop, then traditional Happy Birthday vocal melody with correct phrasing. "
    "Pack Hey! Hey! Hey! and Let's celebrate chants between refrains only. Party horns, "
    "confetti, crowd cheering. No storytelling, no ballad, no generic filler lines. "
    "Pronounce the birthday name clearly."
)

_BIRTHDAY_EDM_PARTY_V3_CAPTION = (
    "128 BPM energetic electronic dance-pop, festive birthday celebration atmosphere, "
    "four-on-the-floor kick drum, bright synthesizers, crowd claps, party horns. "
    "Vocals must start immediately. Primary vocals strictly follow the traditional, "
    "globally recognized Happy Birthday to You melody and rhythmic phrasing, "
    "transitioning into high-energy dance-pop vocals for the celebration verses and chorus. "
    "Structured full song layout"
)

BIRTHDAY_EDM_PARTY_V3_INSTRUCTION = (
    "Vocals start at second zero — spoken shouted countdown 3-2-1-Go, then a short 4-bar "
    "EDM drop only, then Verse 1 traditional Happy Birthday melody immediately. Do NOT "
    "delay vocals 40 seconds. Do NOT skip the spoken countdown. Follow lyrics section tags "
    "in order. Verse 1 uses the global Happy Birthday tune; verses 2-3 and chorus use "
    "dance-pop energy. Pronounce the birthday name clearly."
)

# Melody anchor strength for text2music + reference (short HB clip).
BIRTHDAY_EDM_MELODY_REFERENCE_STRENGTH = 0.24
BIRTHDAY_EDM_PARTY_V4_REFERENCE_STRENGTH = 0.35
BIRTHDAY_EDM_PARTY_V5_REFERENCE_STRENGTH = 0.45

GENRE_MELODY_REFERENCE_STRENGTH: dict[str, float] = {
    "birthday_edm_party_v3": BIRTHDAY_EDM_MELODY_REFERENCE_STRENGTH,
    "birthday_edm_party_v4": BIRTHDAY_EDM_PARTY_V4_REFERENCE_STRENGTH,
    "birthday_edm_party_v5": BIRTHDAY_EDM_PARTY_V5_REFERENCE_STRENGTH,
}

# Per-genre melody blueprint (text2music reference_audio).
GENRE_MELODY_REFERENCE_FILE: dict[str, str] = {
    "birthday_edm_party_v3": "For HAPPY (Name) Birthday Song Happy Birthday to You.mp3",
    "birthday_edm_party_v4": "For HAPPY (Name) Birthday Song Happy Birthday to You.mp3",
    "birthday_edm_party_v5": "Happy Birthday Viraj (2).mp3",
}

DEFAULT_MELODY_REFERENCE_FILE = "For HAPPY (Name) Birthday Song Happy Birthday to You.mp3"

_BIRTHDAY_EDM_PARTY_V4_CAPTION = (
    "128 BPM festival EDM dance-pop, celebratory birthday party atmosphere, heavy "
    "four-on-the-floor kick drum, bright commercial synths. Clear, expressive Indian "
    "female solo vocalist singing with crisp English pronunciation. Main song and vocals "
    "must start immediately at 0:02 right after the countdown. Vocalist strictly delivers "
    "the traditional, globally recognized Happy Birthday to You melody with its authentic "
    "rhythmic phrasing, smoothly transitioning into high-energy dance-pop vocals for "
    "the celebration verses"
)

BIRTHDAY_EDM_PARTY_V4_INSTRUCTION = (
    "Two-second riser then shouted 3-2-1-Go. At 0:02 start Verse 1 immediately — EDM "
    "festival drop AND traditional Happy Birthday vocal melody in the same section. "
    "No separate instrumental drop block. Indian female solo vocalist. Each Happy "
    "Birthday line uses the globally sung universal birthday tune pitch. Verses 2-3 "
    "and chorus use dance-pop energy. Pronounce the birthday name clearly."
)

_BIRTHDAY_EDM_PARTY_V5_CAPTION = (
    "128 BPM energetic electronic dance-pop, festive birthday celebration atmosphere, "
    "four-on-the-floor kick drum, bright synthesizers, crowd claps. Solo Indian female "
    "vocalist with crisp English pronunciation. Crucial structural instruction: The main "
    "song and vocals must start immediately at 0:02 after a short countdown. When singing "
    "the traditional Happy Birthday lines, the vocalist must NOT sing an EDM pop hook; "
    "instead, she must sing it like a normal human group-singalong at a birthday party, "
    "perfectly following the globally recognized traditional birthday melody. The verses "
    "and choruses shift into a high-energy dance-pop vocal style over the heavy "
    "electronic beat"
)

BIRTHDAY_EDM_PARTY_V5_INSTRUCTION = (
    "Short countdown then vocals at 0:02. Verse 1 Happy Birthday lines: natural human "
    "party singalong melody — NOT auto-tuned EDM pop hook, NOT diva vocal runs. EDM beat "
    "underneath only. Verses 2-4 and choruses: dance-pop vocal energy. Indian female solo. "
    "Pronounce the birthday name clearly. Follow clean lyric sections in order."
)

# Fixed English countdown — never localized.
INTRO_COUNTDOWN_EN = "3! 2! 1! Go!"

CELEBRATEVIBES_V2_INTRO_CAPTION = (
    "128 BPM energetic electronic dance-pop, festive birthday celebration atmosphere, "
    "heavy four-on-the-floor kick drum, bright synthesizers, crowd claps. Solo Indian "
    "female vocalist with crisp English pronunciation singing a short festival countdown. "
    "The vocalist must sing 3, 2, 1, Go on the beat — NOT spoken robotically. High-energy "
    "electronic dance music throughout. NOT ballad, NOT slow"
)

CELEBRATEVIBES_V2_INTRO_INSTRUCTION = (
    "Sing the countdown on beat over a steady EDM kick: 3! 2! 1! Go! One count per "
    "downbeat at 128 BPM. Bright female party vocal, not monotone TTS. Keep only the "
    "countdown section — no Happy Birthday melody yet. Follow the Intro lyrics exactly."
)

# v6: performance-score prompting — text-only HB is best-effort; see MELODY_CONDITIONED_NOTE.
MELODY_CONDITIONED_NOTE = (
    "For guaranteed traditional Happy Birthday melody, use reference-audio cover or "
    "Gradio Repaint on the Opening section — text prompts alone cannot lock famous melodies."
)

_BIRTHDAY_EDM_PARTY_V6_RESTORE_CAPTION = (
    "High-energy 128 BPM festival EDM anthem. The song opens with the traditional global "
    "Happy Birthday to You melody sung exactly once by a bright Indian female lead while "
    "the instrumental already plays an uplifting four-on-the-floor EDM groove. Do NOT "
    "improvise the opening melody. No alternate tune. No melodic variation on the opening. "
    "Immediately after the final line, drum fill and riser, then explode into an original "
    "festival EDM drop. Only the opening birthday verse uses the familiar worldwide melody. "
    "Everything after the drop is entirely original — catchy hooks, energetic synths, "
    "uplifting festival vibes. English countdown at 0:02. NOT ballad, NOT slow"
)

_BIRTHDAY_EDM_PARTY_V6_RESTORE_CAPTION_HI = (
    "High-energy 128 BPM festival EDM anthem. English countdown intro. Opening: traditional "
    "global Happy Birthday to You melody sung exactly once in English with the name — bright "
    "Indian female lead, steady EDM kick underneath, crowd claps on beats 2 and 4. Do NOT "
    "invent a new melody for the opening. No improvisation. After the final line, drum riser "
    "into massive festival drop. Verse 2 onward: completely original melody and Hindi lyrics, "
    "NOT Happy Birthday tune. Outro: emotional layered chorus with EDM elements"
)

BIRTHDAY_EDM_PARTY_V6_INSTRUCTION = (
    "ACT 1 — OPENING (~20 seconds): universally recognizable birthday sing-along. Sound like "
    "a crowd singing the classic Happy Birthday melody over modern four-on-the-floor EDM. "
    "Sing the traditional four lines exactly once. No melodic variation. No improvisation. "
    "No vocal riffs. No melisma. No harmony changes on the opening. Pronounce the name clearly. "
    "ACT 2 — TRANSITION: after the final 'Happy birthday to you', drum fill and riser into a "
    "massive festival EDM drop. ACT 3 — ORIGINAL SONG: everything after the drop is brand-new "
    "melody and lyrics only. Catchy festival hooks. NOT Happy Birthday tune. Outro: emotional "
    "final chorus with layered vocals."
)

_BIRTHDAY_EDM_PARTY_V7_CAPTION = (
    "Professional commercial 128 BPM festival EDM birthday anthem. Open immediately with a "
    "strong four-on-the-floor EDM groove. First vocal: classic worldwide Happy Birthday "
    "sing-along sung exactly once — simple, clean, memorable. No vocal runs, freestyle, rap, "
    "spoken words or ad-libs on the opening. Short drum riser after the final line, then "
    "explode into a huge emotional festival drop — big supersaws, wide stereo synths, punchy "
    "kick, powerful bass, Tomorrowland commercial dance-pop energy. From the drop onward: "
    "entirely original melody and supplied lyrics only. Radio-ready, YouTube-ready, uplifting "
    "major-key finish. NOT ballad, NOT slow"
)

_BIRTHDAY_EDM_PARTY_V7_CAPTION_HI = (
    "Professional commercial 128 BPM festival EDM birthday anthem. Strong EDM groove from "
    "beat one. Opening vocal: classic worldwide Happy Birthday in English with the name — "
    "exactly one verse, simple and clean. No ad-libs or spoken words on opening. Drum riser "
    "into massive festival drop. Verse 2 onward: original melody with Hindi lyrics. Emotional "
    "final chorus with name. Commercial radio-ready mix"
)

BIRTHDAY_EDM_PARTY_V7_INSTRUCTION = (
    "You are producing a professional commercial birthday song. The song must feel like a "
    "modern international EDM festival anthem while remaining emotional, joyful and easy for "
    "everyone to sing. ACT 1 — Birthday Sing-Along: Open immediately with a strong EDM groove. "
    "The very first vocal section is the classic worldwide birthday sing-along. The singer "
    "performs only one complete Happy Birthday verse before any original composition begins. "
    "Keep this opening simple, clean and memorable. No vocal runs. No freestyle. No rap. No "
    "spoken words. No ad-libs. No melodic variations during the opening birthday verse. The "
    "rhythm should remain natural while fitting the EDM beat. Immediately after the final "
    "Happy Birthday to you, begin a short drum riser. ACT 2 — Festival Drop: After the riser, "
    "explode into a huge emotional festival EDM drop. Big supersaws. Wide stereo synths. "
    "Punchy kick. Powerful bass. Bright uplifting energy. This drop should feel like "
    "Tomorrowland, Ultra Music Festival and modern commercial dance-pop. ACT 3 — Original "
    "Birthday Song: From this point onward, compose an entirely original melody. Never reuse "
    "the birthday melody again. Continue with the supplied Hindi verses and chorus. The chorus "
    "should be catchy, energetic and easy for friends and family to sing together. Alternate "
    "naturally between verses, chorus and instrumental fills. ENDING: Finish with an emotional "
    "final chorus. Repeat the person's name naturally. End on a strong uplifting major chord "
    "with festival energy. The overall production should sound polished, commercial, "
    "radio-ready and suitable for YouTube birthday videos."
)

CELEBRATEVIBES_V2_VERSE1_COVER_CAPTION = (
    "Traditional worldwide Happy Birthday to You melody, bright female lead, clean party "
    "sing-along, light hand claps, warm commercial studio mix. Preserve the exact source "
    "melody and rhythm. Only the name changes."
)

CELEBRATEVIBES_V2_VERSE1_COVER_INSTRUCTION = (
    "Cover the deterministic source stem. Keep the exact traditional Happy Birthday melody "
    "and phrasing from the source. Sing the supplied lyrics to that same tune. Vocals must "
    "start immediately at second zero — no instrumental intro. Only the name changes. "
    "Pronounce the birthday name exactly as instructed. No ad-libs. No spoken words."
)

CELEBRATEVIBES_V2_BODY_CAPTION = (
    "128 BPM festival EDM birthday party anthem continuation after Happy Birthday, pumping "
    "sidechain bass, bright supersaw drop, crowd hey-hey chants, commercial dance-pop, "
    "catchy English singalong chorus with the name, NOT the traditional Happy Birthday melody, "
    "radio-ready YouTube birthday song"
)

CELEBRATEVIBES_V2_FULL_CAPTION = (
    "Professional commercial 128 BPM festival EDM birthday anthem. Four-on-the-floor kick drum "
    "and bright synths from beat one. Open with a short 2-3 second instrumental party hook — "
    "no vocals, no countdown. Then one classic Happy Birthday verse sung over the dance beat. "
    "Then original festival EDM party lyrics driven by the beat throughout. "
    "NOT ballad, NOT slow, NOT waltz, NOT spoken countdown"
)

CELEBRATEVIBES_V2_BODY_INSTRUCTION = (
    "This is the party section AFTER the traditional Happy Birthday verse. Explode into a "
    "huge festival EDM drop. Use an entirely original melody; never use the traditional "
    "Happy Birthday to You tune here. Keep words simple and birthday-specific. Repeat the "
    "person's name in the chorus with correct pronunciation. No long instrumental buildup "
    "before vocals — party vocals within the first 4 seconds of this section."
)

CELEBRATEVIBES_V2_FULL_INSTRUCTION = (
    "Single-pass festival EDM birthday song. NO countdown. NO spoken 3-2-1-Go. NO separate "
    "instrumental buildup longer than 3 seconds. Structure: (1) Beat starts immediately — "
    "2-3 second instrumental EDM intro hook only, no vocals. (2) One complete traditional "
    "Happy Birthday verse sung over the four-on-the-floor beat — classic worldwide melody, "
    "no improvisation, no ad-libs. (3) Short drum riser then festival drop into original "
    "party lyrics — entirely new melody, beat-driven throughout. Pronounce the birthday name "
    "clearly on every Happy Birthday line and in the chorus."
)

# Legacy aliases kept for tests / older imports.
CELEBRATEVIBES_V2_VOCAL_CAPTION = CELEBRATEVIBES_V2_VERSE1_COVER_CAPTION
CELEBRATEVIBES_V2_VOCAL_INSTRUCTION = CELEBRATEVIBES_V2_VERSE1_COVER_INSTRUCTION
CELEBRATEVIBES_V2_EDM_COVER_CAPTION = CELEBRATEVIBES_V2_VERSE1_COVER_CAPTION
CELEBRATEVIBES_V2_EDM_COVER_INSTRUCTION = CELEBRATEVIBES_V2_VERSE1_COVER_INSTRUCTION

CELEBRATEVIBES_V2_GENRES = frozenset({"celebratevibes_v2"})

EDM_BIRTHDAY_GENRES = frozenset(
    {
        "birthday_edm_party_v1",
        "birthday_edm_party_v2",
        "birthday_edm_party_v3",
        "birthday_edm_party_v4",
        "birthday_edm_party_v5",
        "birthday_edm_party_v6_restore",
        "birthday_edm_party_v7",
    }
)

# Pure text2music — never attach global reference_audio or user template.
NO_MELODY_REFERENCE_GENRES = frozenset(
    {"birthday_edm_party_v6_restore", "birthday_edm_party_v7", "celebratevibes_v2"}
)
MELODY_FIRST_BIRTHDAY_GENRES = BIRTHDAY_ANTHEM_GENRES | CLASSIC_BIRTHDAY_GENRES
VOCAL_FORWARD_BIRTHDAY_GENRES = MELODY_FIRST_BIRTHDAY_GENRES | EDM_BIRTHDAY_GENRES

GENRE_CAPTIONS: dict[str, str] = {
    "party_dance": _PARTY_DANCE_CAPTION,
    "party_dance_intro": _PARTY_DANCE_INTRO_CAPTION,
    "party_dance_body": _PARTY_DANCE_BODY_CAPTION,
    "song_cover": _SONG_COVER_CAPTION,
    "song_guitar_cover": _GUITAR_COVER_CAPTION,
    "birthday_anthem_female_choir": _BIRTHDAY_ANTHEM_FEMALE_CHOIR_CAPTION,
    "birthday_anthem_male_choir": _BIRTHDAY_ANTHEM_MALE_CHOIR_CAPTION,
    "birthday_anthem_female": _BIRTHDAY_ANTHEM_FEMALE_CAPTION,
    "birthday_classic_extended": _BIRTHDAY_CLASSIC_EXTENDED_CAPTION,
    "birthday_restaurant_party_v1": _BIRTHDAY_RESTAURANT_PARTY_CAPTION,
    "birthday_edm_party_v1": _BIRTHDAY_EDM_PARTY_CAPTION,
    "birthday_edm_party_v2": _BIRTHDAY_EDM_PARTY_V2_CAPTION,
    "birthday_edm_party_v3": _BIRTHDAY_EDM_PARTY_V3_CAPTION,
    "birthday_edm_party_v4": _BIRTHDAY_EDM_PARTY_V4_CAPTION,
    "birthday_edm_party_v5": _BIRTHDAY_EDM_PARTY_V5_CAPTION,
    "birthday_edm_party_v6_restore": _BIRTHDAY_EDM_PARTY_V6_RESTORE_CAPTION,
    "birthday_edm_party_v7": _BIRTHDAY_EDM_PARTY_V7_CAPTION,
    "celebratevibes_v2": CELEBRATEVIBES_V2_BODY_CAPTION,
    "user_template_cover": (
        f"Happy Birthday to You song like the reference recording, traditional birthday melody, "
        f"{_DUET_VOCAL_HINT}, piano, hand claps, festive party, professional studio mix, "
        f"personalized birthday song with clear sung name, joyful sing-along"
    ),
    "edm_party_anthem": (
        "upbeat birthday celebration song, worldwide party atmosphere, "
        "Dance Pop EDM party anthem, joyful festive energetic cheerful family-friendly, "
        "piano, bright synths, hand claps, crowd chants, dance drums, bass, party FX, "
        "confetti-style risers, group vocals male and female singers, "
        "modern commercial pop, stadium-sized energy, festival-ready mix, "
        "extremely catchy singalong chorus, universal birthday celebration anthem, "
        "original memorable melody, NOT Happy Birthday to You, NOT traditional birthday tune"
    ),
    "happy_birthday_fast": (
        f"Happy Birthday to You song, {_MELODY_HINT}, upbeat 3/4 waltz birthday party, "
        f"{_VOCAL_HINT}, {_PRODUCTION_HINT}, joyful sing-along, festive celebration"
    ),
    "indian_birthday": (
        f"Indian birthday party song, {_MELODY_HINT}, {_VOCAL_HINT}, {_PRODUCTION_HINT}, "
        "festive family gathering"
    ),
    "pop_party": (
        f"birthday party pop song, {_MELODY_HINT}, {_VOCAL_HINT}, {_PRODUCTION_HINT}, uplifting"
    ),
    "bollywood_warm": (
        f"birthday song, {_MELODY_HINT}, {_VOCAL_HINT}, {_PRODUCTION_HINT}, festive"
    ),
    "acoustic_warm": (
        f"acoustic birthday song, {_MELODY_HINT}, {_VOCAL_HINT}, "
        "professional acoustic guitar and piano, warm strings, polished studio mix"
    ),
    "latin_pop": (
        f"birthday song, {_MELODY_HINT}, {_VOCAL_HINT}, {_PRODUCTION_HINT}, percussion, joyful"
    ),
    "mandarin_pop": (
        f"birthday song, {_MELODY_HINT}, {_VOCAL_HINT}, {_PRODUCTION_HINT}, celebratory"
    ),
}

# Genres using classic Happy Birthday lyrics structure.
TRADITIONAL_GENRES = frozenset(
    {"happy_birthday_fast", "indian_birthday", "pop_party", "bollywood_warm", "acoustic_warm"}
)
# Cover mode skips LM → instrumental only. Opt-in via --cover only.
TRADITIONAL_COVER_GENRES = TRADITIONAL_GENRES
TRADITIONAL_COVER_STRENGTH = 0.68

# Hybrid edit segment lengths (seconds).
HYBRID_INTRO_SEC = 45
HYBRID_BODY_SEC = 195
HYBRID_CROSSFADE_SEC = 2.5
# Melody hint strength when user template is used on intro only (lower = clearer vocals).
HYBRID_INTRO_REFERENCE_STRENGTH = 0.32
HYBRID_VOCAL_INSTRUCTION = (
    "Sing every lyric line clearly and prominently. Lead vocal must be loud, "
    "upfront, and easy to understand. Pronounce the name clearly."
)

# Verses needed to fill ~240s at 132 BPM (classic phrase + blessing chorus).
_TEXT2MUSIC_VERSE_COUNT = 8


def genre_time_signature(genre_variant: str) -> str:
    """Return ACE-Step time_signature for a genre variant."""
    return GENRE_TIME_SIGNATURE.get(genre_variant, DEFAULT_TIME_SIGNATURE)


def genre_duration_sec(genre_variant: str, default: int = 240) -> int:
    """Return target duration for a genre variant, or *default* if unset."""
    return GENRE_DURATION_SEC.get(genre_variant, default)


def resolve_melody_reference_file(genre_variant: str, batch_root: Path) -> Path | None:
    """Return path to genre-specific melody blueprint MP3, if present."""
    filename = GENRE_MELODY_REFERENCE_FILE.get(genre_variant, DEFAULT_MELODY_REFERENCE_FILE)
    path = batch_root / "templates" / "audio" / filename
    return path if path.exists() else None


def apply_personalization(
    text: str,
    *,
    name: str,
    age: str = "",
    city: str = "",
    hobby: str = "",
    relationship: str = "",
) -> str:
    """Replace ${Name} / [NAME] and optional CSV placeholders in lyric templates."""
    replacements = {
        "${Name}": name,
        "[NAME]": name,
        "${Age}": age,
        "${City}": city,
        "${Hobby}": hobby,
        "${Relationship}": relationship,
    }
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text


def build_lyrics(
    name: str,
    language: str = "en",
    *,
    genre_variant: str = "happy_birthday_fast",
    section: str | None = None,
    country: str = "",
    age: str = "",
    city: str = "",
    hobby: str = "",
    relationship: str = "",
) -> str:
    """Return ACE-Step lyrics for the requested genre and language."""
    if genre_variant == "birthday_edm_party_v5":
        return _lyrics_birthday_edm_party_v5(
            name,
            age=age,
            city=city,
            hobby=hobby,
            relationship=relationship,
        )
    if genre_variant == "birthday_edm_party_v6_restore":
        return _lyrics_birthday_edm_party_v6_restore(
            name,
            language=language,
            age=age,
            city=city,
            hobby=hobby,
            relationship=relationship,
        )
    if genre_variant == "birthday_edm_party_v7":
        return _lyrics_birthday_edm_party_v7(
            name,
            language=language,
            age=age,
            city=city,
            hobby=hobby,
            relationship=relationship,
        )
    if genre_variant == "celebratevibes_v2":
        return build_full_song_lyrics(name, language, variant=0, country=country)
    if genre_variant == "birthday_edm_party_v4":
        return _lyrics_birthday_edm_party_v4(
            name,
            age=age,
            city=city,
            hobby=hobby,
            relationship=relationship,
        )
    if genre_variant == "birthday_edm_party_v3":
        return _lyrics_birthday_edm_party_v3(
            name,
            age=age,
            city=city,
            hobby=hobby,
            relationship=relationship,
        )
    if genre_variant == "birthday_edm_party_v2":
        return _lyrics_birthday_edm_party_v2(
            name,
            age=age,
            city=city,
            hobby=hobby,
            relationship=relationship,
        )
    if genre_variant == "birthday_edm_party_v1":
        return _lyrics_birthday_edm_party(
            name,
            age=age,
            city=city,
            hobby=hobby,
            relationship=relationship,
        )
    if genre_variant == "birthday_restaurant_party_v1":
        return _lyrics_birthday_restaurant_party(
            name,
            age=age,
            city=city,
            hobby=hobby,
            relationship=relationship,
        )
    if genre_variant == "birthday_classic_extended":
        return _lyrics_birthday_classic_extended(
            name,
            age=age,
            city=city,
            hobby=hobby,
            relationship=relationship,
        )
    if genre_variant in BIRTHDAY_ANTHEM_GENRES:
        return _lyrics_birthday_anthem(
            name,
            age=age,
            city=city,
            hobby=hobby,
            relationship=relationship,
        )
    if genre_variant in ("song_cover", "song_guitar_cover"):
        return _lyrics_jaaniya()
    if genre_variant in ("party_dance", "party_dance_intro", "party_dance_body"):
        if section == "intro" or genre_variant == "party_dance_intro":
            return _lyrics_party_dance_intro(name)
        if section == "body" or genre_variant == "party_dance_body":
            return _lyrics_party_dance_body(name)
        return _lyrics_party_dance_hybrid_full(name)
    if genre_variant == "edm_party_anthem":
        return _lyrics_edm_party(name)
    if genre_variant == "user_template_cover":
        return _lyrics_duet_traditional(name, language)
    if genre_variant in TRADITIONAL_GENRES:
        return _lyrics_traditional(name, language)
    builders = {
        "en": _lyrics_en,
        "es": _lyrics_es,
        "hi": _lyrics_hi,
        "zh": _lyrics_zh,
    }
    builder = builders.get(language, _lyrics_en)
    return builder(name.strip())


def genre_caption(genre: str, language: str = "en") -> str:
    """Return ACE-Step caption for genre, with optional language variant."""
    if genre == "birthday_edm_party_v6_restore" and language == "hi":
        return _BIRTHDAY_EDM_PARTY_V6_RESTORE_CAPTION_HI
    if genre == "birthday_edm_party_v7" and language == "hi":
        return _BIRTHDAY_EDM_PARTY_V7_CAPTION_HI
    if genre == "celebratevibes_v2" and language == "hi":
        return (
            f"{CELEBRATEVIBES_V2_FULL_CAPTION} "
            "Verse 1 uses fixed English Happy Birthday melody; body uses English party hooks."
        )
    if genre == "celebratevibes_v2":
        return CELEBRATEVIBES_V2_FULL_CAPTION
    return GENRE_CAPTIONS.get(genre, GENRE_CAPTIONS["happy_birthday_fast"])


def _classic_four_lines_hi(name: str) -> str:
    """Traditional Happy Birthday lines in Hindi."""
    return f"""जन्मदिन की शुभकामनाएँ
जन्मदिन की शुभकामनाएँ
जन्मदिन मुबारक हो {name}
जन्मदिन की शुभकामनाएँ"""


def _classic_four_lines(name: str) -> str:
    return f"""Happy birthday to you
Happy birthday to you
Happy birthday dear {name}
Happy birthday to you"""


def build_intro_lyrics() -> str:
    """Countdown intro — one line per count for tight timing."""
    return "[Intro]\n3!\n2!\n1!\nGo!"


def build_verse1_lyrics(name: str) -> str:
    """Verse 1 vocal lyrics — pure traditional Happy Birthday (name personalized)."""
    classic = _classic_four_lines(name.strip())
    return f"[Verse 1]\n{classic}"


def build_verse1_intro_lyrics(name: str) -> str:
    """Full opening section lyrics (intro + verse1) for sidecar documentation."""
    return f"{build_intro_lyrics()}\n\n{build_verse1_lyrics(name)}"


def build_full_song_lyrics(
    name: str,
    language: str = "en",
    *,
    variant: int = 0,
    country: str = "",
) -> str:
    """Single-pass EDM song: short intro tune → Happy Birthday → party body."""
    clean = name.strip()
    classic = _classic_four_lines(clean)
    if country.strip().lower() in ("india", "russia", "china"):
        pron = resolve_pronunciation(clean, country)
        body = build_native_body_lyrics(
            clean,
            country,
            variant=variant,
            native_name=pron.native_script,
            language=language,
        )
    else:
        body = build_body_lyrics(clean, language, variant=variant)
    intro = "[Intro]\n[Instrumental]"
    verse1 = f"[Verse 1]\n{classic}"
    build = "[Build]\n[Instrumental]"
    drop = "[Drop]\n[Instrumental]"
    return f"{intro}\n\n{verse1}\n\n{build}\n\n{drop}\n\n{body}"


def _classic_to_you_four_lines() -> str:
    """Traditional Happy Birthday melody with no personal name."""
    return """Happy birthday to you
Happy birthday to you
Happy birthday to you
Happy birthday to you"""


def build_generic_body_lyrics(*, variant: int = 0) -> str:
    """EDM party body with no personal name — for channel intro / universal uploads."""
    variant = variant % 2
    if variant == 0:
        verse2 = """Everybody jump, the lights go wild
Tonight you're the star so bright
Candles glow and friends all smile
We dance until the morning light"""
        chorus = """Happy birthday to you, put your hands up high
Happy birthday to you, touch the sky
Hey! Hey! Happy birthday to you
Let's party all night"""
        verse3 = """Make a wish and blow the flame
Hear the crowd call out your name
Laughing, singing, hearts on fire
This is your moment, take it higher"""
        verse4 = """One more time now, all together
Louder, louder, feel the beat
We celebrate this special day
Dancing down the city street"""
    else:
        verse2 = """DJ drop the beat, the crowd goes wild
Neon lights and happy smiles
We party till the morning light
Celebrate with joy tonight"""
        chorus = """Happy birthday to you, hands up to the sky
Happy birthday to you, feel the vibe
Oh oh, happy birthday to you
Party all night"""
        verse3 = """Blow the candles, make it count
Every voice joins in the sound
Friends around from left to right
Sparklers glowing in the night"""
        verse4 = """Turn it up and sing along
Birthday wishes in this song
Clap your hands and feel the groove
Here's a day we all can prove"""
    return (
        f"[Verse 2]\n{verse2}\n\n[Chorus]\n{chorus}\n\n"
        f"[Verse 3]\n{verse3}\n\n[Verse 4]\n{verse4}\n\n"
        f"[Final Chorus]\n{chorus}\nHappy birthday to you!"
    )


def build_generic_full_song_lyrics(*, variant: int = 0) -> str:
    """Single-pass EDM song: Verse 1 HB first, then drop, then party body.

    Lyrics contain only singable lines and standard section tags — timing and
    performance notes belong in the ACE-Step caption/instruction fields only.
    """
    classic = _classic_to_you_four_lines()
    body = build_generic_body_lyrics(variant=variant)
    verse1 = f"[Verse 1]\n{classic}"
    drop = "[Drop]\n[Instrumental]"
    return f"{verse1}\n\n{drop}\n\n{body}"


def build_body_lyrics(name: str, language: str = "en", *, variant: int = 0) -> str:
    """Festival EDM party body — English hooks with rotating templates."""
    clean = name.strip()
    variant = variant % 4

    if variant == 0:
        verse2 = f"""Everybody jump, the lights go wild
{clean}, you're the star tonight
Candles glow and friends all smile
We dance until the morning light"""
        chorus = f"""Happy birthday {clean}, put your hands up high
Happy birthday {clean}, touch the sky
Hey! Hey! Happy birthday {clean}
Let's party all night"""
        verse3 = f"""Make a wish and blow the flame
{clean}, hear us call your name
Laughing, singing, hearts on fire
This is your moment, take it higher"""
        verse4 = f"""One more time now, all together
Louder, louder, feel the beat
{clean}, we celebrate you
Dancing down the city street"""
    elif variant == 1:
        verse2 = f"""DJ drop the beat, the crowd goes wild
{clean}, you're shining bright tonight
Neon lights and happy smiles
We party till the morning light"""
        chorus = f"""Happy birthday {clean}, hands up to the sky
Happy birthday {clean}, let the good times fly
Hey! Hey! Happy birthday {clean}
Dance with me tonight"""
        verse3 = f"""Blow the candles, make it count
{clean}, hear the music loud
Singing, jumping, feeling free
This night belongs to you and me"""
        verse4 = f"""Turn it up and sing along
Feel the bass and move your feet
{clean}, this is your birthday song
Dancing down the city street"""
    elif variant == 2:
        verse2 = f"""Spotlight on you, the room ignites
{clean}, you're the hero of the night
Friends around and joy so bright
We rave until the morning light"""
        chorus = f"""Happy birthday {clean}, jump into the sky
Happy birthday {clean}, let the sparks fly high
Hey! Hey! Happy birthday {clean}
Party all night long"""
        verse3 = f"""Wish upon the candle glow
{clean}, let the whole world know
Singing loud with hearts on fire
Take your dreams a little higher"""
        verse4 = f"""Hands up high and sing out strong
Feel the rhythm in your feet
{clean}, we cheer you all night long
Grooving down the city street"""
    else:
        verse2 = f"""Festival lights and bass so loud
{clean}, you're the star of the crowd
Smiles and cheers from every side
We dance with festival pride"""
        chorus = f"""Happy birthday {clean}, reach up to the sky
Happy birthday {clean}, let the moment fly
Hey! Hey! Happy birthday {clean}
Celebrate tonight"""
        verse3 = f"""Make a wish and feel the flame
{clean}, we shout your name
Laughing loud with hearts on fire
This is your hour, take it higher"""
        verse4 = f"""One more chorus, all as one
Louder now and feel the heat
{clean}, your party has begun
Moving down the city street"""

    outro = f"""Happy birthday {clean}
Happy birthday {clean}
We love you, never stop the cheer
Happy birthday {clean}"""

    return f"""[Verse 2]
{verse2}

[Chorus]
{chorus}

[Verse 3]
{verse3}

[Chorus]
{chorus}

[Verse 4]
{verse4}

[Chorus]
{chorus}

[Outro]
{outro}"""


def _opening_traditional_hb_performance_score(name: str) -> str:
    """Opening performance score — single classic HB refrain with explicit constraints."""
    classic = _classic_four_lines(name)
    return f"""[Opening - Traditional Happy Birthday Melody]

Tempo: 128 BPM. Festival EDM instrumental begins immediately — steady four-on-the-floor kick.

Performance:
- Bright female lead vocal.
- The opening MUST be performed exactly like the traditional worldwide Happy Birthday song
  that children sing at birthday parties.
- Do NOT invent a new melody. Do NOT improvise. Do NOT use an alternate tune.
- Follow the classic four-line birthday melody before transitioning into original EDM.
- Children's choir joins softly on line 3 (name line).
- Crowd claps on beats 2 and 4.
- No vocal riffs. No melisma. No harmony changes on the opening.
- Maintain the familiar rhythm and phrasing used at birthday celebrations worldwide.
- Classic birthday melody sung exactly once — then transition to original composition.

Lyrics:
{classic}"""


def _opening_v7_birthday_singalong(name: str) -> str:
    """ACT 1 opening — one classic HB verse over immediate EDM groove."""
    classic = _classic_four_lines(name)
    return f"""[ACT 1 - Birthday Sing-Along]

Tempo: 128 BPM. Strong four-on-the-floor EDM groove starts immediately.

Performance:
- Bright lead vocal.
- Sing one complete classic worldwide Happy Birthday verse.
- Simple, clean, memorable.
- No vocal runs. No freestyle. No rap. No spoken words. No ad-libs.
- No melodic variations during the opening birthday verse.
- Natural rhythm fitting the EDM beat. Pronounce the name clearly.

Lyrics:
{classic}"""


def _hb_refrain_block(name: str, tag: str) -> str:
    """Two back-to-back traditional Happy Birthday phrases."""
    classic = _classic_four_lines(name)
    return f"[{tag} - traditional Happy Birthday melody, choir singalong]\n{classic}\n\n{classic}"


def _sung_traditional_hb_lines(name: str) -> str:
    """Happy Birthday lines with pitch-tracking cue for ACE-Step LM."""
    cue = "(sung to traditional universal birthday tune) "
    return (
        f"{cue}Happy birthday to you\n"
        f"{cue}Happy birthday to you\n"
        f"{cue}Happy birthday dear {name}\n"
        f"{cue}Happy birthday to you"
    )


def _outro_variant_for_name(name: str) -> str:
    """Pick a deterministic outro lyric block — same structure, unique fingerprint per name."""
    clean = name.strip()
    digest = hashlib.sha256(clean.lower().encode("utf-8")).digest()
    idx = digest[0] % 6
    outros = (
        f"Happy birthday dear {clean}\nWe celebrate with you\n"
        f"Happy birthday dear {clean}\nMay all your dreams come true",
        f"Happy birthday dear {clean}\nTonight we dance for you\n"
        f"Happy birthday dear {clean}\nShine bright the whole year through",
        f"Happy birthday dear {clean}\nThe party's here for you\n"
        f"Happy birthday dear {clean}\nMay joy surround you too",
        f"Happy birthday dear {clean}\nWe sing this song for you\n"
        f"Happy birthday dear {clean}\nMay blessings follow through",
        f"Happy birthday dear {clean}\nRaise your voice and cheer\n"
        f"Happy birthday dear {clean}\nAnother happy year",
        f"Happy birthday dear {clean}\nWith love from everyone\n"
        f"Happy birthday dear {clean}\nUntil the night is done",
    )
    return outros[idx]


def _outro_variant_hi_for_name(name: str) -> str:
    """Hindi outro variants — unique per name."""
    clean = name.strip()
    digest = hashlib.sha256(clean.lower().encode("utf-8")).digest()
    idx = digest[0] % 4
    outros = (
        f"जन्मदिन मुबारक हो {clean}\nहम सब मिलकर गाएँ\n"
        f"जन्मदिन मुबारक हो {clean}\nखुशियाँ हमेशा साथ रहें",
        f"जन्मदिन मुबारक हो {clean}\nआज की रात तुम्हारी है\n"
        f"जन्मदिन मुबारक हो {clean}\nहर दिन रोशन रहे",
        f"जन्मदिन मुबारक हो {clean}\nप्यार भरा यह पल\n"
        f"जन्मदिन मुबारक हो {clean}\nसपने सच हो जाएँ",
        f"जन्मदिन मुबारक हो {clean}\nसबकी दुआएँ साथ हैं\n"
        f"जन्मदिन मुबारक हो {clean}\nखुशियों भरा साल",
    )
    return outros[idx]


def _lyrics_birthday_edm_party_v6_restore(
    name: str,
    *,
    language: str = "en",
    age: str = "",
    city: str = "",
    hobby: str = "",
    relationship: str = "",
) -> str:
    """~165s EDM v6 — performance-score opening, drop, original festival body."""
    opening = _opening_traditional_hb_performance_score(name)
    build = (
        "[Build - Transition After Opening]\n"
        "After the final 'Happy birthday to you', begin a drum fill and riser.\n"
        "Rising tension. Energy lift. No new lyrics. Crowd hype: Hey! Hey! Here we go!"
    )
    drop = (
        "[Drop - Massive Festival EDM Drop]\n"
        "Explode into original festival EDM. Heavy kick and bass. Bright synths.\n"
        "Instrumental burst. Confetti energy. From here onward: entirely original melody."
    )
    verse2_tag = (
        "[Verse 2 - Original Festival Composition]\n"
        "Completely original melody and lyrics. Do NOT use Happy Birthday to You tune.\n"
        "Festival dance-pop vocal. Celebrating the birthday."
    )
    verse3_tag = (
        "[Verse 3 - Original Festival Composition]\n"
        "New original melody. Do NOT return to traditional birthday tune."
    )
    verse4_tag = (
        "[Verse 4 - Original Festival Composition]\n"
        "New original melody. Peak party energy before final chorus."
    )
    chorus_tag = (
        "[Chorus - Original Festival Hook]\n"
        "Catchy original festival melody. Energetic synths. Uplifting singalong.\n"
        "Do NOT use Happy Birthday to You tune. Do NOT improvise traditional melody."
    )
    if language == "hi":
        verse2 = """तुम्हारे सपने सच हों
हर दिन नया उजियाला लाए
आज तुम्हारे दिल में हँसी हो
खुशियाँ तुम्हारे संग रहें"""
        chorus = """गाओ मिलकर, जश्न मनाओ
यह है तुम्हारा खास दिन
परिवार और दोस्त इकट्ठे
खुशियाँ बाँटते हैं"""
        verse3 = """खुशियाँ और प्यार मिले
हर पल मुस्कान भरे
भाग्य तुम्हारे संग चले
हर दुआ पूरी हो"""
        verse4 = """संगीत तुम्हें ऊँचा उठाए
चमकें सितारे आसमान में
एक ख्वाहिश करो और मनाओ
सब मिलकर जयकार करें"""
        outro = _outro_variant_hi_for_name(name)
    else:
        verse2 = """May your dreams all come true
May your days be bright and new
May laughter fill your heart today
And happiness stay with you"""
        chorus = """Celebrate and sing along
This is your special day
Friends and family gathered here
To cheer and celebrate"""
        verse3 = """Wishing joy and wishing love
Wishing smiles the whole year through
May good fortune walk beside you
And every wish come through"""
        verse4 = """Let the music lift you high
See the sparks fly to the sky
Make a wish and blow them out
Hear the whole crowd cheer and shout"""
        outro = _outro_variant_for_name(name)

    template = f"""[Intro - English Countdown]
Tempo: 128 BPM. Festival EDM groove starts under countdown.
{INTRO_COUNTDOWN_EN}

{opening}

{build}

{drop}

{verse2_tag}
{verse2}

{chorus_tag}
{chorus}

{verse3_tag}
{verse3}

{chorus_tag}
{chorus}

{verse4_tag}
{verse4}

{chorus_tag}
{chorus}

[Outro - Emotional Final Chorus]
Layered vocals. Harmonies. EDM elements. Original festival melody only.
{chorus_tag}
{chorus}

{outro}

[End]"""
    return apply_personalization(
        template,
        name=name,
        age=age,
        city=city,
        hobby=hobby,
        relationship=relationship,
    )


def _lyrics_birthday_edm_party_v7(
    name: str,
    *,
    language: str = "en",
    age: str = "",
    city: str = "",
    hobby: str = "",
    relationship: str = "",
) -> str:
    """~165s EDM v7 — commercial ACT 1/2/3 structure, no countdown or ad-libs."""
    opening = _opening_v7_birthday_singalong(name)
    build = (
        "[Build - Drum Riser]\n"
        "Immediately after the final 'Happy birthday to you', short drum riser only.\n"
        "Instrumental. No vocals. No ad-libs. No spoken words."
    )
    drop = (
        "[ACT 2 - Festival Drop]\n"
        "Huge emotional festival EDM drop. Big supersaws. Wide stereo synths. Punchy kick.\n"
        "Powerful bass. Bright uplifting energy. Tomorrowland commercial dance-pop feel.\n"
        "Instrumental burst. From here onward: entirely original melody."
    )
    verse2_tag = (
        "[ACT 3 - Verse 2 - Original Birthday Song]\n"
        "Entirely original melody. Do NOT reuse Happy Birthday to You tune.\n"
        "Festival dance-pop vocal. Celebrating the birthday."
    )
    verse3_tag = (
        "[ACT 3 - Verse 3 - Original Birthday Song]\n"
        "New original melody. Do NOT return to traditional birthday tune."
    )
    verse4_tag = (
        "[ACT 3 - Verse 4 - Original Birthday Song]\n"
        "New original melody. Peak party energy before final chorus."
    )
    chorus_tag = (
        "[ACT 3 - Chorus - Original Festival Hook]\n"
        "Catchy original festival melody. Energetic synths. Easy singalong for family.\n"
        "Do NOT use Happy Birthday to You tune."
    )
    if language == "hi":
        verse2 = """तुम्हारे सपने सच हों
हर दिन नया उजियाला लाए
आज तुम्हारे दिल में हँसी हो
खुशियाँ तुम्हारे संग रहें"""
        chorus = """गाओ मिलकर, जश्न मनाओ
यह है तुम्हारा खास दिन
परिवार और दोस्त इकट्ठे
खुशियाँ बाँटते हैं"""
        verse3 = """खुशियाँ और प्यार मिले
हर पल मुस्कान भरे
भाग्य तुम्हारे संग चले
हर दुआ पूरी हो"""
        verse4 = """संगीत तुम्हें ऊँचा उठाए
चमकें सितारे आसमान में
एक ख्वाहिश करो और मनाओ
सब मिलकर जयकार करें"""
        outro = _outro_variant_hi_for_name(name)
    else:
        verse2 = """May your dreams all come true
May your days be bright and new
May laughter fill your heart today
And happiness stay with you"""
        chorus = """Celebrate and sing along
This is your special day
Friends and family gathered here
To cheer and celebrate"""
        verse3 = """Wishing joy and wishing love
Wishing smiles the whole year through
May good fortune walk beside you
And every wish come through"""
        verse4 = """Let the music lift you high
See the sparks fly to the sky
Make a wish and blow them out
Hear the whole crowd cheer and shout"""
        outro = _outro_variant_for_name(name)

    template = f"""{opening}

{build}

{drop}

{verse2_tag}
{verse2}

{chorus_tag}
{chorus}

{verse3_tag}
{verse3}

{chorus_tag}
{chorus}

{verse4_tag}
{verse4}

{chorus_tag}
{chorus}

[Ending - Emotional Final Chorus]
Layered vocals. Harmonies. EDM elements. Original festival melody only.
End on a strong uplifting major chord with festival energy.
{chorus_tag}
{chorus}

{outro}

[End]"""
    return apply_personalization(
        template,
        name=name,
        age=age,
        city=city,
        hobby=hobby,
        relationship=relationship,
    )


def _lyrics_birthday_edm_party_v5(
    name: str,
    *,
    age: str = "",
    city: str = "",
    hobby: str = "",
    relationship: str = "",
) -> str:
    """~150s EDM v5 — clean lyrics, natural HB singalong, extended Verse 4."""
    classic = _classic_four_lines(name)
    verse2 = """May your dreams all come true
May your days be bright and new
May laughter fill your heart today
And happiness stay with you"""

    chorus = """Celebrate and sing along
This is your special day
Friends and family gathered here
To cheer and celebrate"""

    verse3 = """Wishing joy and wishing love
Wishing smiles the whole year through
May good fortune walk beside you
And every wish come true"""

    verse4 = """Let the music lift you high
See the sparks fly to the sky
Make a wish and blow them out
Hear the whole crowd cheer and shout"""

    outro = f"""Happy birthday dear {name}
We celebrate with you
Happy birthday dear {name}
May all your dreams come true"""

    template = f"""[Intro]
3! 2! 1! Go!

[Verse 1]
{classic}

[Verse 2]
{verse2}

[Chorus]
{chorus}

[Verse 3]
{verse3}

[Chorus]
{chorus}

[Verse 4]
{verse4}

[Chorus]
{chorus}

[Outro]
{outro}

[End]"""
    return apply_personalization(
        template,
        name=name,
        age=age,
        city=city,
        hobby=hobby,
        relationship=relationship,
    )


def _lyrics_birthday_edm_party_v4(
    name: str,
    *,
    age: str = "",
    city: str = "",
    hobby: str = "",
    relationship: str = "",
) -> str:
    """~150s EDM v4 — vocals at 0:02, drop merged into Verse 1, Indian female vocal."""
    hb_verse = _sung_traditional_hb_lines(name)
    party_chant = """Hey! Hey! Hey!
Everybody clap your hands!
Hey! Hey! Hey!
Let's celebrate today!"""

    verse2 = """May your dreams all come true
May your days be bright and new
May laughter fill your heart today
And happiness stay with you"""

    chorus = """Celebrate and sing along
This is your special day
Friends and family gathered here
To cheer and celebrate"""

    party_section = """Let's celebrate! (Hey!)
Let's celebrate! (Hey!)
Hip hip hooray!"""

    verse3 = """Wishing joy and wishing love
Wishing smiles the whole year through
May good fortune walk beside you
And every wish come true"""

    cue = "(sung to traditional universal birthday tune) "
    outro = (
        f"{cue}Happy birthday dear {name}\n"
        "We celebrate with you\n"
        f"{cue}Happy birthday dear {name}\n"
        "May all your dreams come true"
    )

    template = f"""[Intro - 2-second high energy electronic riser cue]
(Shouted) 3! 2! 1! Go!

[Verse 1 - Instant 128 BPM EDM Festival Drop, Indian Female Vocalist singing traditional global melody]
{hb_verse}

[Party Chant - Crowd claps and energetic hype chants]
{party_chant}

[Verse 2 - Indian Female Vocalist, high-energy dance-pop melody, rhythmic synth bass]
{verse2}

[Chorus - Massive uplifting EDM festival chorus, crowd singing along]
{chorus}

[Party Section - Hype chants and horn blasts]
{party_section}

[Verse 3 - Indian Female Vocalist, upbeat electronic tempo]
{verse3}

[Chorus - Massive uplifting EDM festival chorus, maximum energy]
{chorus}

[Outro - Final Refrain, traditional melody climax, festival confetti drop, crowd cheering]
{outro}

[End]"""
    return apply_personalization(
        template,
        name=name,
        age=age,
        city=city,
        hobby=hobby,
        relationship=relationship,
    )


def _lyrics_birthday_edm_party_v3(
    name: str,
    *,
    age: str = "",
    city: str = "",
    hobby: str = "",
    relationship: str = "",
) -> str:
    """~150s EDM party v3 — instant vocals, shouted countdown, hardcoded structure."""
    classic = _classic_four_lines(name)
    party_chant = """Hey! Hey! Hey!
Everybody clap your hands!
Hey! Hey! Hey!
Let's celebrate today!"""

    verse2 = """May your dreams all come true
May your days be bright and new
May laughter fill your heart today
And happiness stay with you"""

    chorus = """Celebrate and sing along
This is your special day
Friends and family gathered here
To cheer and celebrate"""

    party_section = """Let's celebrate! (Hey!)
Let's celebrate! (Hey!)
Hip hip hooray!"""

    verse3 = """Wishing joy and wishing love
Wishing smiles the whole year through
May good fortune walk beside you
And every wish come true"""

    outro = f"""Happy birthday dear {name}
We celebrate with you
Happy birthday dear {name}
May all your dreams come true"""

    template = f"""[Intro - High energy electronic build-up, rising synth sweep]
(Shouted) 3!
(Shouted) 2!
(Shouted) 1!
(All) Go!

[Short EDM Drop - Heavy 128 BPM festival dance beat, bright lead synths, party horns]

[Verse 1 - Traditional Global Happy Birthday Melody and Phrasing, direct vocal entry]
{classic}

[Party Chant - Crowd claps and hype chants synchronized to the beat]
{party_chant}

[Verse 2 - Energetic dance-pop melody, rhythmic synth bass]
{verse2}

[Chorus - Massive uplifting EDM festival chorus, crowd singing along]
{chorus}

[Party Section - Hype chants and horns between sections]
{party_section}

[Verse 3 - High-energy rhythm, bright synths]
{verse3}

[Chorus - Massive uplifting EDM festival chorus, maximum energy]
{chorus}

[Outro - Final Refrain, traditional melody climax, confetti cannons, crowd cheering]
{outro}

[End]"""
    return apply_personalization(
        template,
        name=name,
        age=age,
        city=city,
        hobby=hobby,
        relationship=relationship,
    )


def _lyrics_birthday_edm_party_v2(
    name: str,
    *,
    age: str = "",
    city: str = "",
    hobby: str = "",
    relationship: str = "",
) -> str:
    """~150s festival EDM remix — strict global Happy Birthday melody phrasing."""
    classic = _classic_four_lines(name)
    party_chant = """Hey! Hey! Hey!
Everybody clap your hands!
Hey! Hey! Hey!
Let's celebrate today!"""

    hype_section = """Let's celebrate! (Hey!)
Let's celebrate! (Hey!)
It's your special day!
Let's celebrate! (Hey!)
Let's celebrate! (Hey!)
Hip hip hooray!"""

    template = f"""[Intro - 3-2-1 buildup, rising synth sweep, crowd cheering]
3...
2...
1...

[Drop - Heavy 128 BPM four-on-the-floor festival dance beat]
[Instrumental Drop - bright lead synths, massive bass, party horns]

[Refrain - Traditional Global Happy Birthday Melody and Phrasing]
{classic}

[Party Chant - Crowd claps and hype chants synchronized to the beat]
{party_chant}

[Refrain - Traditional Global Happy Birthday Melody, full crowd singalong]
{classic}

[Hype Section - Energy riser, rhythmic chanting]
{hype_section}

[Party Chant - Heavy beat, rhythmic crowd claps]
{party_chant}

[Refrain - Traditional Global Happy Birthday Melody, ultimate energy level]
{classic}

[Outro - Festival EDM drop outro, confetti cannons, crowd cheering and whistling]
[Fade Out]"""
    return apply_personalization(
        template,
        name=name,
        age=age,
        city=city,
        hobby=hobby,
        relationship=relationship,
    )


def _lyrics_birthday_edm_party(
    name: str,
    *,
    age: str = "",
    city: str = "",
    hobby: str = "",
    relationship: str = "",
) -> str:
    """~150s EDM party remix: countdown, drops, chants, Happy Birthday melody loops."""
    classic = _classic_four_lines(name)
    party_chant = """Hey!
Hey!
Hey!

Everybody clap your hands

Hey!
Hey!
Hey!

Celebrate today"""

    party_section = """Let's celebrate
Let's celebrate

It's your special day

Let's celebrate
Let's celebrate

Hip hip hooray"""

    final_refrain = f"""{classic}

Everybody sing along

Happy birthday dear {name}"""

    parts = [
        "[Intro - countdown, building EDM energy]\n3...\n2...\n1...",
        (
            "[Drop - festival EDM drop, four-on-the-floor beat]\n"
            "[Instrumental]\n[dance drums, bass drop, bright synths]\n"
            f"{classic}"
        ),
        f"[Party Chant - crowd claps and chants]\n{party_chant}",
        f"[Refrain - traditional Happy Birthday melody over dance beat]\n{classic}",
        f"[Party Section - group chant, party horns]\n{party_section}",
        f"[Party Chant - repeat]\n{party_chant}",
        f"[Refrain - Happy Birthday melody]\n{classic}",
        (
            "[Final Drop - EDM build and drop]\n"
            "[Instrumental]\n[confetti riser, party FX, crowd noise]"
        ),
        f"[Final Refrain - big singalong]\n{final_refrain}",
        "[Outro - party FX fade]\n[crowd cheering, hand claps]\n[Fade Out]",
    ]
    return apply_personalization(
        "\n\n".join(parts),
        name=name,
        age=age,
        city=city,
        hobby=hobby,
        relationship=relationship,
    )


def _lyrics_birthday_restaurant_party(
    name: str,
    *,
    age: str = "",
    city: str = "",
    hobby: str = "",
    relationship: str = "",
) -> str:
    """~180s restaurant birthday party — crowd singalong, Happy Birthday core melody."""
    classic = _classic_four_lines(name)
    wishes = """Let's celebrate together
Clap your hands today
Everybody sing along
It's your special day"""

    crowd = f"""Happy birthday dear {name}
We're so glad you're here
Happy birthday dear {name}
Let's all give a cheer"""

    parts = [
        (
            "[Intro - traditional Happy Birthday melody, hand claps, restaurant party]\n"
            f"{classic}\n\n{classic}"
        ),
        f"[Verse 1 - birthday wishes, clapping, Happy Birthday melody feel]\n{wishes}",
        _hb_refrain_block(name, "Happy Birthday refrain - choir and hand claps"),
        (
            "[Crowd singalong - call and response, whole restaurant joins]\n"
            f"{crowd}\n\n"
            "[Everyone - clap and sing]\n"
            "Happy birthday to you\n"
            "Happy birthday to you"
        ),
        f"[Verse 2 - birthday wishes, party energy]\n{wishes}",
        (
            "[Finale - big Happy Birthday celebration, crowd and choir]\n"
            f"{classic}\n\n{classic}\n\n"
            f"Happy birthday dear {name}\n"
            "Let's all give a cheer\n\n"
            f"{classic}"
        ),
        f"[Outro - hand claps fade]\nHappy birthday dear {name}\n[Fade Out]",
    ]
    return apply_personalization(
        "\n\n".join(parts),
        name=name,
        age=age,
        city=city,
        hobby=hobby,
        relationship=relationship,
    )


def _lyrics_birthday_classic_extended(
    name: str,
    *,
    age: str = "",
    city: str = "",
    hobby: str = "",
    relationship: str = "",
) -> str:
    """~240s song built on repeated Happy Birthday melody (no pop verse/chorus)."""
    classic = _classic_four_lines(name)
    wishes = """May God bless you on this day
May joy and laughter come your way
We gather here to celebrate
You make this moment simply great"""

    memories = """Every year brings something new
Every friend is here for you
Memories we hold so dear
We wish you happiness all year"""

    bridge = """Make a wish and blow the flame
We all sing out your name
May your dreams come true today
Happy birthday we all say"""

    parts = [
        f"[Intro - traditional Happy Birthday melody]\n{classic}\n\n{classic}",
        f"[Verse 1 - birthday wishes, sing to Happy Birthday melody]\n{wishes}",
        _hb_refrain_block(name, "Happy Birthday refrain"),
        f"[Verse 2 - memories, sing to Happy Birthday melody]\n{memories}",
        _hb_refrain_block(name, "Happy Birthday refrain"),
        f"[Bridge - sing to Happy Birthday melody]\n{bridge}",
        _hb_refrain_block(name, "Happy Birthday refrain"),
        f"[Verse 3 - birthday wishes, Happy Birthday melody]\n{wishes}",
        _hb_refrain_block(name, "Happy Birthday refrain"),
        f"[Verse 4 - memories, Happy Birthday melody]\n{memories}",
        _hb_refrain_block(name, "Happy Birthday refrain"),
        f"[Finale - traditional Happy Birthday melody, full crowd singalong]\n{classic}\n\n{classic}\n\n{classic}\n\n{classic}",
        f"[Outro - traditional Happy Birthday melody]\nHappy birthday dear {name}\nHappy birthday to you\n[Fade Out]",
    ]
    return apply_personalization(
        "\n\n".join(parts),
        name=name,
        age=age,
        city=city,
        hobby=hobby,
        relationship=relationship,
    )


def _lyrics_birthday_anthem(
    name: str,
    *,
    age: str = "",
    city: str = "",
    hobby: str = "",
    relationship: str = "",
) -> str:
    """Modern birthday anthem template (~240s): classic intro then original song."""
    classic = _classic_four_lines(name)
    pre_chorus = """Raise your hands up to the sky
Let the music lift us high"""

    chorus = f"""Oh it's your birthday
We're singing loud today
Every heart is here to say
Happy birthday

Oh it's your birthday
Let's celebrate your way
May happiness forever stay
Happy birthday"""

    final_chorus = f"""Oh it's your birthday
We're singing loud today
Every heart is here to say
Happy birthday

Happy birthday dear {name}
Happy birthday dear {name}
May your brightest dreams come true
We're celebrating you"""

    template = f"""[Intro - traditional Happy Birthday melody, female lead and choir]
{classic}

{classic}

[Verse 1 - warm female lead vocal]
Today the stars are shining bright
We're gathered here tonight
Every smile and every cheer
Celebrates another year

The candles glow, the laughter flows
A moment everyone knows
This special day belongs to you
And all your dreams are coming true

[Pre-Chorus - building energy]
{pre_chorus}

[Chorus - female lead with mixed choir, huge singalong]
{chorus}

[Verse 2 - emotional female lead vocal]
Every memory that we've made
Every challenge that you've faced
Made you stronger day by day
And brought you to this place

[Pre-Chorus]
{pre_chorus}

[Chorus - choir joins big]
{chorus}

[Bridge - heartfelt, building to climax]
Make a wish and close your eyes
Dreams are waiting in the skies
Every journey starts anew
The world is cheering just for you

[Final Chorus - anthemic, full choir]
{final_chorus}

[Outro - gentle, traditional feel]
Happy birthday to you
Happy birthday dear {name}
May your dreams come true
[Fade Out]
"""
    return apply_personalization(
        template,
        name=name,
        age=age,
        city=city,
        hobby=hobby,
        relationship=relationship,
    )


def _blessing_chorus_en() -> str:
    return """May God bless you
May God bless you
On this wonderful day
May God bless you"""


def _lyrics_jaaniya() -> str:
    """Lyrics for Jaaniya (Haunted 3D) — used with cover mode."""
    return """[Verse 1 - male vocal]
Dil sunta hai teri sada
Aa ru ba ru ab toh zara
Bechain si meri zindagi
Sun kar teri yeh dastaan

Jeena mera aasan kar
Tu mil ke yeh ehsaan kar
Kahin kho gaya chain-o-sukoon
Tere dard ko ab jaan kar

[Chorus]
Jaaniya, o jaaniya
Bas roye dil mera
Aansoo palkon pe nahi hai bewajah
Dil hai ghamzada, jaaniya

[Verse 2]
Tujhe paa liya ya kho diya
Is baat par dil ro diya
Ke chaah kar tu na aa sake
Tu waqt hai guzra hua

Tujhe rakh liya in yaadon ne
Ik phool sa kitaabon mein
Is dil mein tu rahega sada
Aur mehkega in saanson mein

[Verse 3]
Raaton mein tu jal jaata hai
Chehre mein tu dhal jaata hai
Taara hai tu mujhme toota sa

Neendon se jaga deta hai
Palkon ko bhigo deta hai
Dariya hai tu mujhme dooba sa
Har waqt khwaabon ki tarah tu aata raha

[Chorus]
Jaaniya, o jaaniya
Din kya raat kya
Aahat ho koi, lagta hai sada
Ke tu hai wahan jaaniya

[Final Chorus]
Jaaniya, o jaaniya
Bas roye dil mera
Aansoo palkon pe nahi hai bewajah
Dil hai ghamzada, jaaniya
[Fade Out]
"""


def _lyrics_party_dance_intro(name: str) -> str:
    """Classic HB lyrics on a full dance beat from bar one (~45s)."""
    return f"""[Intro - loud clear lead female vocal upfront, beat from bar one]
Happy birthday to you
Happy birthday to you
Happy birthday dear {name}
Happy birthday to you

Happy birthday to you
Happy birthday to you
Happy birthday dear {name}
Happy birthday to you

Happy birthday dear {name}
Happy birthday to you"""


def _lyrics_party_dance_body(name: str) -> str:
    """Former dance-party section: verses, chorus, drop, outro (~195s)."""
    chorus = f"""[Chorus - loud clear lead vocal with group backing]
Happy birthday {name}, let's celebrate
Dance all night, this is your day
Hands up high, sing it out loud
Happy birthday {name}, we love you now"""

    return f"""[Verse 1 - loud clear lead female vocal upfront]
The lights are flashing, the music's loud
{name}, you're the star of the crowd
Another year, another cheer
Everybody's dancing, the party's here

[Pre-Chorus - clear lead vocal]
Put your hands together, feel the beat
Stomp your feet to the party heat
Here we go, here we go now

{chorus}

[Drop - lead vocal over dance beat]
Happy birthday {name}
Happy birthday {name}
Everybody sing it now
Happy birthday {name}

[Verse 2 - loud clear lead female vocal upfront]
Make a wish and blow the flame
The whole room is calling your name
Laughing, singing, hearts are bright
{name}, this is your night

[Pre-Chorus - clear lead vocal]
Put your hands together, feel the beat
Stomp your feet to the party heat
Here we go, here we go now

{chorus}

[Bridge - clear lead vocal with harmonies]
From every corner of the room
We're sending love your way
Unforgettable moments bloom
On your special day, {name}

[Final Chorus - loud anthemic lead vocal]
Happy birthday {name}, let's celebrate
Dance all night, this is your day
Hands up high, sing it out loud
Happy birthday {name}, we love you now

[Outro - clear lead vocal]
Happy birthday, {name}!
Happy birthday to you
[Fade Out]
"""


def _lyrics_party_dance_hybrid_full(name: str) -> str:
    """Full single-pass lyrics (intro + body) — used without hybrid edit."""
    return _lyrics_party_dance_intro(name) + "\n\n" + _lyrics_party_dance_body(name)


def _lyrics_party_dance(name: str) -> str:
    """Alias for full single-pass party-dance lyrics."""
    return _lyrics_party_dance_hybrid_full(name)


def _lyrics_edm_party(name: str) -> str:
    """Original EDM party anthem structure (~240s) with personalized name."""
    return f"""[Intro]
[Instrumental]
[party FX, synth riser, crowd noise]
[crowd chant: Hey! Hey! Hey!]

[Verse 1 - male and female vocals]
Tonight we celebrate you, {name}
Friends and family gathered here
Every smile is shining through
This is your moment, loud and clear

[Pre-Chorus - building energy]
Can you feel it rising up
Every heartbeat counts today
Hands up high and don't stop
Here comes the celebration

[Chorus - anthemic group vocals]
Oh-oh, it's your day, {name}
Sing it loud across the world
Happiness and success and laughter
Memories we'll keep forever
Oh-oh, we celebrate tonight
Birthday flames burning bright
Everybody sing together
This is your time to shine

[Drop]
[Instrumental]
[dance drums, bass drop, bright synths]
[crowd chant: {name}! {name}!]
[hand claps]

[Verse 2 - male and female vocals]
Another year of dreams come true
Friendship standing by your side
Wishing all the best to you
Joy and luck on this great ride

[Pre-Chorus - building energy]
Can you feel it rising up
Every heartbeat counts today
Hands up high and don't stop
Here comes the celebration

[Chorus - anthemic group vocals]
Oh-oh, it's your day, {name}
Sing it loud across the world
Happiness and success and laughter
Memories we'll keep forever
Oh-oh, we celebrate tonight
Birthday flames burning bright
Everybody sing together
This is your time to shine

[Bridge - group vocals]
From every corner of the world
We're sending love your way
Unforgettable moments bloom
On your special day, {name}

[Build]
[Instrumental]
[confetti-style riser, party FX]
[crowd chant: Happy birthday!]

[Final Chorus - anthemic group vocals]
Oh-oh, it's your day, {name}
Sing it loud across the world
Happiness and success and laughter
Memories we'll keep forever
Oh-oh, we celebrate tonight
Birthday flames burning bright
Everybody sing together
This is your time to shine

[Outro]
[Instrumental]
[crowd cheering, hand claps]
Happy birthday, {name}!
[Fade Out]
"""


def _lyrics_duet_traditional(name: str, language: str = "en") -> str:
    """Classic Happy Birthday lyrics for duet cover — matches vocal reference structure."""
    if language != "en":
        return _lyrics_traditional(name, language)
    classic = _classic_four_lines(name)
    blessing = _blessing_chorus_en()
    parts: list[str] = []
    for verse in range(1, 7):
        parts.append(f"[Verse {verse} - male and female duet]\n{classic}")
        parts.append(f"[Chorus - duet harmonies]\n{blessing}")
    parts.append(
        f"[Outro - duet]\nHappy birthday, {name}\nMay God bless you always\n[Fade Out]"
    )
    return "\n\n".join(parts)


def _lyrics_traditional(name: str, language: str = "en") -> str:
    """Classic Happy Birthday lyrics — vocals from bar one, professional sing-along."""
    if language == "hi":
        classic = f"""जन्मदिन की शुभकामनाएँ
जन्मदिन की शुभकामनाएँ
जन्मदिन मुबारक हो {name}
जन्मदिन की शुभकामनाएँ"""
        blessing = """भगवान आपको आशीर्वाद दे
भगवान आपको आशीर्वाद दे
इस खूबसूरत दिन पर
भगवान आपको आशीर्वाद दे"""
    elif language == "es":
        classic = f"""Feliz cumpleaños a ti
Feliz cumpleaños a ti
Feliz cumpleaños querido {name}
Feliz cumpleaños a ti"""
        blessing = """Que Dios te bendiga
Que Dios te bendiga
En este día especial
Que Dios te bendiga"""
    else:
        classic = _classic_four_lines(name)
        blessing = _blessing_chorus_en()

    parts: list[str] = []
    for verse in range(1, _TEXT2MUSIC_VERSE_COUNT + 1):
        parts.append(f"[Verse {verse} - powerful female vocal]\n{classic}")
        parts.append(f"[Chorus - group vocals]\n{blessing}")
    parts.append(
        f"[Outro - female vocal]\nHappy birthday, {name}\nMay God bless you always\n[Fade Out]"
    )
    return "\n\n".join(parts)


def _lyrics_en(name: str) -> str:
    """Default English lyrics: classic Happy Birthday structure."""
    return _lyrics_traditional(name, "en")


def _lyrics_cover(name: str, language: str) -> str:
    """Tighter lyrics for cover mode (src_audio drives melody)."""
    if language == "hi":
        classic = f"""जन्मदिन की शुभकामनाएँ
जन्मदिन की शुभकामनाएँ
जन्मदिन मुबारक हो {name}
जन्मदिन की शुभकामनाएँ"""
        blessing = """भगवान आपको आशीर्वाद दे
भगवान आपको आशीर्वाद दे
इस खूबसूरत दिन पर
भगवान आपको आशीर्वाद दे"""
    else:
        classic = _classic_four_lines(name)
        blessing = _blessing_chorus_en()

    return f"""[Verse 1]
{classic}

[Chorus]
{blessing}

[Verse 2]
{classic}

[Chorus]
{blessing}

[Verse 3]
{classic}

[Chorus]
{blessing}

[Verse 4]
{classic}

[Chorus]
{blessing}

[Verse 5]
{classic}

[Chorus]
{blessing}

[Verse 6]
{classic}

[Outro]
Happy birthday, {name}
May God bless you always
[Fade Out]
"""


def _lyrics_es(name: str) -> str:
    classic = f"""Feliz cumpleaños a ti
Feliz cumpleaños a ti
Feliz cumpleaños querido {name}
Feliz cumpleaños a ti"""
    blessing = """Que Dios te bendiga
Que Dios te bendiga
En este día especial
Que Dios te bendiga"""
    parts: list[str] = []
    for verse in range(1, 7):
        parts.append(f"[Verse {verse} - warm female vocal]\n{classic}")
        parts.append(f"[Chorus]\n{blessing}")
    parts.append(f"[Outro]\nFeliz cumpleaños, {name}\n[Fade Out]")
    return "\n\n".join(parts)


def _lyrics_hi(name: str) -> str:
    return _lyrics_cover(name, "hi")


def _lyrics_zh(name: str) -> str:
    classic = f"""祝你生日快乐
祝你生日快乐
亲爱的{name}生日快乐
祝你生日快乐"""
    blessing = """愿上帝祝福你
愿上帝祝福你
在这美好的一天
愿上帝祝福你"""
    parts: list[str] = []
    for verse in range(1, 7):
        parts.append(f"[Verse {verse} - warm female vocal]\n{classic}")
        parts.append(f"[Chorus]\n{blessing}")
    parts.append(f"[Outro]\n生日快乐，{name}\n[Fade Out]")
    return "\n\n".join(parts)
