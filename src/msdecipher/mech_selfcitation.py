"""Timm & Schinner's self-citation text generator (2020), run through the *authors' own reference implementation*.

    Timm, T. & Schinner, A. (2020). A possible generating algorithm of the Voynich manuscript. Cryptologia 44(1), 1-19.
    doi:10.1080/01611194.2019.1596999. Code: https://github.com/TorstenTimm/SelfCitationTextgenerator (MIT, (c) 2019 Torsten Timm),
    pinned here at commit ``a6ede22``.

**Why the Java program and not a re-implementation.** The paper gives the algorithm only as a sketch (Algorithm 1: pick a
source word, copy it, then add/remove a prefix or suffix, combine or split, or replace glyphs with similar ones, subject to
glyph "can follow" rules, limits on repetition and suggestions that keep -in/-ol/-dy endings frequent). The behaviour of the
published text depends on ~5000 lines of rules (glyph groups, replacement tables, the curve-line follow rules, source choosers).
Porting them by hand would produce a *plausible* generator, not *the* generator; this module therefore compiles the authors'
source (JDK 17 + log4j 1.2.17) and drives it through its documented ``conf.properties`` options. If no JDK is available it falls
back to the generated texts cached under ``data/mechanisms/selfcitation/`` (produced by this module).

What the reference generator contains that is *not* independent of MS 408 (so a good match is not evidence of anything):
the glyph classes and "similar glyph" tables, the curve-line follow rule and the `daiin` / `ol` / `chedy` suggestion types were
designed after looking at Voynichese, and the text is seeded with the f103v line ``pchal shal shorchdy ...``. The other
``method.canFollow`` options ``voynich`` (uses a dictionary of MS 408 word types) and ``statistic`` / ``percent`` (MS 408 glyph
statistics) are circular and excluded from the sweep.

Fitting: every numeric option has a documented range in ``conf.properties`` (``BOUNDS`` below); :func:`sweep` samples
parameter vectors inside those ranges (plus the shipped defaults) and ranks them by a distance to MS 408 computed on the
*lexicon-level* metrics the authors themselves target (not on the structure metrics used later to evaluate the mechanism).
"""
from __future__ import annotations

import hashlib
import os
import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence

from .paths import repo_root

STG_COMMIT = "a6ede2202dd7ad6285ce2c007bf22c2a0e7709b7"
STG_URL = "https://github.com/TorstenTimm/SelfCitationTextgenerator.git"
LOG4J_URL = "https://repo1.maven.org/maven2/log4j/log4j/1.2.17/log4j-1.2.17.jar"

DEFAULTS: dict[str, object] = {
    "text.lines_to_create": 4000, "text.max_line_length": 55, "text.min_line_length": 15, "text.lines_per_page": 29,
    "text.max_repeat_count": 3, "text.initial_line": "pchal shal shorchdy okeor okain shedy pchedy qotchedy qotar ol lkar",
    "method.random": "pseudo", "method.random.pseudo.seed": 19, "method.canFollow": "curveline", "method.canFollow.error_rate": 0,
    "method.sourceChooser": "page", "method.sourceChooser.same_position_probability": 28, "method.morph": "slim",
    "method.morph.add_remove.probability": 20, "method.morph.combine_split.probability": 30,
    "method.morph.replace.probability": 50, "method.morph.reuse_last.probability": 10,
    "method.morph.combined.dismiss_as_source_probability": 30, "method.morph.use_word_final_substitutions": "true",
    "method.suggestions": "top", "method.suggestions.probability": 40, "method.suggestions.iType_min_percentage": 20,
    "method.suggestions.olType_min_percentage": 25, "method.suggestions.dyType_min_percentage": 25,
    "save.filename": "out.txt", "save.path": "./generate/", "save.properties_in_seperate_file": "false",
    "save.gephi.nodes": "false", "save.gephi.use_voynich_similarities": "false",
}
# numeric parameters and the ranges documented in the shipped conf.properties / PROPERTIES.md
BOUNDS: dict[str, tuple[int, int]] = {
    "method.morph.add_remove.probability": (0, 80),
    "method.morph.combine_split.probability": (0, 80),
    "method.morph.replace.probability": (20, 100),
    "method.morph.reuse_last.probability": (0, 20),
    "method.morph.combined.dismiss_as_source_probability": (0, 100),
    "method.sourceChooser.same_position_probability": (0, 100),
    "text.max_repeat_count": (1, 5),
    "method.canFollow.error_rate": (0, 10),
    "method.suggestions.probability": (0, 100),
    "method.suggestions.iType_min_percentage": (0, 100),
    "method.suggestions.olType_min_percentage": (0, 100),
    "method.suggestions.dyType_min_percentage": (0, 100),
}
CHOICES: dict[str, tuple[str, ...]] = {
    "method.sourceChooser": ("page", "position", "random"),
    "method.suggestions": ("top", "daiin", "random", "none"),
    "method.morph.use_word_final_substitutions": ("true", "false"),
}
# parameters varied by the sweep (others stay at the authors' defaults)
SWEPT = list(BOUNDS) + list(CHOICES)


def _candidates() -> list[Path]:
    env = os.environ.get("MSDECIPHER_JAVA_HOME")
    out = []
    if env:
        out.append(Path(env) / "bin")
    out += [Path("/workspace/refs/jdk/bin"), Path.home() / ".cache/msdecipher/jdk/bin"]
    return out


def find_java() -> tuple[str, str] | None:
    """(java, javac) executables or None."""
    for d in _candidates():
        if (d / "java").exists():
            return str(d / "java"), str(d / "javac")
    j, c = shutil.which("java"), shutil.which("javac")
    return (j, c) if j and c else None


def classes_dir() -> Path:
    return Path(os.environ.get("MSDECIPHER_STG_CLASSES", "/workspace/refs/stg_build"))


def log4j_jar() -> Path:
    return Path(os.environ.get("MSDECIPHER_LOG4J", "/workspace/refs/log4j-1.2.17.jar"))


def build(dest: Path | None = None, quiet: bool = True) -> Path:
    """Fetch the reference source at the pinned commit and compile it with javac (needs git, a JDK, network)."""
    java = find_java()
    if not java:
        raise RuntimeError("no JDK found (set MSDECIPHER_JAVA_HOME)")
    dest = dest or Path.home() / ".cache/msdecipher/stg"
    src = dest / "src"
    if not src.exists():
        dest.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", STG_URL, str(src)], check=True)
        subprocess.run(["git", "-C", str(src), "checkout", "-q", STG_COMMIT], check=True)
    jar = dest / "log4j-1.2.17.jar"
    if not jar.exists():
        subprocess.run(["curl", "-sL", "-o", str(jar), LOG4J_URL], check=True)
    out = dest / "classes"
    out.mkdir(exist_ok=True)
    files = [str(p) for p in (src / "source/src/main/java").rglob("*.java")]
    subprocess.run([java[1], "-nowarn", "-encoding", "UTF-8", "-cp", str(jar), "-d", str(out), *files], check=True,
                   capture_output=quiet)
    for p in (src / "source/src/main/resources").glob("*"):
        shutil.copy(p, out / p.name)
    os.environ["MSDECIPHER_STG_CLASSES"], os.environ["MSDECIPHER_LOG4J"] = str(out), str(jar)
    return out


def available() -> bool:
    return find_java() is not None and (classes_dir() / "de").exists() and log4j_jar().exists()


def cache_dir() -> Path:
    return repo_root() / "data" / "mechanisms" / "selfcitation"


def param_key(params: dict, seed: int) -> str:
    items = sorted((k, str(v)) for k, v in params.items() if k in SWEPT)
    return hashlib.sha1((repr(items) + f"|{seed}").encode()).hexdigest()[:10]


def _conf(params: dict, seed: int, lines: int, outdir: str) -> str:
    p = {**DEFAULTS, **params, "method.random.pseudo.seed": seed, "text.lines_to_create": lines,
         "save.path": outdir + "/", "save.filename": "out.txt"}
    return "\n".join(f"{k}={v}" for k, v in p.items()) + "\n"


def run_java(params: dict, seed: int, lines: int = 4000, timeout: int = 120) -> list[list[str]]:
    """One run of the reference generator -> list of lines (each a list of words)."""
    java = find_java()
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "generate").mkdir()
        Path(td, "conf.properties").write_text(_conf(params, seed, lines, str(Path(td) / "generate")), encoding="utf-8")
        cp = f"{classes_dir()}:{log4j_jar()}"
        # the program reads conf.properties from the classpath: put the temp dir first so it overrides the bundled default
        r = subprocess.run([java[0], "-cp", f"{td}:{cp}", "de.voynich.text.SelfCitationTextGenerator"], cwd=td,
                           capture_output=True, text=True, timeout=timeout)
        out = Path(td) / "generate" / "out.txt"
        if not out.exists():
            raise RuntimeError("generator produced no output: " + r.stdout[-300:] + r.stderr[-300:])
        txt = out.read_text(encoding="utf-8")
    return [ln.split() for ln in txt.splitlines() if ln.strip() and not ln.startswith("#")]


def generate(params: dict | None, seed: int, n_tokens: int = 35000, tag: str | None = None, use_cache: bool = True) -> list[str]:
    """Flat word list of exactly ``n_tokens`` words (Java generator, or the cached text for ``tag``/``param_key`` when no JDK)."""
    params = dict(params or {})
    name = f"{tag or 'p' + param_key(params, seed)}_s{seed}.txt"
    cached = cache_dir() / name
    if available():
        lines = 4000
        while True:
            ls = run_java(params, seed, lines)
            words = [w for l in ls for w in l]
            if len(words) >= n_tokens or lines > 20000:
                break
            lines = int(lines * 1.4)
        words = words[:n_tokens]
        if tag and use_cache:
            cache_dir().mkdir(parents=True, exist_ok=True)
            cached.write_text("\n".join(" ".join(l) for l in ls) + "\n", encoding="utf-8")
        return words
    if cached.exists():
        return [w for l in cached.read_text(encoding="utf-8").splitlines() for w in l.split()][:n_tokens]
    raise RuntimeError(f"no JDK and no cached text {cached.name}: install a JDK (MSDECIPHER_JAVA_HOME) or run build()")


def sample_params(rng: random.Random) -> dict:
    """A random parameter vector inside the documented bounds (the authors' defaults are evaluated separately)."""
    p: dict = {k: rng.randint(lo, hi) for k, (lo, hi) in BOUNDS.items()}
    for k, ch in CHOICES.items():
        p[k] = rng.choice(ch)
    return p
