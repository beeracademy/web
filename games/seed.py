from random import Random


def is_seed_valid_for_players(seed, player_count):
    n = 13 * player_count
    if len(seed) + 1 != n:
        return False

    for i, v in zip(range(n - 1, 0, -1), seed):
        if not (0 <= v <= i):
            return False

    return True


def generate_seed(n, random_seed=None):
    random = Random(random_seed)
    seed = []
    for i in range(n - 1, 0, -1):
        seed.append(random.randint(0, i))
    return seed


def generate_seed_for_players(player_count, random_seed=None):
    return generate_seed(player_count * 13, random_seed)


def shuffle_with_seed(l, seed):
    n = len(l)
    assert len(seed) + 1 == n

    for i in range(n - 1, 0, -1):
        j = seed[n - 1 - i]
        l[i], l[j] = l[j], l[i]
