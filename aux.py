import time
import random

def send_keys_naturally(element, text):
    for char in text:
        time.sleep(random.uniform(0.1, 0.3))  # delay between key presses
        element.send_keys(char)