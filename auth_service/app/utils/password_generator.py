import random
import string as s


def generate_password(num: int = 10):
    alphabet = s.digits + s.ascii_letters + s.hexdigits + s.punctuation
    res = str()

    for _ in range(num):
        res += random.choice(alphabet)

    return res