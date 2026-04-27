"""Example usage of the GameEngine for the Chicken game.

This demonstrates how to use the engine to run a game with simple strategies.
"""

from engine import GameEngine


def always_stay_strategy(gamestate: dict) -> bool:
    """Strategy that always chooses to stay."""
    return True


def always_swerve_strategy(gamestate: dict) -> bool:
    """Strategy that always chooses to swerve."""
    return False


def tit_for_tat_strategy(gamestate: dict, player: str) -> bool:
    """Strategy that mirrors the opponent's previous action.
    
    Args:
        gamestate: Current game state
        player: "p1" or "p2"
    
    Returns:
        True to stay, False to swerve
    """
    opponent = "p2" if player == "p1" else "p1"
    opponent_history = gamestate.get(f"{opponent}_action_history", [])
    
    # If opponent has no history, default to swerve (cooperate initially)
    if not opponent_history:
        return False
    
    # Mirror opponent's last action
    last_action = opponent_history[-1]
    return last_action == "stay"


def main():
    """Run a simple game demonstration."""
    # Create engine with default gamestate
    engine = GameEngine()
    
    # Define strategies
    def p1_strategy(gs: dict) -> bool:
        return tit_for_tat_strategy(gs, "p1")
    
    def p2_strategy(gs: dict) -> bool:
        # P2 always stays on first round, then mirrors p1
        if gs["round"] == 0:
            return True
        return tit_for_tat_strategy(gs, "p2")
    
    # Run game for 5 rounds
    print("Running Chicken game for 5 rounds...")
    print("=" * 50)
    
    history = engine.run_game(
        max_rounds=5,
        p1_strategy=p1_strategy,
        p2_strategy=p2_strategy
    )
    
    # Print game history
    for i, state in enumerate(history):
        print(f"\nState {i}:")
        print(f"  Round: {state['round']}")
        p1_history = state.get('p1_action_history', [])
        p2_history = state.get('p2_action_history', [])
        print(f"  P1: {'STAY' if state['p1_stay'] else 'SWERVE'} "
              f"(HP: {state['p1_hp']}, History: {p1_history})")
        print(f"  P2: {'STAY' if state['p2_stay'] else 'SWERVE'} "
              f"(HP: {state['p2_hp']}, History: {p2_history})")
    
    print("\n" + "=" * 50)
    print(f"Final state after {len(history)} gamestates")
    final = history[-1]
    print(f"P1 HP: {final['p1_hp']}, P2 HP: {final['p2_hp']}")


if __name__ == "__main__":
    main()
