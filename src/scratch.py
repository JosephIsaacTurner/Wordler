import numpy as np 
import pandas as pd
from Wordle import Wordle

if __name__ == "__main__":
    
    def _validate_guess(guess, actual_word):
        """Validates the guess (if you know the actual word) and returns the response and yellow letters."""
        response = ''.join([g if g == a else '_' for g, a in zip(guess, actual_word)])
        green_count = sum(g == a for g, a in zip(guess, actual_word))
        yellow_letters = ''.join(set(g for g, a in zip(guess, actual_word) if g != a and g in actual_word))
        yellow_count = len(yellow_letters)
        return response, green_count, yellow_letters, yellow_count

    def apply_validate_guess(row):
        response, green_count, yellow_letters, yellow_count = _validate_guess(row['attempt'], row['target'])
        return pd.Series([response, green_count, yellow_letters, yellow_count, green_count + yellow_count])

    word_list = Wordle()._find_possible_answers()
    pairs = [np.array([word_1, word_2]) for word_1 in word_list for word_2 in word_list if word_1 != word_2]
    df = pd.DataFrame(pairs, columns=["attempt", "target"])

    df[['response', 'green_count', 'yellow_letters', 'yellow_count', 'total_count']] = df.apply(apply_validate_guess, axis=1)
    display(df)

