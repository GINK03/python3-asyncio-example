import asyncio
import time
import profile
import random
async def calc(x):
    r = 0
    for i in range(10**7):
        if random.random() < 0.99:
            r += i % x
    return r

async def main():
    r = await asyncio.gather(*[calc(i) for i in range(1, 16)])
    print(r)

start = time.time()
asyncio.run(main())
elapsed = time.time() - start
print(elapsed)
