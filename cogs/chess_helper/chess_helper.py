from helper_functions import getEmoji


NOTHING = 0
KING = 1
PAWN = 2
KNIGHT = 3
BISHOP = 4
ROOK = 5
QUEEN = 6
WHITE = 8
BLACK = 16

WHITE_SQUARE = "\N{white large square}"
BLACK_SQUARE = "\U0001f7eb"
symbols = {
    WHITE + KING  : "Joshua",
    WHITE + PAWN  : "PaimonKnife",
    WHITE + KNIGHT: "KannaSoviet",
    WHITE + BISHOP: "KannaFreeze",
    WHITE + ROOK  : "naenaezuko",
    WHITE + QUEEN : "KannaHeart",

    BLACK + KING  : "Ahmad3",
    BLACK + PAWN  : "Hiltergruss",
    BLACK + KNIGHT: "Ahmad2",
    BLACK + BISHOP: "Hammad",
    BLACK + ROOK  : "Fulip2",
    BLACK + QUEEN : "astolfoThinking",
}
    

def get_symbol_by_number(bot, num):
    return str(getEmoji(bot, symbols[num]))