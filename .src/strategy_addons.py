"""
Strategy Addons:

These are classes that add additional functionality to the basic chicken strategy.
Think of these as "secondary" objectives or "modifiers" to behavior.
These exist to:
A) allow users to test out dynamic versions of different behaviors
B) standardize modifications for first-order logic in module 1
C) 'pre-load' some strategies for users to test out

"""

class Strategy:

    def __init__(self, player:str, gamestate:dict, history=[]):
        self.player = player
        self.gamestate = gamestate
        self.history = history

class Strategy_HP(Strategy):
    def __init__(self, player:str, gamestate:dict, history=[]):
        super().__init__(player, gamestate, history)
    
    def evaluate(self)  -> float:
        return self.gamestate[f"{self.player}_hp"] - self.gamestate[f"{self.player}_crash_dmg"]