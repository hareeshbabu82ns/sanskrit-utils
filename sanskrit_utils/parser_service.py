"""Sanskrit analysis services built on ``sanskrit_parser`` and ``sanskrit_util``.

This module has no GraphQL in it: the resolvers in ``schema/sans_parser.py``
call these functions and shape the results. Everything is SLP1 internally;
``to_slp1`` / ``from_slp1`` sit at the edges.

Why this does not simply use ``sanskrit_parser.Parser``:

* ``Parser`` keeps the request's encodings on the (shared) instance, so one
  request can change another's output. Here every call takes its settings as
  arguments and the only shared, stateful piece (the sandhi analyzer) is
  guarded by a lock.
* Upstream's non-strict input normalisation rewrites anusvara before a
  semivowel into a nasalised semivowel (``saMyoga`` -> ``say~yoga``), a form
  the lexicon does not have; in strict mode it does not touch anusvara at all,
  so ``SuklAMbara`` never matches ``SuklAmbara``. ``normalize`` below replaces
  both with one rule that the lexicon agrees with.
* The splits ``Parser.split`` returns share their word objects, and
  ``Split.parse`` appends the word's tags to them on every call. Parsing a
  second split therefore sees every shared word's readings twice, the third
  three times, and the search grows to minutes. ``SplitAnalysis`` analyses
  each split on objects of its own, and under a time budget, since a long
  sentence can be slow on its own account.
"""
import contextlib
import contextvars
import os
import re
import threading
import time
from functools import cached_property
from urllib.parse import urlencode

from indic_transliteration import sanscript
from sanskrit_parser.base.maheshvara_sutra import MaheshvaraSutras
from sanskrit_parser.base.sanskrit_base import (SanskritImmutableString,
                                                SanskritObject)
from sanskrit_parser.parser import datastructures as _vakya
from sanskrit_parser.parser.datastructures import (
    VakyaGraph, k_shortest_paths_dag_optimized)
from sanskrit_parser.parser.sandhi_analyzer import LexicalSandhiAnalyzer
from sanskrit_parser.util import normalization
from sanskrit_parser.util.DhatuWrapper import DhatuWrapper
from sanskrit_util import sounds

SLP1 = sanscript.SLP1

# Limits that keep one request from tying up a worker.
MAX_TEXT_LENGTH = int(os.environ.get('MAX_TEXT_LENGTH', '1000'))
MAX_LIMIT = 100
MAX_JOIN_RESULTS = 100
# Candidate splits that are scored to pick the best `limit`: at least, at most.
SPLIT_POOL_MIN = 50
SPLIT_POOL_MAX = 2000
# Seconds the vakya analysis of one split may take, and of all splits of one
# `parse` query together.
PARSE_SPLIT_TIMEOUT = float(os.environ.get('PARSE_SPLIT_TIMEOUT', '10'))
PARSE_TOTAL_TIMEOUT = float(os.environ.get('PARSE_TOTAL_TIMEOUT', '30'))

# Loading the lexicons takes a few seconds; do it once, at import.
analyzer = LexicalSandhiAnalyzer()
# getSandhiSplits() keeps its working state on the analyzer instance.
_analyzer_lock = threading.Lock()
_maheshvara = MaheshvaraSutras()

LEXICONS = {
    'COMBINED': analyzer.forms,
    'INRIA': analyzer.forms.inria,
    'SANSKRIT_DATA': analyzer.forms.sanskrit_data,
}


class InputError(ValueError):
    """The request cannot be served as asked; the message is for the client."""


# --------------------------------------------------------------------------
# Encoding and normalisation
# --------------------------------------------------------------------------

def _check_scheme(scheme):
    if scheme not in sanscript.SCHEMES:
        raise InputError(f'{scheme.upper()} is not a script that text can be converted to or from')


def to_slp1(text, scheme):
    _check_scheme(scheme)
    return text if scheme == SLP1 else sanscript.transliterate(text, scheme, SLP1)


def from_slp1(text, scheme, denormalize=False):
    """SLP1 -> `scheme`. `denormalize` shows a word-final s/r as visarga."""
    _check_scheme(scheme)
    if denormalize:
        text = normalization.denormalize(text)
    return text if scheme == SLP1 else sanscript.transliterate(text, SLP1, scheme)


_CLASS_NASAL = {}
for _stops, _nasal in (('kKgGN', 'N'), ('cCjJY', 'Y'), ('wWqQR', 'R'),
                       ('tTdDn', 'n'), ('pPbBm', 'm')):
    for _c in _stops:
        _CLASS_NASAL[_c] = _nasal
_ANUSVARA_BEFORE_STOP = re.compile('M(?=[%s])' % ''.join(_CLASS_NASAL))
_DANDAS = re.compile('[|।॥]')


def _class_nasals(s):
    """Anusvara directly before a stop or nasal -> that consonant's class nasal.

    `aMga` and `aNga` are two spellings of one word and the lexicon only has
    the second. Anusvara before y r l v S z s h is left alone (`saMyoga`).
    """
    return _ANUSVARA_BEFORE_STOP.sub(lambda m: _CLASS_NASAL[s[m.end()]], s)


def normalize(text, scheme, strict):
    """Text in `scheme` -> the SLP1 string handed to the parser.

    Always: surrounding/repeated whitespace is dropped and anusvara before a
    stop becomes the class nasal. When not `strict`, punctuation, digits and
    dandas are removed as well, and a final anusvara / `o` becomes `m` / `aH`.
    """
    s = to_slp1(text, scheme)
    if not strict:
        s = _DANDAS.sub(' ', s).strip()
        try:
            s = normalization.normalize(s)
        except IndexError:  # upstream indexes the last letter of what may be ''
            s = ''
    s = _class_nasals(' '.join(s.split()))
    if not s:
        raise InputError('text has no Sanskrit letters in it')
    if len(s) > MAX_TEXT_LENGTH:
        raise InputError(f'text is too long ({len(s)} letters; the limit is {MAX_TEXT_LENGTH})')
    return s


def _words(text, scheme, strict):
    """Whitespace-separated words of `text`, each normalised on its own."""
    words = []
    for w in to_slp1(text, scheme).split():
        try:
            words.append(normalize(w, SLP1, strict))
        except InputError:
            if strict:
                raise
            # a token that was only punctuation or digits
    if not words:
        raise InputError('text has no Sanskrit letters in it')
    return words


def _visarga_variants(word, strict):
    """Ways to read a final visarga: as typed when strict, else as s, then r."""
    if strict or not word.endswith('H'):
        return [word]
    return [word[:-1] + 's', word[:-1] + 'r']


def _check_limit(limit, name='limit'):
    if limit is None or limit < 1:
        raise InputError(f'{name} must be at least 1')
    return min(limit, MAX_LIMIT)


# --------------------------------------------------------------------------
# Sandhi: split, join
# --------------------------------------------------------------------------

def _best_paths(graph, limit):
    """The `limit` best paths of a SandhiGraph: fewest words, then best score.

    SandhiGraph.find_all_paths ranks the same way, but only looks at the first
    limit*5 shortest paths, and which of several equally short paths those are
    differs from call to call. So the same text could come back with different
    splits. Here the candidates are widened until they hold every path that is
    as short as the ones returned, and ties are ordered by the words.
    """
    if graph.roots:
        graph.lock_start()
    k = max(limit * 5, SPLIT_POOL_MIN)
    while True:
        found = k_shortest_paths_dag_optimized(graph.G, graph.start, graph.end, k)
        paths = [tuple(w.canonical() for w in path[1:-1]) for _, path in found]
        last_returned = paths[min(limit, len(paths)) - 1]
        if len(paths) < k or len(paths[-1]) > len(last_returned) or k >= SPLIT_POOL_MAX:
            break
        k = min(k * 4, SPLIT_POOL_MAX)
    paths = list(dict.fromkeys(paths))
    scores = graph.scorer.score_splits(paths)
    ranked = sorted(zip(paths, scores), key=lambda ps: (len(ps[0]), -ps[1], ps[0]))
    return [list(path) for path, _ in ranked[:limit]]


def _split_slp1(s, limit):
    """Best `limit` segmentations of an SLP1 string into known words."""
    obj = SanskritObject(s, encoding=SLP1, strict_io=True, replace_ending_visarga=None)
    with _analyzer_lock:
        graph = analyzer.getSandhiSplits(obj)
        return _best_paths(graph, limit) if graph is not None else []


def split(text, scheme, strict=False, limit=10):
    """Sandhi-split `text`. Returns a list of splits, each a list of SLP1 words."""
    return _split_slp1(normalize(text, scheme, strict), _check_limit(limit))


def presegment(text, scheme, strict=False):
    """Words of a sentence whose sandhi is already resolved, as SLP1 padas.

    A final visarga is read as r or s, whichever makes a known word. A word
    that is not known as it stands is itself sandhi-split (best split only).
    """
    padas = []
    for word in _words(text, scheme, strict):
        candidates = _visarga_variants(word, strict)[::-1]  # r first, as upstream does
        known = next((c for c in candidates if analyzer.forms.valid(c)), None)
        if known:
            padas.append(known)
            continue
        pieces = _split_slp1(word, 1)
        if not pieces:
            hint = ' (strictIO is on: write a final m, s or r, not anusvara or visarga)' if strict else ''
            raise InputError(f'"{from_slp1(word, scheme)}" is not a known word '
                             f'and cannot be split into known words{hint}')
        padas.extend(pieces[0])
    return padas


def join(words, scheme, strict=False):
    """All sandhi-joined forms of `words`, in order. Returns SLP1 strings.

    The rules over-generate: not every result is a form in actual use.
    """
    if len(words) < 2:
        raise InputError('joins needs at least two words')
    parts = []
    for w in words:
        w = normalize(w, scheme, strict)
        parts.append(_visarga_variants(w, strict)[0])

    def S(x):
        return SanskritImmutableString(x, encoding=SLP1)

    def rank(x):
        return (x.count(' '), x)

    results = {parts[0]}
    for word in parts[1:]:
        joined = set()
        for left in results:
            forms = analyzer.sandhi.join(S(left), S(word))
            joined.update(forms or {f'{left} {word}'})
        results = set(sorted(joined, key=rank)[:MAX_JOIN_RESULTS])
    return sorted(results, key=rank)


def split_pairs(text, scheme, strict=False, position=None, valid_only=False):
    """Two-part sandhi decompositions of one word, straight from the rules.

    Returns (left, right, valid) in SLP1; `valid` says both parts are words the
    lexicon knows. `position` restricts the cut to one 0-based SLP1 letter.
    """
    s = normalize(text, scheme, strict)
    if ' ' in s:
        raise InputError('splitPairs works on a single word; use splits for a sentence')
    word = SanskritImmutableString(s, encoding=SLP1)
    if position is None:
        pairs = analyzer.sandhi.split_all(word)
    else:
        if not 0 <= position < len(s):
            raise InputError(f'position must be between 0 and {len(s) - 1}')
        pairs = analyzer.sandhi.split_at(word, position)
    out = []
    for left, right in pairs or ():
        if not left or not right:
            continue
        valid = analyzer.forms.valid(left) and analyzer.forms.valid(right)
        if valid or not valid_only:
            out.append((left, right, valid))
    return sorted(out, key=lambda p: (not p[2], len(p[0]), p[0], p[1]))


# --------------------------------------------------------------------------
# Morphological tags
# --------------------------------------------------------------------------

def _plain(tag_pairs):
    """[(root, tagset)] of SanskritStrings -> sorted [(root, [tags])] of SLP1 str."""
    plain = {(str(root), tuple(sorted(str(t) for t in tagset))) for root, tagset in tag_pairs}
    return [(root, list(tagset)) for root, tagset in sorted(plain)]


def tags(text, scheme, strict=False, lexicon='COMBINED'):
    """Morphological analyses of each word of `text`.

    Returns [(form, [(root, [tags])])] in SLP1, one entry per input word;
    the analyses are empty for a word the lexicon does not know.
    """
    lookup = LEXICONS[lexicon]
    result = []
    for word in _words(text, scheme, strict):
        variants = _visarga_variants(word, strict)
        form, found = variants[0], None
        for candidate in variants:
            found = lookup.get_tags(candidate)
            if found:
                form = candidate
                break
        result.append((form, _plain(found or [])))
    return result


# --------------------------------------------------------------------------
# Dhatupatha
# --------------------------------------------------------------------------

class Dhatupatha(DhatuWrapper):
    """The dhatupatha, found by the names the lexicon gives to roots.

    The parser asks it whether a verb can take an object, using the root the
    lexicon named for that verb. Upstream's wrapper matches the name exactly
    and answers "no" for a root it does not find - and it does not find more
    than a quarter of the lexicon's verb roots. The lexicon writes roots in
    -ai and -o with -A (`DyA` for the dhatupatha's `DyE`, `SA` for `So`);
    others are spelt differently or are not in this dhatupatha at all (`stu`,
    `praS`, `mokz`). Such a verb is never given an object, so a sentence
    built on it has no analysis. Here an -A root that is not found is looked
    up as -E and -o. A root that is still not found stays intransitive, as
    upstream has it, unless the caller asks for the opposite with
    `unknown_roots_transitive()` - which is what upstream itself assumes for
    participles and gerunds.
    """

    # Per call, not per instance: the one instance serves every request.
    _unknown_transitive = contextvars.ContextVar('unknown_roots_transitive', default=False)

    def __init__(self):
        super().__init__()
        self._by_name, self._by_taught_form = {}, {}
        for entry in self.db.all():
            self._by_name.setdefault(entry['DAtuH'], []).append(entry)
            self._by_taught_form.setdefault(entry['mUlaDAtuH'], []).append(entry)

    def _get_dhatus(self, d):
        found = self._by_name.get(d, [])
        if not found and d and d.endswith('A'):
            found = self._by_name.get(d[:-1] + 'E', []) + self._by_name.get(d[:-1] + 'o', [])
        return found

    def is_sakarmaka(self, d):
        if not self._get_dhatus(d):
            return self._unknown_transitive.get()
        return super().is_sakarmaka(d)

    @contextlib.contextmanager
    def unknown_roots_transitive(self, transitive):
        """Within the block, say whether a root that is not found may take an object."""
        token = self._unknown_transitive.set(bool(transitive))
        try:
            yield
        finally:
            self._unknown_transitive.reset(token)

    def find(self, name):
        """Entries for a root given by name or as taught with its markers."""
        found = list(self._get_dhatus(name))
        found.extend(e for e in self._by_taught_form.get(name, []) if e not in found)
        return found


dhatupatha = Dhatupatha()
# VakyaGraph asks its module's `dw` when it adds karaka relations.
_vakya.dw = dhatupatha


# --------------------------------------------------------------------------
# Vakya analysis (dependency parse of a split)
# --------------------------------------------------------------------------

class _ParseTimeout(Exception):
    pass


class _BudgetedVakyaGraph(VakyaGraph):
    """VakyaGraph that gives up on the parse search at `deadline`.

    The search calls on_the_fly() for every candidate it considers, which
    makes it the place to look at the clock. Giving up leaves the graph of
    possible relations (self.G) intact and the parse list empty. With a
    `deadline` of None the search is not run at all: building the relations
    takes milliseconds, the search can take any amount of time.
    """

    def __init__(self, path, deadline, **kwargs):
        self._deadline = deadline
        self.timed_out = False
        super().__init__(path, **kwargs)

    def on_the_fly(self, p):
        if time.monotonic() > self._deadline:
            raise _ParseTimeout()
        return super().on_the_fly(p)

    def get_parses_dc(self):
        if self._deadline is None:
            return set()
        try:
            return super().get_parses_dc()
        except _ParseTimeout:
            self.timed_out = True
            return set()


class ParseBudget:
    """Clock shared by the splits of one `parse` query."""

    def __init__(self, per_split=None, total=None):
        self.per_split = PARSE_SPLIT_TIMEOUT if per_split is None else per_split
        self.total = PARSE_TOTAL_TIMEOUT if total is None else total
        self._end = None

    def deadline(self):
        """Deadline for the next split, or None if the query's time is used up."""
        now = time.monotonic()
        if self._end is None:  # the clock starts with the first analysis
            self._end = now + self.total
        if now >= self._end:
            return None
        return min(now + self.per_split, self._end)


def _dot_quote(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _to_dot(nodes, edges, label_of):
    """DOT text for VakyaGraphNodes `nodes` and (u, v, label) `edges`."""
    ids = {}
    lines = ['digraph {']
    for n in sorted(nodes, key=_node_key):
        ids[n] = f'n{n.index}_{len(ids)}'
        lines.append(f'  {ids[n]} [label={_dot_quote(label_of(n))}];')
    for u, v, label in sorted(edges, key=lambda e: (_node_key(e[0]), _node_key(e[1]), e[2])):
        lines.append(f'  {ids[u]} -> {ids[v]} [label={_dot_quote(label)}];')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def dot_url(dot):
    """URL of a hosted Graphviz renderer for `dot` (built here, not fetched)."""
    return 'https://image-charts.com/chart?' + urlencode({'cht': 'gv:dot', 'chl': dot})


class _Output:
    """How a result is to be written out: target scheme and strictness."""

    def __init__(self, scheme, strict):
        _check_scheme(scheme)
        self.scheme = scheme
        self.strict = strict

    def pada(self, s, scheme=None):
        return from_slp1(s, scheme or self.scheme, denormalize=not self.strict)

    def term(self, s, scheme=None):
        """Roots, tags and relation names: transliterated, never denormalised."""
        return from_slp1(s, scheme or self.scheme)

    def node_label(self, node, scheme=None):
        root, tagset = _node_tag(node)
        tags_ = ', '.join(self.term(t, scheme) for t in tagset)
        return f'{self.pada(node.pada.canonical(), scheme)} [{self.term(root, scheme)}, {{{tags_}}}]'

    def tag(self, node):
        """One reading of a word, as a `ParseTag`."""
        root, tagset = _node_tag(node)
        return self.word(node.index, node.pada.canonical(), root, tagset)

    def word(self, index, pada, root, tagset):
        """A `ParseTag` from SLP1 parts."""
        return {
            'index': index,
            'pada': self.pada(pada),
            'root': self.term(root),
            'tags': [self.term(t) for t in tagset],
        }

    def relation(self, node, head=None, label=None):
        """`node` and how it relates to `head`, as a `ParseGraph`."""
        return {
            'node': self.tag(node),
            'predecessor': self.tag(head) if head is not None else None,
            'sambandha': self.term(label) if label is not None else None,
        }


def _node_tag(node):
    root, tagset = node.getMorphologicalTags()
    return str(root), sorted(str(t) for t in tagset)


def _node_key(node):
    """Sort key that is the same on every run (str(node) prints a set)."""
    root, tagset = _node_tag(node)
    return (node.index, node.pada.canonical(), root, tuple(tagset))


class ParseResult:
    """One vakya analysis of a split: a tree of relations between its words."""

    def __init__(self, graph, cost, out):
        self._graph = graph
        self._out = out
        self.cost = cost

    def _rows(self):
        """(node, head or None, relation or None) by word position."""
        g = self._graph
        for node in sorted(g, key=lambda n: n.index):
            heads = list(g.predecessors(node))
            if heads:
                head = heads[0]
                yield node, head, next(iter(g[head][node].values()))['label']
            else:
                yield node, None, None

    @cached_property
    def graph(self):
        return [self._out.relation(node, head, label) for node, head, label in self._rows()]

    @cached_property
    def conll(self):
        """CoNLL-style rows: ID, FORM, LEMMA(_), ROOT, TAGS, HEAD, DEPREL."""
        lines = []
        for node, head, label in self._rows():
            t = self._out.tag(node)
            lines.append('\t'.join([
                str(node.index + 1), t['pada'], '_', t['root'], '|'.join(t['tags']) or '_',
                str(head.index + 1) if head is not None else '0',
                self._out.term(label) if label is not None else 'root',
            ]))
        return '\n'.join(lines)

    def dot(self, scheme=None):
        edges = [(u, v, self._out.term(label, scheme))
                 for u, v, label in self._graph.edges(data='label')]
        return _to_dot(self._graph, edges, lambda n: self._out.node_label(n, scheme))

    def dot_url(self, scheme=None):
        return dot_url(self.dot(scheme))


class SplitAnalysis:
    """One sandhi split of a sentence and, on demand, its vakya analyses.

    Nothing is analysed until a field that needs it is read, so a query that
    only asks for `split` costs no more than `splits` does. There are two
    steps, and a field triggers only the one it needs: finding the relations
    that are possible between the words (quick), and searching them for the
    trees that connect every word (can run into the time budget).
    """

    def __init__(self, padas, out, budget, parse_limit=2, min_cost_only=False,
                 unknown_roots_transitive=False):
        self._padas = padas
        self._out = out
        self._budget = budget
        self._parse_limit = _check_limit(parse_limit, 'parseLimit')
        self._min_cost_only = min_cost_only
        self._unknown_roots_transitive = unknown_roots_transitive

    @property
    def split(self):
        return [self._out.pada(p) for p in self._padas]

    @cached_property
    def _path(self):
        """The words as tagged objects; None if the lexicon has no tags for one."""
        path = []
        for pada in self._padas:
            obj = SanskritObject(pada, encoding=SLP1, strict_io=True, replace_ending_visarga=None)
            found = analyzer.getMorphologicalTags(obj)
            if not found:
                return None
            obj.setMorphologicalTags(found)
            path.append(obj)
        return path

    def _graph(self, deadline):
        # the relations are found while the graph is built, which is when
        # the dhatupatha is asked whether a verb takes an object
        with dhatupatha.unknown_roots_transitive(self._unknown_roots_transitive):
            return _BudgetedVakyaGraph(self._path, deadline, max_parse_dc=5, fast_merge=True)

    @cached_property
    def _unsearched(self):
        """Graph of the possible relations, without the search for analyses."""
        return self._graph(None) if self._path is not None else None

    @cached_property
    def _analysed(self):
        """(graph, status) after the search for analyses."""
        if self._path is None:
            return None, 'NO_PARSE'
        deadline = self._budget.deadline()
        if deadline is None:
            return self._unsearched, 'TIMEOUT'
        graph = self._graph(deadline)
        if graph.timed_out:
            return graph, 'TIMEOUT'
        return graph, 'OK' if graph.parses else 'NO_PARSE'

    @property
    def _relations(self):
        """A graph to read the possible relations from; never starts a search."""
        if '_analysed' in self.__dict__:
            return self._analysed[0]
        return self._unsearched

    @property
    def status(self):
        """OK, NO_PARSE (no analysis links all the words) or TIMEOUT."""
        return self._analysed[1]

    @cached_property
    def analysis(self):
        graph = self._analysed[0]
        if graph is None:
            return []
        # Upstream orders by cost only and leaves ties in set order, which
        # changes from run to run; order ties by their relations instead.
        ranked = sorted(zip(graph.parses, graph.parse_costs),
                        key=lambda r: (r[1], sorted((_node_key(v), _node_key(u), label)
                                                    for u, v, label in r[0].edges(data='label'))))
        if self._min_cost_only and ranked:
            best = ranked[0][1]
            ranked = [r for r in ranked if r[1] == best]
        return [ParseResult(g, cost, self._out) for g, cost in ranked[:self._parse_limit]]

    def relations(self, by_head=True):
        """What `split_dot` draws, as `ParseGraph` rows.

        One row for each way a word could relate to another: the word (its
        position, form and root), the relation, and the word it would depend
        on. Readings of a word that differ only in their tags are one row,
        with the tags of all of them; the same goes for the word depended on.
        A word, or a root of it, that nothing could govern has a row without
        a relation. With `by_head` false the word depended on is left out, so
        there is one row per word, root and relation.
        """
        graph = self._relations
        if graph is None:
            return []

        def word(node):
            return (node.index, node.pada.canonical(), _node_tag(node)[0])

        merged = {}   # (word, relation, head word) -> (tags of the word, tags of the head)
        for node in graph.G:
            heads = {(head, label) for head, _, label in graph.G.in_edges(node, data='label')}
            for head, label in heads or {(None, None)}:
                key = (word(node), label or '', word(head) if by_head and head is not None else ())
                tags_, head_tags = merged.setdefault(key, (set(), set()))
                tags_.update(_node_tag(node)[1])
                if head is not None:
                    head_tags.update(_node_tag(head)[1])
        return [{
            'node': self._out.word(*node, sorted(tags_)),
            'predecessor': self._out.word(*head, sorted(head_tags)) if head else None,
            'sambandha': self._out.term(label) if label else None,
        } for (node, label, head), (tags_, head_tags) in sorted(merged.items())]

    def split_dot(self, scheme=None):
        """DOT of every relation that is possible between the words (not one parse)."""
        graph = self._relations
        if graph is None:
            return ''
        edges = [(u, v, self._out.term(label, scheme))
                 for u, v, label in graph.G.edges(data='label')]
        return _to_dot(graph.G, edges, lambda n: self._out.node_label(n, scheme))

    def split_dot_url(self, scheme=None):
        dot = self.split_dot(scheme)
        return dot_url(dot) if dot else ''

    def parse_dots(self, scheme=None):
        return [p.dot(scheme) for p in self.analysis]

    def parse_dot_urls(self, scheme=None):
        return [p.dot_url(scheme) for p in self.analysis]


def parse(text, scheme_from, scheme_to, strict=False, limit=10, pre_segmented=False,
          parse_limit=2, min_cost_only=False, unknown_roots_transitive=False, budget=None):
    """Sandhi-split `text` and return a SplitAnalysis for each split.

    `unknown_roots_transitive` lets a verb whose root the dhatupatha does not
    have take an object (see Dhatupatha).
    """
    out = _Output(scheme_to, strict)
    if pre_segmented:
        _check_limit(limit)
        splits = [presegment(text, scheme_from, strict)]
    else:
        splits = split(text, scheme_from, strict, limit)
    budget = budget or ParseBudget()
    return [SplitAnalysis(padas, out, budget, parse_limit, min_cost_only, unknown_roots_transitive)
            for padas in splits]


# --------------------------------------------------------------------------
# Dhatupatha lookup, pratyaharas, metre
# --------------------------------------------------------------------------

_DHATU_FIELDS = {
    'dhatu': 'DAtuH', 'mulaDhatu': 'mUlaDAtuH', 'artha': 'DAtvarTaH', 'gana': 'gaRaH',
    'karmakatva': 'karmakatvaM', 'ittva': 'iwtvaM', 'pada': 'upagrahaH', 'rupa': 'rUpam',
}


def dhatus(name, scheme):
    """Dhatupatha entries for a root.

    The root may be given bare (`gam`), the way the lexicon names it (`DyA`
    for `DyE`), or as taught with its markers (`gamx~`). Returns dicts of SLP1
    strings plus the booleans `sakarmaka` / `dvikarmaka`.
    """
    key = to_slp1(name, scheme).strip()
    if not key:
        raise InputError('dhatu is empty')
    result = []
    for entry in dhatupatha.find(key):
        row = {field: entry.get(source, '') for field, source in _DHATU_FIELDS.items()}
        row['sakarmaka'] = entry['karmakatvaM'] in ('sakarmakaH', 'dvikarmakaH')
        row['dvikarmaka'] = entry['karmakatvaM'] == 'dvikarmakaH'
        result.append(row)
    return result


def maheshvara_sutras():
    """The fourteen Maheshvara sutras, in SLP1."""
    return str(_maheshvara).split()


def pratyahara(name, scheme, long_form=True, with_long_vowels=False):
    """Sounds a pratyahara stands for. Returns (name, [sounds]) in SLP1.

    `long_form` picks the later of two possible end markers (aR, iR).
    """
    key = to_slp1(name, scheme).strip()
    sutras = str(_maheshvara)
    its = {s[-1] for s in sutras.split()}
    if len(key) < 2 or key[-1] not in its or sutras.find(key[:-1]) == -1:
        raise InputError(f'"{name}" is not a pratyahara')
    try:
        varnas = _maheshvara.getPratyahara(
            SanskritImmutableString(key, encoding=SLP1),
            longp=long_form, remove_a=True, dirghas=with_long_vowels)
    except (ValueError, IndexError):
        raise InputError(f'"{name}" is not a pratyahara') from None
    return key, list(str(varnas))


_VERSE_BREAK = re.compile(r'[\n|.।॥]+')


def meter(text, scheme):
    """Syllable weights of each line of `text` (lines end at a newline or danda).

    Returns [(line, syllable count, pattern)]; the line is SLP1 and the pattern
    has one letter per syllable, G for guru (heavy) and L for laghu (light).
    """
    lines = []
    for line in _VERSE_BREAK.split(to_slp1(text, scheme)):
        line = ' '.join(line.split())
        pattern = ''.join(sounds.meter(line, heavy='G', light='L'))
        if pattern:
            lines.append((line, len(pattern), pattern))
    if not lines:
        raise InputError('text has no Sanskrit syllables in it')
    return lines
