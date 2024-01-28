import requests
import pandas as pd
import numpy as np
import time

def get_word_frequency(word):
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

def main():
    """Main function, to populate a CSV file with word frequencies."""
    word_file_path = r'wordle-answers-alphabetical.txt' # Path to the word file
    output_file_path = 'word_frequencies.csv'

    try:
        # Read words into a DataFrame
        df = pd.read_csv(word_file_path, header=None, names=['word'])
        
        # Apply the function across rows
        df['frequency'] = df['word'].apply(get_word_frequency)

        # Save to CSV
        df.to_csv(output_file_path, index=False)
        print(f"CSV file created at {output_file_path}")

    except FileNotFoundError:
        print(f"File {word_file_path} not found.")

if __name__ == "__main__":
    main()