import inspect
import random

import hashids
import telethon

from mini_apps.app import App, Client


id_encoder = hashids.Hashids("tictactoe", alphabet="abcdefhkmnpqrstuvwxy34578")


class Player:
    """
    Keeps track of a player's status
    """
    def __init__(self, client: Client):
        self.game = None
        self.user = client.user
        self.client = client
        self.id = client.user.telegram_id
        self.requested = None
        self.player_order = -1

    async def send(self, **kwargs):
        """
        Sends a message to the player
        """
        # TODO send something on telegram if the client isn't online
        if self.client:
            await self.client.send(**kwargs)


class Game:
    triplets = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),

        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),

        (0, 4, 8),
        (2, 4, 6),
    ]

    def __init__(self, host: Player):
        self.host: Player = host
        self.guest: Player = None
        self.table = [""] * 9
        self.winner = None
        self.id = id_encoder.encode(host.user.telegram_id)
        self.turn = -1
        self.winning_triplet = None
        self.free = 9

    def turn_name(self):
        if self.turn == 0:
            return self.host.user.name
        elif self.turn == 1:
            return self.guest.user.name
        return ""

    def is_host(self, player: Player):
        return player.id == self.host.id

    async def send_state(self, player: Player):
        await player.send(
            type="game.state",
            turn=self.turn,
            table=self.table,
            turn_name=self.turn_name(),
            finished=self.winner is not None,
            winner=self.winner,
            triplet=self.winning_triplet
        )

    async def send_to_player(self, player: Player):
        if self.winner is not None:
            await self.send_state(player)
        elif self.is_host(player):
            if self.guest:
                player.player_order = 0
                await player.send(type="game.join", id=self.id, other_player=self.guest.user.name, player_order=0)
                await self.send_state(player)
            else:
                await player.send(type="game.created", id=self.id)
        elif player.id == self.guest.id:
            player.player_order = 1
            await player.send(type="game.join", id=self.id, other_player=self.host.user.name, player_order=1)
            await self.send_state(player)
        else:
            await player.send(type="error", msg="Not in this game")
            await player.send(type="game.leave")

    async def move(self, player: Player, cell: int):
        """
        Make a move on the player
        """
        if self.winner is not None or player.player_order != self.turn or cell < 0 or cell >= 9 or self.table[cell] != "":
            return

        self.free -= 1
        self.table[cell] = "XO"[player.player_order]
        self.turn = (self.turn + 1) % 2

        for triplet in self.triplets:
            if self.check_same(triplet):
                self.winning_triplet = triplet
                self.winner = player.user.name
                self.turn = player.player_order
                break

        if self.winner is None and self.free <= 0:
            self.winner = "No one"
            self.winning_triplet = []

        await self.send_state(self.host)
        await self.send_state(self.guest)

    def check_same(self, triplet):
        """
        Checks for wins
        """
        a = self.table[triplet[0]]
        if a == "":
            return False

        b = self.table[triplet[1]]
        if b == "" or a != b:
            return False

        c = self.table[triplet[2]]
        if c == "" or c != b:
            return False

        return True


class TicTacToe(App):
    """
    Tic Tac Toe Game
    """
    def __init__(self, *args):
        super().__init__(*args)
        self.players = {}

    def inline_buttons(self):
        """
        Returns the telegram inline button that opens the web app
        """
        types = telethon.tl.types
        return types.ReplyInlineMarkup([
            types.TypeKeyboardButtonRow([
                types.KeyboardButtonWebView(
                    "Play",
                    self.settings.url
                )
            ])
        ])

    async def on_client_authenticated(self, client: Client):
        """
        Called when a client has been authenticated
        """
        player: Player = self.players.get(client.user.telegram_id)
        if not player:
            player = Player(client)
            self.players[client.user.telegram_id] = player
        else:
            player.client = client

        client.player = player
        if player.game:
            await player.game.send_to_player(player)

    @App.bot_command("start", description="Start message")
    async def on_telegram_start(self, args: str, event: telethon.events.NewMessage):
        """
        Called when a user sends /start to the bot
        """
        await self.telegram.send_message(event.chat, inspect.cleandoc("""
        Tic Tac Toe game against another player on telegram
        """), buttons=self.inline_buttons())

    async def on_client_disconnected(self, client: Client):
        """
        Called when a client disconnects from the server
        """
        if client.player:
            client.player.client = None
            # TODO update online status for the other player (if any)

    async def handle_message(self, client: Client, type: str, data: dict):
        """
        Handles messages received from the client
        """
        game = client.player.game

        # A user creates a new game
        if type == "game.new":
            if not game:
                game = Game(client.player)
                client.player.game = game
                client.player.requested = None
            await game.send_to_player(client.player)

        # A user leaves / cancels the game
        elif type == "game.leave":
            if game.is_host(client.player):
                if game.guest:
                    game.guest.game = None
                    await game.guest.send(type="game.leave")
            else:
                game.guest = None

            client.player.game = None

        # A user wants to join an existing game
        elif type == "game.join":
            if game:
                await game.send_to_player(client.player)
                return
            try:
                host_id = id_encoder.decode(data.get("game"))[0]
            except Exception:
                await client.send(type="join.fail")
                return

            host = self.players.get(host_id)
            if not host:
                await client.send(type="join.fail")
                return

            game = host.game
            if not game or game.guest or game.is_host(client.player) or game.winner is not None:
                await client.send(type="join.fail")
                return

            client.player.requested = game.id
            await game.host.send(type="join.request", id=client.user.telegram_id, name=client.user.name)

        # Join request accepted
        elif type == "join.accept":
            guest = self.players.get(data.get("who"))
            if not game or not guest or guest.game or guest.requested != game.id:
                return

            guest.game = game
            game.guest = guest
            game.turn = random.randint(0, 1)
            await game.send_to_player(client.player)
            await game.send_to_player(guest)

        # Join request rejected
        elif type == "join.refuse":
            guest = self.players.get(data.get("who"))
            if not game or not guest or guest.game or guest.requested != game.id:
                return
            await guest.send(type="join.fail")

        # A user makes a move
        elif type == "game.move":
            if game:
                try:
                    cell = int(data["cell"])
                except Exception:
                    return

                await game.move(client.player, cell)

                if game.winner is not None:
                    game.guest.game = None
                    game.host.game = None