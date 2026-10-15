NUM_PROMPTS_IN_CATEGORY = 5
MAX_CATEGORIES_IN_LOBBY = 10
MIN_CATEGORIES_IN_LOBBY = 1

SCORE_MULTIPLIER = 100
ANSWERING_TIME_SECONDS = 30
BUZZING_TIME_SECONDS = 10
ANSWER_REVEAL_TIME_SECONDS = 30
# A dropped socket is only shown as disconnected after this long, so a network blip is invisible.
DISCONNECT_GRACE_SECONDS = 15

MEDIA_MAX_BYTES_BY_KIND = {
    "image": 10 * 1024 * 1024,
    "audio": 20 * 1024 * 1024,
    "video": 100 * 1024 * 1024,
}
