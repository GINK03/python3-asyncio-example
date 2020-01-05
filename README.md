# PythonのasyncioとThreadingでベンチを取ったらasyncioがThreadingに圧勝した

## 1. 😇
新年あけましておめでとうございます。  

しばらく何も投稿していなかったのですが、心身が安定し、やるべきことをやっていくぞ、という気持ちに少しなれています。この気持を高めていって、いろいろアチーブしたいです。。。😇

Python 3.6で色々知識が止まっていたので、年末年始を利用してPython3.8に上げるととも様々な組み込み関数の更新や、今までキャッチアップできていなかった機能について調べていきました。  

Python 3.7 ~ 3.8では、最近流行りのcoroutineのasyncio関連の関数がPythonにて成熟して普段遣いに良さそうな関数と記法が揃ってきています。

よく並列化という文脈でasyncioとThreadingは同様のもののように語られますが、使い方と想定する状況と設計が大きく違うし、後述のベンチマークではパフォーマンスも大きく違うことがわかりました。  

## 2. asyncioとThreadingの違いとはなに？
　英文になりますが[この記事](http://masnun.rocks/2016/10/06/async-python-the-different-forms-of-concurrency/)が大変わかりやすかったです。  

### Threadingについて

上記のリンクを参考にすると、このようなことが言われています。（読むのがめんどくさい人はGoogle翻訳を使いましょう）

> Threads & Processes
Python has had Threads for a very long time. Threads allow us to run our operations concurrently. But there was/is a problem with the Global Interpreter Lock (GIL) for which the threading could not provide true parallelism. However, with multiprocessing, it is now possible to leverage multiple cores with Python

> Global Interpreter Lock (GIL)
The Global Interpreter Lock aka GIL was introduced to make CPython’s memory handling easier and to allow better integrations with C (for example the extensions). The GIL is a locking mechanism that the Python interpreter runs only one thread at a time. That is only one thread can execute Python byte code at any given time. This GIL makes sure that multiple threads DO NOT run in parallel.  
Quick facts about the GIL:  
One thread can run at a time.  
The Python Interpreter switches between threads to allow concurrency.  
The GIL is only applicable to CPython (the defacto implementation). Other implementations like Jython, IronPython don’t have GIL.  
GIL makes single threaded programs fast.  
For I/O bound operations, GIL usually doesn’t harm much.  
GIL makes it easy to integrate non thread safe C libraries, thansk to the GIL, we have many high performance extensions/modules written in C.
For CPU bound tasks, the interpreter checks between N ticks and switches threads. So one thread does not block others.
Many people see the GIL as a weakness. I see it as a blessing since it has made libraries like NumPy, SciPy possible which have taken Python an unique position in the scientific communities.


このようにもとのもとGILという仕組みでPythonとC言語系との連携が可能になり、numpyなscipyなどのライブラリという祝福はありましたが真の並列処理を提供できなかったとあります。  

現行のThreadingはGILの成約の中で、処理を次々に切り替えながら処理するような方法をとっているようです。  

### ayncioについて

> What is asyncio?
Asyncio provides us an event loop along with other good stuff. The event loop tracks different I/O events and switches to tasks which are ready and pauses the ones which are waiting on I/O. Thus we don’t waste time on tasks which are not ready to run right now.

ThreadingはN tickという方式で計算リソースを平等に割り当てますが、ayncioはioの関係で準備ができていないものには計算リソースを割り当てず、逆に処理できるものから処理していくというもであることがわかります。

> The idea is very simple. There’s an event loop. And we have functions that run async, I/O operations. We give our functions to the event loop and ask it to run those for us. The event loop gives us back a Future object, it’s like a promise that we will get something back in the future. We hold on to the promise, time to time check if it has a value (when we feel impatient) and finally when the future has a value, we use it in some other operations.

Futureオブジェクトという将来値を取り出せるオブジェクト（つまり、その時点で計算中かio待ちのオブジェクト）を引き回して後で取り出すというユースケースがありそうです。よくイベントループは通信など品質が安定しないものに適していると言われていますが、nginxもイベントループで動いていると言うし、io待ちが発生するようなものとは相性が良さそうです。 

ふむふむ、よーく理解できました。  

web brawserなどやソシャゲーのバックエンドなどはThreadingよりこのasyncioで設計したほうが効率が良さそうです。  


## 単純な疑問、ioとかあんまり考えなくても普通の並列計算でasyncioとThreadingはどっちがいいの？

asyncioの記法は少々特殊で関数の前に、`async` をつけて Futureオブジェクト的なものから値を取り出すときに `await` をつける記法になっています。  

```python
import asyncio
async def calc(x): # <- この関数は非同期で実行する
    r = 0
    for i in range(10**7): # <- 適当な重い計算
        r += i % x
    return r

async def main():
    r = await asyncio.gather(*[calc(i) for i in range(1, 16)]) # <-　ここで 並列処理させて結果を取得
    print(r)
```

ブロッキングアーキテクチャになれきった身としては普段使いするには少々トレーニングが必要です。Threadingよりasyncioがいいのであれば、Threadingを忘れてasyncioに流れたいのですが、どの程度の実用性があるのでしょうか？

## ベンチマーク
実際に計測します。
計算は、1 ~ 15の値で 0 ~ 10^7までの数字の modulo をとった値の和を与えます。randomで 1%の確率で計算をスキップします。

ベンチマークを取ったコンピュータは家の `Intel(R) Core(TM) i7-7820X CPU @ 3.60GHz` になります。中身はXeonなのでそこそこ早いはず。  
Pythonのバージョンやコンパイルは以下の通りです。

```
Python 3.7.4 (default, Dec 29 2019, 22:54:23)
[GCC 9.2.1 20191008] on linux
```

### Threading
**コード**

```python
import time
import profile
from concurrent.futures import ThreadPoolExecutor as TPE
import random
def calc(x):
    r = 0
    for i in range(10**7):
        if random.random() < 0.99:
            r += i % x
    return r

def main():
    with TPE(max_workers=16) as exe:
        r = [r for r in exe.map(calc, list(range(1, 16)))]
    print(r)

start = time.time()
main()
elapsed = time.time() - start
print(elapsed)
```
**5回の試行結果** 

```
1回目: 65.97[s]
2回目: 63.55[s]
3回目: 64.57[s]
4回目: 63.69[s]
5回目: 64.92[s]
```
**CPU使用の状況**
<div align="center">
    <img width="100%" src="https://www.dropbox.com/s/tgms7ytv66zpgub/%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%BC%E3%83%B3%E3%82%B7%E3%83%A7%E3%83%83%E3%83%88%202020-01-05%2016.29.26.png?raw=1">
    <div> 図1. 全然CPUを本気で使ってくれない </div>
</div> 

### asyncio

**コード** 

```python
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
```

**5回の試行結果** 

```
1回目: 17.30[s]
2回目: 17.47[s]
3回目: 17.14[s]
4回目: 17.10[s]
5回目: 17.09[s]
```

**CPU使用の状況**
<div align="center">
    <img width="100%" src="https://www.dropbox.com/s/2rzkkusel932dln/%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%BC%E3%83%B3%E3%82%B7%E3%83%A7%E3%83%83%E3%83%88%202020-01-05%2016.21.48.png?raw=1">
    <div> 図2. 1のCPU(正確にはthread)を100%使っている </div>
</div> 

## Multiprocessing
**コード**

```python
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
```

**5回の試行結果** 

```
1回目: 2.78[s]
2回目: 2.69[s]
3回目: 2.71[s]
4回目: 2.78[s]
5回目: 2.68[s]
```
**CPU使用の状況**
<div align="center">
    <img width="100%" src="https://www.dropbox.com/s/w2ugpzgsdkaak4e/%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%BC%E3%83%B3%E3%82%B7%E3%83%A7%E3%83%83%E3%83%88%202020-01-05%2016.30.45.png?raw=1">
    <div> 図3. 完全にCPUを使用している </div>
</div> 

### ブロッキング
通常の並列処理を挟まない処理です。 
**コード**  

```python
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
```
**5回の試行結果** 

```
1回目: 18.28[s]
2回目: 17.39[s]
3回目: 17.28[s]
4回目: 17.23[s]
5回目: 17.92[s]
```
わずかにasyncioより遅い（ので、一応この例であってもasncioで非同期処理する意味がある）

## わかったこと
random関数か算術自体になにかブロッキング性があるのか、asyncioとThreadとで３倍以上とすごい差が出ました。 
ThreadはCPU使用率がまるで上がらず、効率が悪いことがわかります。またasyncio自体が1processで完結しているので1CPUの範囲内で消費するのは正しいのですが、正しく100%リソースを活用できているあたり、すごいです。(MultiprocessingはSpawnやForkしているので一番早いのはしょうがない)  
Multiprocessingはグローバル変数や特定の状態の共有が基本できないか難しいなどの成約があり、Thread的なアプローチで並列化する必要があるときはもうasyncioでいいかもしれません。

## 再現性
ベンチマークに使ったコードは[ここ](https://github.com/GINK03/python3-asyncio-example)においてあります

## Appendix. 個人的に好きなasyncioの書き方
これ系のライブラリはとにかく書き方やデザインパターンが安定しないので、一つ確実に使えて多くのユースケースで適応できる書き方を正しく体得しておくとよいです。  

個人的にはこのように、最初にTaskオブジェクト(Futureとほぼ同じ)を取り出して、必要になったらawaitをかけるとかが美しいし効果的かと思います。  

```python
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
    tasks = [asyncio.create_task(calc(i)) for i in range(1, 16)]
    # この書き方がmainの中のthreadも進行できて良い
    # ここになにか処理を書くのがasyncioのプラクティス
    r = [await task for task in tasks]
    print(r)

start = time.time()
asyncio.run(main())
elapsed = time.time() - start
print(elapsed)
```