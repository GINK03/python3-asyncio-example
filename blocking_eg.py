import asyncio
import time
import profile
import random
def calc(x):
    r = 0
    for i in range(10**7):
        if random.random() < 0.99:
            r += i % x
    return r

def main():
    r = [calc(i) for i in range(1, 16)]
    print(r)

start = time.time()
main()
elapsed = time.time() - start
print(elapsed)
