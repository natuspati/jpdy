NUM_PROMPTS_IN_CATEGORY = 5
MIN_ROUNDS_IN_LOBBY = 1
MAX_ROUNDS_IN_LOBBY = 3
MIN_CATEGORIES_PER_ROUND = 1
MAX_CATEGORIES_PER_ROUND = 5
MAX_BETTING_PROMPTS_PER_ROUND = MAX_CATEGORIES_PER_ROUND * NUM_PROMPTS_IN_CATEGORY

SCORE_MULTIPLIER = 100
# Max bet is this many times the highest prompt value of the round.
MAX_BET_MULTIPLIER = 5
ROUND_SCORE_MULTIPLIER = 2
ANSWERING_TIME_SECONDS = 30
BETTING_ANNOUNCEMENT_SECONDS = 4
BETTING_TIME_SECONDS = 15
BETTING_PROMPT_DEFAULT_PERCENT = 10
BUZZING_TIME_SECONDS = 10
ANSWER_REVEAL_TIME_SECONDS = 30
ROUND_SUMMARY_TIME_SECONDS = 10
FINAL_BETTING_TIME_SECONDS = 30
FINAL_ANSWERING_TIME_SECONDS = 60
# A dropped socket is only shown as disconnected after this long, so a network blip is invisible.
DISCONNECT_GRACE_SECONDS = 15
# A finished game is already in SQL; Redis keeps it briefly so late reconnects still see the result.
FINISHED_GAME_TTL_SECONDS = 24 * 60 * 60
# The event stream is an unread audit trail of full snapshots; keep only the recent tail.
GAME_EVENTS_MAX_LENGTH = 200

MEDIA_MAX_BYTES_BY_KIND = {
    "image": 10 * 1024 * 1024,
    "audio": 20 * 1024 * 1024,
    "video": 100 * 1024 * 1024,
}
