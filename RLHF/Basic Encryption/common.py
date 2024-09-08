import random 

def generate_character(start_char, stop_char):
    for char in range(ord(start_char), ord(stop_char)):
        for char in range(ord(start_char), ord(stop_char) + 1):
            yield chr(char) 
        

    
def generate_one_time_pad(n_chars, characters):
    return ''.join(random.choice(characters) for _ in range(n_chars))

lower_case = list(generate_character('a', 'z'))
upper_case = list(generate_character('A', "Z"))

punctuation = ['.', ',', ' ', '?', '!']

alphabet = lower_case + upper_case + punctuation 

