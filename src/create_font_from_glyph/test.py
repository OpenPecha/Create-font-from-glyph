import re

text = "This is a test string with some numbers 1234 and some special characters !@#$%^&*()_+"

def clean_test(text):
    return re.sub(r'[^a-zA-Z0-9 ]', '', text)

