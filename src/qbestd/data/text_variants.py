"""One-token transcript variants for the split ``textdisjoint_q20_v2``.

Some TIMIT SX sentences appear in two transcript variants that differ by
one token ("will" against "would", a missing "the"). Grouping by exact text
(v1) puts such variants on opposite sides of the split. This module finds
candidate pairs by a one-token edit and holds the explicit, verified list of
links that v2 merges (``V2_VARIANT_LINKS``).

The finder only *proposes*. The committed list is what a human check of the
full transcripts and row counts kept; it never grows by a general rule.
"""

from collections import defaultdict
from dataclasses import dataclass

# An SX sentence is read by 7 speakers, so a unit of variants of one
# sentence cannot hold more rows than that.
MAX_UNIT_ROWS = 7

# Explicit links between v1 group hashes (see ``docs/split_textdisjoint.md``
# for the evidence of each). Each pair is sorted, and so is the tuple.
V2_VARIANT_LINKS = (
    ("0164a42a74865470aedfa01f6ee065a069d03a137d9d7ec661a76894e3e36b11",
     "40b189a45527d06b58971623efa17e9da234f71e1f7f7e0c060ca199b572a16b"),
    ("0609435b34ca1e4da90698bedd3385ebd115328527f366a6ed31edab54f60f92",
     "a3b42edc22f2f4947428b5279f78597bc3baf42b8a95bffe97f069c2334bfce2"),
    ("0984b6229f40df08ae12e125aafaa44b966809c67017a1e00ba32a2165a07738",
     "cf064136a3b7125ff7b14f229c436b87da1d277ff005fa046e2771c213cc9898"),
    ("09e46dbdc06ba06cbfbf03035267bcce9985b385c195ec7c1a84975e5b1f1f17",
     "55b771c503e3b03946d8622a8f193bd4eec7ce2edb87e43856a40fc9c1647c7b"),
    ("24181c08ebc9ab5f6927fc334fe478ac33f0b85e2cfd0264e7b2c776d7d087f4",
     "cb69f301723241053c034550c48b65386006caee2ec383245d42956bd88eb294"),
    ("24a69ee847258bab6daac25aa8df66df9df5553a58fb0737b0555afff91dd4ee",
     "4f59ccc36397d7a864abcaa7a7fdd9e19226d5856438be05d0a6c7e3d5bdab4f"),
    ("31820500b0cc091c06486cc960ec81952927f9d401992d0b15d38acfeafa607f",
     "88de70720b33709aa8d78b3909c4642f740e3b86d91ba3f50b7d659164cf1181"),
    ("3b70f551e88939c8b7259a1230c021bd2f547c06d49fe51596a9a33e6b7d5142",
     "f07866806318af5115dc491b137d3ba2e62e2ebd42e0c40c366929d7eadc11bb"),
    ("3b70f551e88939c8b7259a1230c021bd2f547c06d49fe51596a9a33e6b7d5142",
     "f43bec409d4ae44f4acd4cf910f8892379a6ca9ae2fae4b53e6065d37a0c86a3"),
    ("4566ad641f695669546a71edad006bdf751a85fe7cd50bff25bc7c38bb38522c",
     "a4946f5c51ed6028fdf6435c1335f04063db99465561c30f2a5673d490c1223c"),
    ("45c072ef7c8fc773bb83308b20b52fbfc7feb51d39bf6bf6d8dc03d8176944dd",
     "6f0ab47a079ff81f14485d55453bbfcf073da856456503f2363f3371683d7909"),
    ("5302e3537839119c196dc546cfa8e1040e505a2041e4a8132577861dcab87170",
     "5979ddfeda1d0b2a5c54100cef4b349436b913c26cdf87f365b1ce0a008e8607"),
    ("5f6365c9433a51cea878d8cdcaf5779dd9536ba519d78b48587b6e9fb28628ff",
     "f84e16c77e75751f96f1bab904b46443732bf75ef3a3c4a05c7c7162b23dfd58"),
    ("62b22fe30ad9db3b2102d7558a2f456dc7f579a8a2b2702fe8132cce3a117881",
     "f281b1ceff7c651cebd92c1bd597e18b788b9d31d008094fdfcdc3cefa88b41e"),
    ("845b65478f45c29cc22b3916e55e0eda9dcc4228870658ff34e87938398d0ef9",
     "ff100ae27314541d4d6507535e3640dc55b1f0345d94beb53452e14658459de0"),
    ("a0435d4e88962e38829a660ccba18e2080d8c49b3a42a01783109cc5c24e51e8",
     "e69015b9d66ae8921aa58ebab96e14fc9b555547b6ba98fbfd38b4785ab9f4bd"),
    ("ca48eb2f5435c558f5374d3bf4705f91fbe387c7d4877be54a1472081fdc17de",
     "fe03851b0532dd5fbc2bb1a4446249651abe4656c7eac62d200b55e28b579805"),
    ("caccbb974bedbe82182eafa4eb41803ad8aa67737d0be9864079e8858cad3b7d",
     "e44f9c30a8b608d6b58356291a93c16a108fe0df48cf1693a56301019739b638"),
    ("cc396d7f8b839c7c60e515bd88c438a727dec9ffae5d1db07b043194ffacc940",
     "f33def961554d75aff9de5ede2c67436394706bdff3e41b4a0e02e2152ea5177"),
    ("ee0def7dd93473e4cc7df8a43a2b8acb819d4be0768e74f66fe0499b2f954227",
     "f80fe9ac2666560d35539f0541d85bbacbc887d98fa82b79a74f3ce5bfe17d79"),
)


@dataclass(frozen=True, order=True)
class VariantCandidate:
    """A proposed pair; ``hash_a < hash_b``.

    ``edit`` is relative to ``hash_a``: ``insertion`` means ``hash_b`` has
    one extra token, ``deletion`` that it lacks one, ``substitution`` that
    one token differs. ``token`` is the differing token (``"x/y"`` for a
    substitution, ``a``'s token first).
    """

    hash_a: str
    hash_b: str
    edit: str
    token: str
    rows_a: int
    rows_b: int


def one_edit(tokens_a, tokens_b):
    """``(edit, token)`` when the sequences differ by one token, else None.

    ``edit`` is ``substitution``, ``insertion`` (b has an extra token) or
    ``deletion`` (b lacks one), as in :class:`VariantCandidate`.
    """
    a, b = list(tokens_a), list(tokens_b)
    if a == b or abs(len(a) - len(b)) > 1:
        return None
    first = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y),
                 min(len(a), len(b)))
    if len(a) == len(b):
        if a[first + 1:] == b[first + 1:]:
            return "substitution", f"{a[first]}/{b[first]}"
        return None
    if len(b) == len(a) + 1:
        return ("insertion", b[first]) if a[first:] == b[first + 1:] else None
    return ("deletion", a[first]) if a[first + 1:] == b[first:] else None


def _neighbour_keys(tokens):
    """Keys shared by every sequence one substitution or one deletion
    away from ``tokens`` (or, for the short side, equal to it)."""
    tokens = tuple(tokens)
    keys = [("sub", i, tokens[:i], tokens[i + 1:])
            for i in range(len(tokens))]
    keys += [("del", tokens[:i] + tokens[i + 1:])
             for i in range(len(tokens))]
    return keys


def find_variant_candidates(groups, max_rows=MAX_UNIT_ROWS,
                            require_multi=True):
    """Pairs of groups one token apart, to be verified by hand.

    ``groups`` is ``{hash: {"tokens": [...], "rows": [...]}}``. A pair is
    proposed when the token sequences differ by exactly one substitution,
    insertion or deletion, at least one group is multi-read (more than one
    row) and the combined row count is at most ``max_rows``
    (``MAX_UNIT_ROWS``). The result is sorted. ``require_multi=False`` and a
    large ``max_rows`` lift the two filters, to count what they exclude.
    """
    by_sequence = defaultdict(list)
    by_key = defaultdict(list)
    for h, group in groups.items():
        by_sequence[tuple(group["tokens"])].append(h)
        for key in _neighbour_keys(group["tokens"]):
            by_key[key].append(h)
    pairs = set()
    for h, group in groups.items():
        tokens = tuple(group["tokens"])
        for key in _neighbour_keys(tokens):
            if key[0] == "sub":
                pairs.update((h, o) for o in by_key[key] if o != h)
            else:  # a longer group h, a shorter group equal to the key
                pairs.update((h, o) for o in by_sequence.get(key[1], ()))
    found = []
    for first, second in pairs:
        rows_first = len(groups[first]["rows"])
        rows_second = len(groups[second]["rows"])
        if rows_first + rows_second > max_rows:
            continue
        if require_multi and rows_first < 2 and rows_second < 2:
            continue
        a, b = sorted((first, second))
        edit = one_edit(groups[a]["tokens"], groups[b]["tokens"])
        if edit is None:
            continue
        found.append(VariantCandidate(a, b, edit[0], edit[1],
                                      len(groups[a]["rows"]),
                                      len(groups[b]["rows"])))
    return sorted(set(found))


def cross_side_candidates(groups, side_of):
    """Candidates whose two groups are on different sides.

    ``side_of`` maps a group hash to ``"train"`` or ``"test"``. Run on a
    finished split, it should be empty when every variant is linked.
    """
    return [c for c in find_variant_candidates(groups)
            if side_of[c.hash_a] != side_of[c.hash_b]]
