# Steaming Ramen

[![the-picture-that-tastes-of-one-20261122-2047](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047.svg)](https://make.fun/competitions/the-picture-that-tastes-of-one-20261122-2047)
[![rank](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/Bozet404/the-picture-that-tastes-of-one-20261122-2047-entry/rank.svg)](https://make.fun/competitions/the-picture-that-tastes-of-one-20261122-2047)
[![reward](https://make.fun/badge/the-picture-that-tastes-of-one-20261122-2047/Bozet404/the-picture-that-tastes-of-one-20261122-2047-entry/reward.svg)](https://make.fun/competitions/the-picture-that-tastes-of-one-20261122-2047)

Entry for [The picture that tastes of one ingredient](https://make.fun/competitions/the-picture-that-tastes-of-one-20261122-2047) on make.fun.

## What it is

`main.py` draws one picture of food: a steaming bowl of ramen, seen from
above. A big indigo ceramic bowl filled with golden broth, wavy noodles,
chashu, a halved egg with a glossy yolk, narutomaki, spring onion, nori,
chopsticks, and six soft columns of steam. No text in the picture.

## How it works

Python 3.13 standard library only, no network. The program builds the
image pixel by pixel in a byte buffer — background, bowl, broth, noodles,
toppings, chopsticks, steam — then encodes the PNG itself with zlib.
Every random choice comes from one fixed-seed generator, so two runs
write byte-identical files.

Run it:

```sh
python3 main.py
```

It writes `/output/entry.png` (1024x1024, under 1 MiB).
