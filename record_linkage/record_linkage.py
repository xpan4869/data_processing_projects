'''
Linking restaurant records in Zagat and Fodor's list using restaurant
names, cities, and street addresses.

Xinyue Yolanda Pan

'''
import csv
import jellyfish
import pandas as pd
import util

def find_matches(output_filename, mu, lambda_, block_on_city=False):
    '''
    Put it all together: read the data and apply the record linkage
    algorithm to classify the potential matches.

    Inputs:
      output_filename (string): the name of the output file,
      mu (float) : the maximum false positive rate,
      lambda_ (float): the maximum false negative rate,
      block_on_city (boolean): indicates whether to block on the city or not.
    '''

    # Hard-coded filename
    zagat_filename = "data/zagat.csv"
    fodors_filename = "data/fodors.csv"
    known_links_filename = "data/known_links.csv"

    ### YOUR CODE HERE
    za_df = pd.read_csv(zagat_filename)
    fo_df = pd.read_csv(fodors_filename)
    known_links_df = pd.read_csv(known_links_filename, header = None)
    unmatch_pairs_df = pd.read_csv("data/unmatch_pairs.csv", header = None)
    
    # Estimate probabilities
    mat_prob_dict = estimate_prob(known_links_df, za_df, fo_df)
    unm_prob_dict = estimate_prob(unmatch_pairs_df, za_df, fo_df)

    # Construct and sort probability tuples
    sorted_remaining = construct_probability_tuples(mat_prob_dict, unm_prob_dict)

    # Label similarity tuples
    match, unmatch = ini_find_matches(sorted_remaining, mu, lambda_)
    possible = initial_screening_possible_match(mat_prob_dict, unm_prob_dict)
    labels = check_unlabeled(possible, match, unmatch)

    # Classify pairs and write to output file
    with open(output_filename, 'w') as f:
        writer = csv.writer(f)

        for za_index, za_row in za_df.iterrows():
            for fo_index, fo_row in fo_df.iterrows():

                if block_on_city:
                    if za_row['city'] != fo_row['city']:
                        continue
                
                similarity_tpl = compute_similarity_tpl(za_row, fo_row)
                label = labels[similarity_tpl]
                writer.writerow([za_index, fo_index, label])

### YOUR AUXILIARY FUNCTIONS HERE
def construct_similarity_tuple_dictionary():
    '''
    This function initializes a dictionary to store the frequency of each similarity tuple.
    The similarity tuple is a combination of three categories: 'low', 'medium', and 'high'.
    The dictionary keys are all possible combinations of these categories, and the values are initialized to 0.
    '''
    result = {}
    for a in ['low', 'medium', 'high']:
        for b in ['low', 'medium', 'high']:
            for c in ['low', 'medium', 'high']:
                result[(a, b, c)] = 0
    return result

def compute_similarity_ctg(str1, str2):
    '''
    This function computes the Jaro-Winkler similarity between two strings 
    and categorizes the result into "low", "medium", or "high".
    The Jaro-Winkler similarity score is a measure of string similarity, and the category is determined based on predefined thresholds.
    '''
    jw_score = jellyfish.jaro_winkler_similarity(str(str1), str(str2))
    jw_ctg = util.get_jw_category(jw_score)
    return jw_ctg

def compute_similarity_tpl(za_series, fo_series):
    '''
    This is a helper function that constructs a similarity tuple for a pair of rows from the Zagat and Fodor's datasets. 
    It computes the similarity category for the name, city, and address fields.
    The function returns a tuple of three categories representing the similarity of the corresponding fields.
    '''    
    similarity_tpl = ()
    for i in range(1,4):
        ctg = compute_similarity_ctg(za_series.iloc [i], fo_series.iloc[i])
        similarity_tpl += (ctg,)
    return similarity_tpl

def estimate_prob(link_df, left_df, right_df):
    '''
    This function estimates the probability of each similarity tuple based on the linked data.
    It iterates through the linked data, computes the similarity tuple for each pair, and updates the frequency of each tuple in the dictionary.
    Finally, it calculates the probability of each tuple by dividing its frequency by the total number of linked pairs.
    '''
    similarity_tuple_dict = construct_similarity_tuple_dictionary()
    prob_dict = {}
    for _, row in link_df.iterrows():
        za_idx = row[0]  # First column
        fo_idx = row[1]  # Second column
        
        jw_ctg = compute_similarity_tpl(left_df.iloc[za_idx], 
                                      right_df.iloc[fo_idx])
        similarity_tuple_dict[jw_ctg] += 1
        
    for key, val in similarity_tuple_dict.items():
        prob_dict[key] = val/len(link_df)
        
    return prob_dict


def initial_screening_possible_match(mat_prob_dict, unm_prob_dict):
    '''
    This function performs an initial screening to identify possible matches based on the probability dictionaries.
    It identifies tuples where both the match and unmatch probabilities are zero, indicating that these tuples are possible matches.
    '''
    partition_dict = construct_similarity_tuple_dictionary()
    possible_match = []
    all = partition_dict.keys()
    for tpl in all: 
        m_w = mat_prob_dict[tpl]
        u_w = unm_prob_dict[tpl]
        if  m_w == 0 and u_w == 0:
            possible_match.append(tpl)
    return possible_match

def construct_probability_tuples(mat_prob_dict, unm_prob_dict):
    '''
    This function constructs a list of probability tuples for the remaining similarity tuples after the initial screening.
    It excludes the possible matches identified in the initial screening and sorts the remaining tuples based on their probabilities.
    '''
    partition_dict = construct_similarity_tuple_dictionary()
    all = partition_dict.keys()
    possible_match = initial_screening_possible_match(mat_prob_dict, unm_prob_dict)
    unvisited = all - possible_match

    for_sorting = []
    for key in unvisited:
        for_sorting.append((key, mat_prob_dict[key], unm_prob_dict[key]))
    
    sorted_remaining = util.sort_prob_tuples(for_sorting)
    return sorted_remaining

def ini_find_matches(sorted_remaining, mu, lambda_):
    '''
    This function identifies matches and non-matches based on the sorted probability tuples.
    It accumulates the probabilities of unmatch and match tuples until the thresholds mu and lambda_ are reached, respectively.
    '''
    cum_u_w = 0
    match = []
    
    unmatch = []
    cum_m_w = 0

    for tpl in sorted_remaining:
        if cum_u_w + tpl[2] > mu:
            break
        cum_u_w += tpl[2]
        match.append(tpl[0])
    
    for tpl in sorted_remaining[::-1]:
        if cum_m_w + tpl[1] > lambda_: 
            break
        cum_m_w += tpl[1]
        unmatch.append(tpl[0])
    return match, unmatch

def check_unlabeled(possible, match, unmatch):
    '''
    This function checks for unlabeled similarity tuples and updates the classification of each tuple.
    It handles crossover cases where a tuple is classified as both a match and a non-match, biasing towards matches.
    It also identifies tuples that were not labeled and adds them to the possible matches.
    Finally, it returns a mapping of each tuple to its classification.
    '''
    mapping = {}
    partition_dict = construct_similarity_tuple_dictionary()
    all = partition_dict.keys()
    new_possible = possible.copy()  # Start with initial possible matches
    
    # Handle crossover - bias towards matches
    duplicates = set(match) & set(unmatch)
    if duplicates:
        for dup in duplicates:
                unmatch.remove(dup)
    
    # Find missing/unlabeled tuples and add them to possible matches
    labeled = set(match + unmatch + new_possible)
    for tpl in all:
        if tpl not in labeled:
            new_possible.append(tpl)
    
    # Then apply classifications in priority order
    for pos in new_possible:
        mapping[pos] = 'possible match'
    for unm in unmatch:
        mapping[unm] = 'unmatch'
    for mat in match:
        mapping[mat] = 'match'
        
    return mapping