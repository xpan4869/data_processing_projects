import pandas as pd
import numpy as np

def simulate_election(model, n_sim):
    """
    Simulates multiple election outcomes based on state win probabilities.
    Each simulation generates a random number for each state (50 states + DC).
    If the random number is less than the win probability for Obama in that state,
    he wins the state's electoral votes. This process repeats for `n_simulations`.

    Args:
        model (pd.DataFrame): A DataFrame with Obama's win probability per state 
                              and electoral votes per state.
        n_simulations (int): The number of election simulations to run.

    Returns:
        np.ndarray: An np array of total Obama electoral votes across all simulations.
    """

    simulations = np.random.uniform(size=(51, n_sim))
    print("Random number:", simulations)

    obama_votes = ((simulations < model.Obama.values.reshape(-1, 1))
                    * model.Votes.values.reshape(-1, 1))
    print("Electoral votes:", obama_votes)

    # summing over rows gives the total electoral votes for each simulation
    return obama_votes.sum(axis=0)