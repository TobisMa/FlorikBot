from config import PLAN_PW
import discord
from discord.ext import commands
import datetime
from helper_functions import *
import cogs.chess_helper.chess_helper as chess


class Chess(commands.Cog):
    """Schach"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        await ctx.send(embed=self.boar_to_embed(self.create_board()))

    def boar_to_embed(self, board):
        e = discord.Embed()
        e.description = ""
        for row in range(8):
            for line in range(8):
                light_square = (line + row) % 2 == 0
                if board[row * 8 + line] == 0:
                    e.description += chess.WHITE_SQUARE if light_square else chess.BLACK_SQUARE
                else:
                    e.description += chess.get_symbol_by_number(
                        self.bot, board[row * 8 + line])
            e.description += "\n"
        return e

    def start_game(self):
        pass

    def create_board(self):
        board = [0 for _ in range(64)]

        board[0] = chess.BLACK | chess.ROOK
        board[7] = chess.BLACK | chess.ROOK
        board[1] = chess.BLACK | chess.KNIGHT
        board[6] = chess.BLACK | chess.KNIGHT
        board[2] = chess.BLACK | chess.BISHOP
        board[5] = chess.BLACK | chess.BISHOP
        board[3] = chess.BLACK | chess.QUEEN
        board[4] = chess.BLACK | chess.KING
        for i in range(8):
            board[8 + i] = chess.BLACK | chess.PAWN

        board[0 + 56] = chess.WHITE | chess.ROOK
        board[7 + 56] = chess.WHITE | chess.ROOK
        board[1 + 56] = chess.WHITE | chess.KNIGHT
        board[6 + 56] = chess.WHITE | chess.KNIGHT
        board[2 + 56] = chess.WHITE | chess.BISHOP
        board[5 + 56] = chess.WHITE | chess.BISHOP
        board[3 + 56] = chess.WHITE | chess.QUEEN
        board[4 + 56] = chess.WHITE | chess.KING
        for i in range(8):
            board[48 + i] = chess.WHITE | chess.PAWN

        return board


def setup(bot):
    bot.add_cog(Chess(bot))
