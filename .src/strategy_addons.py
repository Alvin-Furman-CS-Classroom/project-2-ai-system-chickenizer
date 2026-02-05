"""
Strategy Addons:

These are classes that add additional functionality to the basic chicken strategy.
Think of these as "secondary" objectives or "modifiers" to behavior.
These exist to:
A) allow users to test out dynamic versions of different behaviors
B) standardize modifications for first-order logic in module 1
C) 'pre-load' some strategies for users to test out

"""

#Dependencies:
import sympy as sp

class Behavior_Default:
    def __init__(self, player, opponent_action):
        if player not in ["p1", "p2"]:
            raise ValueError("Player must be 'p1' or 'p2'")

        self.player = player
        self.opponent_action = opponent_action

    def get_behavior(self):
        if self.opponent_action[3:] == "stay":
            return sp.Symbol(f"{self.player}_swerve")
        else:
            return sp.Symbol(f"{self.player}_stay")

class Behavior_HP:
    def __init__(self, player, hp_curr, hp_thresh, crash_dmg=0):

        #validate p1 or p2
        if player not in ["p1", "p2"]:
            raise ValueError("Player must be 'p1' or 'p2'")

        #instance vars
        self.player = player
        self.hp_curr = hp_curr #starting hp for this player
        self.hp_thresh = hp_thresh #at what point does player alter behavior?
        self.crash_dmg = crash_dmg #how damaging is a crash?
    
    def get_behavior(self):
        if self.hp_curr - self.crash_dmg > self.hp_thresh:
            return sp.Symbol(f"{self.player}_stay")
        else:
            return sp.Symbol(f"{self.player}_swerve")

class Behavior_Constituency:
    def __init__(self, player, history = [], fail = 0, fail_weights = {"big_win":-1, "small_loss":1, "big_loss":2}, fail_thresh=0, hopeful=False):
        if player not in ["p1", "p2"]:
            raise ValueError("Player must be 'p1' or 'p2'")

        self.player = player
        self.history = []
        self.fail_weights = fail_weights
        self.fail_thresh = fail_thresh
        self.hopeful = hopeful

        if player == "p1":
            for rnd in history:
                if rnd[0] == "p1_stay" and rnd[1] == "p2_swerve":
                    self.history.append(fail_weights["big_win"])
                elif rnd[0] == "p1_swerve" and rnd[1] == "p2_stay":
                    self.history.append(fail_weights["small_loss"])
                elif rnd[0] == "p1_swerve" and rnd[1] == "p2_swerve":
                    self.history.append(fail_weights["big_loss"])
                else:
                    self.history.append(0)
        elif player == "p2":
            for rnd in history:
                if rnd[0] == "p2_stay" and rnd[1] == "p1_swerve":
                    self.history.append(fail_weights["big_win"])
                elif rnd[0] == "p2_swerve" and rnd[1] == "p1_stay":
                    self.history.append(fail_weights["small_loss"])
                elif rnd[0] == "p2_swerve" and rnd[1] == "p1_swerve":
                    self.history.append(fail_weights["big_loss"])
                else:
                    self.history.append(0)

        self.fail = sum(self.history)
    
    def get_behavior(self):
        if self.fail > self.fail_thresh and not self.hopeful:
            return sp.Symbol(f"{self.player}_swerve")
        else:
            return sp.Symbol(f"{self.player}_stay")

class Behavior_Memory:
    def __init__(self, player, history=[]):
        if player not in ["p1", "p2"]:
            raise ValueError("Player must be 'p1' or 'p2'")

        self.player = player
        self.history = history

class Behavior_Memory_Grudge(Behavior_Memory):
    def __init__(self, player, history=[]):
        super().__init__(player, history)
        self.grudge = False
        
        if player == "p1":
            for rnd in history:
                if rnd[1] == "p2_stay":
                    self.grudge = True
        elif player == "p2":
            for rnd in history:
                if rnd[0] == "p1_stay":
                    self.grudge = True

    def get_behavior(self):
        if self.grudge:
            return sp.Symbol(f"{self.player}_stay")
        else:
            return sp.Symbol(f"{self.player}_swerve")

class Behavior_Memory_TitForTat(Behavior_Memory):
    def __init__(self, player, history=[]):
        super().__init__(player, history)
        self.history = history  
     
    def get_behavior(self):
        if self.history == []:
            return sp.Symbol(f"{self.player}_swerve")
        else:
            if self.player == "p1":
                return sp.Symbol(self.history[-1][0])
            elif self.player == "p2":
                return sp.Symbol(self.history[-1][1])

class Behavior_Forgiveness_Time(Behavior_Memory):
    def __init__(self, player, history = [], forgiveness_timer=0):
        super().__init__(player, history)
        self.forgiveness_timer = forgiveness_timer
        self.grudge = False

        if player == "p1":
            for rnd in history:
                if rnd[1] == "p2_stay":
                    self.grudge = True
        elif player == "p2":
            for rnd in history:
                if rnd[0] == "p1_stay":
                    self.grudge = True

    def get_behavior(self):
        if self.grudge and self.forgiveness_timer > 0:
            self.forgiveness_timer -= 1
            return sp.Symbol(f"{self.player}_stay")
        else:
            return sp.Symbol(f"{self.player}_swerve")

class Behavior_Forgiveness_Apology(Behavior_Memory):
    def __init__(self, player, history=[], rnds_to_forgiveness=0):
        super().__init__(player, history)
        self.history = history
        self.grudge = False
        self.most_recent_transgression = 0
        
        if player == "p1":
            for i, rnd in enumerate(history):
                if rnd[1] == "p2_stay":
                    self.grudge = True
                    self.most_recent_transgression = i
                    
        elif player == "p2":
            for i, rnd in enumerate(history):
                if rnd[0] == "p1_stay":
                    self.most_recent_transgression = i
                    self.grudge = True

    def get_behavior(self): 
        #if rnds_to_forgiveness rounds have passed since most recent transgression, drop the grudge.
        self.grudge = (self.most_recent_transgression + self.rnds_to_forgiveness) < len(self.history)

        if self.grudge:
            return sp.Symbol(f"{self.player}_stay")
        else:
            return sp.Symbol(f"{self.player}_swerve")