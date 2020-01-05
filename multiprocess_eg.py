import time
import profile
from concurrent.futures import ProcessPoolExecutor as PPE
import random
def calc(x):
    r = 0
    for i in range(10**7):
        if random.random() < 0.99:
            r += i % x
    return r

def main():
    with PPE(max_workers=16) as exe:
        r = [r for r in exe.map(calc, list(range(1, 16)))]
    print(r)

start = time.time()
main()
elapsed = time.time() - start
print(elapsed)
