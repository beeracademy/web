from random import Random


def is_shuffle_indices_valid_for_players(shuffle_indices, player_count):
    n = 13 * player_count
    if len(shuffle_indices) + 1 != n:
        return False

    for i, v in zip(range(n - 1, 0, -1), shuffle_indices):
        if not (0 <= v <= i):
            return False

    return True


def generate_shuffle_indices(n, random_seed=None):
    random = Random(random_seed)
    shuffle_indices = []
    for i in range(n - 1, 0, -1):
        shuffle_indices.append(random.randint(0, i))
    return shuffle_indices


def generate_shuffle_indices_for_players(player_count, random_seed=None):
    return generate_shuffle_indices(player_count * 13, random_seed)


def shuffle_with_indices(lst, shuffle_indices):
    n = len(lst)
    assert len(shuffle_indices) + 1 == n

    for i in range(n - 1, 0, -1):
        j = shuffle_indices[n - 1 - i]
        lst[i], lst[j] = lst[j], lst[i]
