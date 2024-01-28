import requests
from bs4 import BeautifulSoup
import re
import time
import pandas as pd

class Wordle:
    
    def __init__(self, word_freq_file='src/word_frequencies.csv', exclude_previous_answers=True):
        self.guesses = []
        self.responses = []
        self.disallowed_letters = []
        self.required_letters = []
        self.letters_idx = { _ : None for _ in range(5)}
        self.disallowed_letters_idx = { _ : [] for _ in range(5)}
        self.regex_pattern = None
        self.previous_answers = self._find_previous_wordle_answers(exclude_previous_answers)
        self.word_frequencies = self._load_word_frequencies(word_freq_file)

    def _load_word_frequencies(self, file_path):
        """Load the word frequencies from a CSV file."""
        try:
            df = pd.read_csv(file_path)
            return dict(zip(df['word'], df['frequency']))
        except FileNotFoundError:
            print(f"Word frequencies file '{file_path}' not found. Please provide the correct file.")
            return {}
        
    def rank_words(self, position_letter_frequencies=None, word_list=None, word_count=10):
        """Finds the possible words based on the letter frequencies of available words, 
        taking into account the known letters and disallowed letters."""
        word_list = self._find_allowed_answers()
        position_letter_frequencies = self._compute_letter_frequencies(word_list)
        scored_words = [(word, self._score_word(word, position_letter_frequencies)) for word in word_list]
        scored_words.sort(key=lambda x: x[1], reverse=True)

        # List to store words with no repeated letters.
        non_repeating_words = []

        # Iterate over scored words and select non-repeating words.
        for word, score in scored_words:
            if len(set(word)) == len(word):  # Check for non-repeating characters
                non_repeating_words.append((word, score))
            if len(non_repeating_words) == word_count:
                break

        # Include the rest of the words if less than 10 non-repeating words are found.
        if len(non_repeating_words) < 10:
            remaining_words = [pair for pair in scored_words if pair[0] not in [word for word, _ in non_repeating_words]]
            non_repeating_words.extend(remaining_words[:word_count - len(non_repeating_words)])

        # Return the top 10 words, or all words if there are less than 10.
        return [word for word, _ in non_repeating_words[:word_count]]

    def predict_best_word(self, position_letter_frequencies=None, word_list=None):
        """Predicts the next word to guess based on the letter frequencies of available words,
        taking into account the known letters and disallowed letters.
        Returns the word with the highest frequency from the preloaded list."""
        five_ranked_words = self.rank_words(position_letter_frequencies, word_list, 5)
        five_ranked_words_freq = {word: self.word_frequencies.get(word, 0) for word in five_ranked_words}
        return max(five_ranked_words_freq, key=five_ranked_words_freq.get)

    def submit_multiple_guesses(self, guess_dicts):
        for guess_dict in guess_dicts:
            self.submit_guess(guess_dict["guess"], guess_dict["response"], guess_dict["yellow_letters"])

    def submit_guess(self, guess, response, yellow_letters=None):  
        """Submits a guess and a response to the Wordle game. Updates the known letters and disallowed letters.
        This is most helpful if you are actually playing the game."""
        if yellow_letters is None:
            yellow_letters = ""      
        self.guesses.append(guess)
        self.responses.append(response)

        for i, letter in enumerate(response):
            if letter != "_":
                self.letters_idx[i] = letter
                if letter not in self.required_letters:
                    self.required_letters.append(letter)
            else:
                self.disallowed_letters_idx[i].append(guess[i])

        for i, letter in enumerate(guess):
            if letter not in yellow_letters and letter not in self.letters_idx.values():
                self.disallowed_letters.append(letter)
        
        for i, letter in enumerate(yellow_letters):
            if letter not in self.required_letters:
                self.required_letters.append(letter)     

        self.regex_pattern = self._generate_regex_pattern()   

    def test_search(self, actual_word):
        """Assuming a known word, predicts a word and submits it as a guess. Repeats until the word is found.
        Returns the number of guesses required to find the word. Mostly for testing purposes."""
        guess = self.predict_best_word()
        if guess == actual_word:
            print(f"Found the word: {guess}")
            return len(self.guesses)+1
        elif guess is None:
            print(f"No possible answers found for query {actual_word}")
            return None
        response, yellow_letters = self._validate_guess(guess, actual_word)
        # print(f"Guess: {guess}, Response: {response}, Yellow Letters: {yellow_letters}")
        self.submit_guess(guess, response, yellow_letters)
        return self.test_search(actual_word)
    
    def _generate_regex_pattern(self):
        """Generates a regex pattern based on the known letters and disallowed letters."""
        pattern = ''
        for i in range(5):  # Assuming a 5-letter word
            if i in self.letters_idx and self.letters_idx[i]:
                # Add the known letter for this position
                pattern += self.letters_idx[i]
            else:
                # For positions without a known letter, add a pattern considering disallowed letters
                disallowed_list = self.disallowed_letters_idx.get(i, []) + self.disallowed_letters
                disallowed_str = ''.join(disallowed_list)
                pattern += f'[^{disallowed_str}]' if disallowed_str else '.'

        # Compile the regex pattern
        return re.compile(pattern)

    def _find_previous_wordle_answers(self, enable=True, url="https://www.rockpapershotgun.com/wordle-past-answers", keyword="All Wordle answers"):
        """Finds the previous answers from the website. Optionally, disable this feature."""
        if not enable:
            return []
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()
            start_idx = text.find(keyword)
            end_idx = text.find("Wordle doesn't repeat words")
            if start_idx != -1:
                past_answers = text[start_idx:end_idx].replace(keyword, "").strip().lower().split("\n")
                return past_answers
            else:
                return "Keyword not found."
        except requests.RequestException as e:
            return f"An error occurred: {e}"
    
    def _find_possible_answers(self):
        """Finds the possible answers from the loaded word frequencies."""
        possible_answers = list(self.word_frequencies.keys())
        allowed_answers = [
            answer for answer in possible_answers
            if (self.regex_pattern is None or self.regex_pattern.fullmatch(answer))
            and all(letter in answer for letter in self.required_letters)
            and answer not in self.previous_answers
            and answer not in self.guesses
        ]
        return allowed_answers
    
    def _find_allowed_answers(self):
        """Finds the allowed answers based on the known letters, disallowed letters, and previous answers."""
        allowed_answers = self._find_possible_answers()
        
        allowed_answers = [
            answer for answer in allowed_answers
            if (self.regex_pattern is None or self.regex_pattern.fullmatch(answer))
            and all(letter in answer for letter in self.required_letters)
            and answer not in self.previous_answers
            and answer not in self.guesses
        ]
        
        return allowed_answers

    def _compute_letter_frequencies(self, possible_answers=None):
        """Computes the letter frequencies of the possible answers, taking into account the known letters, disallowed letters, and previous answers."""
        if possible_answers is None:
            possible_answers = self._find_allowed_answers()
        letter_frequency = [dict() for _ in range(5)]
        for answer in possible_answers:
            for i, letter in enumerate(answer):
                if letter in letter_frequency[i]:
                    letter_frequency[i][letter] += 1
                else:
                    letter_frequency[i][letter] = 1
        return letter_frequency
    
    def _score_word(self, word, position_letter_frequencies):
        """Scores the word based on the letter frequencies of the possible answers. 
        Higher score means the word is more representative of the possible answers,
        which is useful for eliminating possible answers."""
        score = 0
        for i, letter in enumerate(word):
            score += position_letter_frequencies[i].get(letter, 0)
        return score

    def _validate_guess(self, guess, actual_word):
        """Validates the guess (if you know the actual word) and returns the response and yellow letters."""
        response = ''.join([g if g == a else '_' for g, a in zip(guess, actual_word)])
        yellow_letters = ''.join(set(g for g, a in zip(guess, actual_word) if g != a and g in actual_word))
        return response, yellow_letters

    def _get_word_frequency(self, word):
        """Get the frequency of a word using the Datamuse API."""
        _wait = 0.05
        max_retries = 5  # Maximum number of retries
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Parameterized query for better readability and security
                params = {'sp': word, 'md': 'f', 'max': 1}
                response = requests.get('https://api.datamuse.com/words', params=params).json()

                # If the response is empty, return a frequency of 0.0
                if not response:
                    return 0.0

                # Extract frequency from the response
                freq_tag = response[0].get('tags', [])
                freq = float(freq_tag[0][2:]) if freq_tag else 0.0
                return freq

            except requests.RequestException as e:
                print(f"Request error: {e}. Sleep and retry...")
                time.sleep(_wait)
                retry_count += 1

        print("Max retries reached. Returning a frequency of 0.")
        return 0.0
