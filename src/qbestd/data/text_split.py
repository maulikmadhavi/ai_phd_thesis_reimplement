"""Text-disjoint train/test splits ``textdisjoint_q20_v1``/``_v2``.

The Hugging Face TIMIT split is per utterance, so most test sentences also
occur in train. The official TIMIT split never shares a non-SA text across
train and test. This module builds a separately named split in which every
distinct (normalised) sentence text is on one side only, using transcripts,
the thesis keyword table (``Table:TIMITdata``) and the official quotas only.

Rule (declared before any score is computed on it, never redrawn; any change
becomes a new name with a written reason):

1. *Universe*: every non-SA row of both HF splits, keyed by
   ``(hf_split, row_index)``. Rows are grouped by the normalised text; the
   group hash is ``sha256("qbestd-textsplit-v1\\n" + text)``.
2. *Keyword constraints*. Keywords that share a group (for example
   "meeting" and "tomorrow") form a connected component; components are
   processed in table order of their first keyword. For a component, every
   assignment of all its groups is enumerated; the cost is the sum over its
   keywords of ``|test tokens - Occ| + |train tokens - Inst|``. The minimum
   cost wins; ties go to the lexicographically smallest sorted tuple of the
   test-side hashes over the component's groups. The winner is fixed.
   The report counts, per component, how many assignments reach the
   minimum cost (``n_min_assignments``); a count above 1 means the winner
   was picked by the tie-break alone.
   (A first draft decided one keyword at a time; it left "tomorrow" at
   cost 8 because "meeting" fixed their shared group first.)
3. *Quotas*: the test side holds 120 multi-read and 504 single-read groups.
   The remaining test groups are the untouched groups in ascending hash
   order within each stratum. Every other group is train. If step 2 already
   exceeds a quota, nothing is moved and the shortfall is reported.

``textdisjoint_q20_v2`` adds one step between 1 and 2 (reason: "variant
groups split SX texts across sides (found in review)"):

1b. *Merge variant links*. ``V2_VARIANT_LINKS`` (``text_variants.py``) is an
   explicit list of pairs of v1 group hashes, each a verified one-token
   transcript variant of the same sentence. The connected components of
   those links are *units*; a unit's key (used for the tie-break, the step 3
   order and the manifest ``group_hash``) is its smallest member hash. The
   hash prefix stays v1, so the links name existing v1 hashes. Steps 2 and
   3 then work on units; a unit is multi-read when it holds several rows.
"""

import argparse
import hashlib
from dataclasses import dataclass
from itertools import product
from pathlib import Path

from qbestd.data.feature_cache import is_sa_sentence
from qbestd.data.text_variants import MAX_UNIT_ROWS, V2_VARIANT_LINKS
from qbestd.data.timit_hf import normalize_transcript

RULE = "textdisjoint_q20_v1"
RULE_V2 = "textdisjoint_q20_v2"
RULES = {"v1": RULE, "v2": RULE_V2}
HASH_PREFIX = "qbestd-textsplit-v1\n"
TEST_QUOTA = {"multi": 120, "single": 504}
MAX_FREE_GROUPS = 16
HEADER = ("hf_split", "row_index", "side", "group_hash")
DEFAULT_DIR = Path("outputs/splits")
DEFAULT_PATH = DEFAULT_DIR / f"{RULE}.tsv"


@dataclass(frozen=True, order=True)
class ManifestRow:
    hf_split: str
    row_index: int
    side: str  # "train" or "test"
    group_hash: str


@dataclass(frozen=True)
class SplitManifest:
    """Rows sorted by ``(hf_split, row_index)`` plus the build report."""

    rule: str
    rows: tuple
    report: dict

    def side_rows(self, hf_split, side):
        """Set of row indices of ``hf_split`` on ``side``."""
        return {r.row_index for r in self.rows
                if r.hf_split == hf_split and r.side == side}


def group_hash(text):
    return hashlib.sha256((HASH_PREFIX + text).encode("utf-8")).hexdigest()


def _build_groups(rows):
    """``{hash: {"tokens", "rows", "variants"}}`` over the non-SA rows.

    ``variants`` lists ``(tokens, number of rows)`` per transcript variant
    of the entry (one item for a group, several for a merged unit)."""
    groups = {}
    for hf_split, row_index, sentence in rows:
        tokens = normalize_transcript(sentence)
        if is_sa_sentence(tokens):
            continue
        entry = groups.setdefault(group_hash(" ".join(tokens)),
                                  {"tokens": tokens, "rows": []})
        entry["rows"].append((hf_split, row_index))
    for entry in groups.values():
        entry["rows"].sort()
        entry["variants"] = [(entry["tokens"], len(entry["rows"]))]
    return groups


def _merge_units(groups, links):
    """Step 1b: merge linked groups into units keyed by the smallest hash.

    Raises:
        ValueError: for a link that is not a sorted pair, that names an
            unknown hash, or that makes a unit of more than
            ``MAX_UNIT_ROWS`` rows.
    """
    parent = {h: h for h in groups}

    def find(h):
        while parent[h] != h:
            parent[h] = parent[parent[h]]
            h = parent[h]
        return h

    for first, second in links:
        if not first < second:
            raise ValueError(f"link {first[:12]} / {second[:12]} is not a "
                             "sorted pair of distinct hashes")
        for h in (first, second):
            if h not in groups:
                raise ValueError(f"link names unknown group hash {h[:12]}")
        parent[find(second)] = find(first)
    members = {}
    for h in groups:
        members.setdefault(find(h), []).append(h)
    units = {}
    for found in members.values():
        key = min(found)
        rows = sorted(r for h in found for r in groups[h]["rows"])
        if len(rows) > MAX_UNIT_ROWS:
            raise ValueError(f"unit {key[:12]} has {len(rows)} rows, more "
                             f"than {MAX_UNIT_ROWS}")
        units[key] = {"tokens": groups[key]["tokens"], "rows": rows,
                      "variants": [v for h in sorted(found)
                                   for v in groups[h]["variants"]]}
    return units


def _stratum(group):
    return "multi" if len(group["rows"]) > 1 else "single"


def _count(group, keyword):
    """Keyword tokens a group or unit contributes: occurrences times rows,
    summed over its transcript variants."""
    return sum(tokens.count(keyword) * n for tokens, n in group["variants"])


def _components(keywords, groups):
    """Keyword components (lists of table entries) and their group hashes.

    Two keywords are connected when some group contains both. Components
    follow the table order of their first keyword; entries inside keep
    table order.
    """
    members = {name: {h for h, g in groups.items() if _count(g, name)}
               for name, _, _ in keywords}
    components, assigned = [], set()
    for entry in keywords:
        if entry[0] in assigned:
            continue
        found, todo = set(), [entry[0]]
        while todo:
            name = todo.pop()
            if name in found:
                continue
            found.add(name)
            todo += [other for other, _, _ in keywords
                     if other not in found and members[name] & members[other]]
        assigned |= found
        chosen = [e for e in keywords if e[0] in found]
        components.append((chosen, set().union(*[members[n] for n in found])))
    return components


def _choose(component, hashes, groups, side):
    """Step 2 for one component; updates ``side``.

    Returns ``(cost per keyword, n_min)``: ``n_min`` is how many of the
    component's assignments reach the minimum summed cost (one count per
    component, not per keyword). The winner is chosen by the tie-break
    alone.
    """
    free = sorted(hashes)
    if len(free) > MAX_FREE_GROUPS:
        names = ", ".join(name for name, _, _ in component)
        raise ValueError(f"{names}: {len(free)} groups is too many to "
                         f"enumerate (limit {MAX_FREE_GROUPS})")
    best, min_cost, n_min = None, None, 0
    for choice in product(("train", "test"), repeat=len(free)):
        trial = dict(zip(free, choice))
        costs = {}
        for name, inst, occ in component:
            test = sum(_count(groups[h], name) for h in free
                       if trial[h] == "test")
            train = sum(_count(groups[h], name) for h in free
                        if trial[h] == "train")
            costs[name] = abs(test - occ) + abs(train - inst)
        ties = tuple(h for h in free if trial[h] == "test")
        total = sum(costs.values())
        if min_cost is None or total < min_cost:
            min_cost, n_min = total, 1
        elif total == min_cost:
            n_min += 1
        key = (total, ties)
        if best is None or key < best[0]:
            best = (key, trial, costs)
    side.update(best[1])
    return best[2], n_min


def _fill_quotas(groups, side):
    """Step 3; returns the quota report."""
    placed = {"multi": 0, "single": 0}
    for h, which in side.items():
        if which == "test":
            placed[_stratum(groups[h])] += 1
    report = {}
    for stratum, quota in TEST_QUOTA.items():
        free = sorted(h for h in groups
                      if h not in side and _stratum(groups[h]) == stratum)
        need = quota - placed[stratum]
        report[stratum] = {"quota": quota, "from_step_2": placed[stratum],
                           "added": max(0, min(need, len(free)))}
        if need < 0:
            report[stratum]["exceeded_by"] = -need
        if need > len(free):
            report[stratum]["short_by"] = need - len(free)
        for h in free[:max(0, need)]:
            side[h] = "test"
    for h in groups:
        side.setdefault(h, "train")
    return report


def build_text_split(rows, keywords, rule=RULE, links=None):
    """Build the manifest from ``rows`` of ``(hf_split, row_index, sentence)``.

    ``keywords`` is a sequence of ``(name, Inst., Occ.)`` in table order.
    ``rule`` is ``RULE`` (v1, no links) or ``RULE_V2``; ``links`` defaults
    to none for v1 and to ``V2_VARIANT_LINKS`` for v2. The result does not
    depend on the order of ``rows`` or of ``links``.
    """
    if links is None:
        links = V2_VARIANT_LINKS if rule == RULE_V2 else ()
    groups = _build_groups(rows)
    n_variant_groups = len(groups)
    groups = _merge_units(groups, links)
    side, costs, components = {}, {}, []
    for component, hashes in _components(keywords, groups):
        found, n_min = _choose(component, hashes, groups, side)
        costs.update(found)
        components.append({"keywords": [name for name, _, _ in component],
                           "n_groups": len(hashes),
                           "cost": sum(found.values()),
                           "n_min_assignments": n_min})
    quotas = _fill_quotas(groups, side)
    manifest_rows = sorted(
        ManifestRow(split, index, side[h], h)
        for h, g in groups.items() for split, index in g["rows"])
    report = {"quotas": quotas, "costs": costs, "components": components,
              "n_groups": len(groups), "n_variant_groups": n_variant_groups,
              "n_links": len(links),
              "keyword_tokens": {
                  name: {which: sum(_count(g, name) for h, g in
                                    groups.items() if side[h] == which)
                         for which in ("train", "test")}
                  for name, _, _ in keywords}}
    return SplitManifest(rule, tuple(manifest_rows), report)


def manifest_bytes(manifest):
    lines = [f"# rule={manifest.rule}", "\t".join(HEADER)]
    lines += [f"{r.hf_split}\t{r.row_index}\t{r.side}\t{r.group_hash}"
              for r in manifest.rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_split_manifest(path, manifest):
    """Write the TSV (LF endings on every platform; no sentence text)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(manifest_bytes(manifest))


def read_split_manifest(path):
    """Read a file written by :func:`write_split_manifest`.

    The ``report`` of the returned manifest is empty.
    """
    lines = Path(path).read_bytes().decode("utf-8").splitlines()
    if not lines or not lines[0].startswith("# rule="):
        raise ValueError(f"{path}: missing '# rule=' header")
    if tuple(lines[1].split("\t")) != HEADER:
        raise ValueError(f"{path}: unexpected columns {lines[1]!r}")
    rows = tuple(ManifestRow(f[0], int(f[1]), f[2], f[3])
                 for f in (line.split("\t") for line in lines[2:]))
    return SplitManifest(lines[0][len("# rule="):], rows, {})


def split_id(path):
    """``<rule>-<first 12 hex of the file sha256>``."""
    rule = read_split_manifest(path).rule
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return f"{rule}-{digest[:12]}"


def main(argv=None):
    """Build the manifest from the cached HF sentences and write it."""
    from qbestd.data.timit_hf import download_timit_parquet, read_sentences
    from qbestd.eval.timit_queries import Q20_KEYWORDS
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--rule", choices=sorted(RULES), default="v1")
    parser.add_argument("--out", type=Path, default=None,
                        help="default: outputs/splits/<rule>.tsv")
    args = parser.parse_args(argv)
    rule = RULES[args.rule]
    out = args.out or DEFAULT_DIR / f"{rule}.tsv"
    rows = [(split, index, sentence)
            for split in ("train", "test")
            for index, sentence in enumerate(
                read_sentences(download_timit_parquet(split)))]
    manifest = build_text_split(rows, Q20_KEYWORDS, rule=rule)
    write_split_manifest(out, manifest)
    print(split_id(out), len(manifest.rows), "rows")
    print(manifest.report["quotas"])


if __name__ == "__main__":
    main()
