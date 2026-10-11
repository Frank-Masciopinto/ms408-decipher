"""Render the first text line of folio f1r as short WAV files under a few candidate maps. ILLUSTRATION ONLY: the pitches are
produced by a hypothetical unit-to-Hz map and carry no evidence about the manuscript. Pitches above 1400 Hz are folded down by octaves."""
import wave
from pathlib import Path

import numpy as np

import h02_lib as L
from msdecipher.segment import Segmenter, PRESETS

SR = 11025
NOTE, GAP = 0.16, 0.10


def render(freqs_by_word) -> np.ndarray:
    out = []
    for w in freqs_by_word:
        for f in w:
            n = int(SR * NOTE)
            t = np.arange(n) / SR
            env = np.minimum(1, np.minimum(t / 0.01, (NOTE - t) / 0.03))
            out.append(0.35 * env * np.sin(2 * np.pi * f * t))
        out.append(np.zeros(int(SR * GAP)))
    return np.concatenate(out)


def fold(f):
    while f > 1400:
        f /= 2
    return f


def main():
    audio_dir = L.HERE / "audio"
    audio_dir.mkdir(exist_ok=True)
    t = L.build_ms("T1")
    st = L.unit_stats(t, np.ones(len(t.L), bool), slot_grammar=True, seed=1)
    folios = L.H1.load_folios(L.TR / "ZL3b-n.txt", "P")
    f1r = [f for f in folios if f.folio == "f1r"][0]
    lines = f1r.lines[:1]
    seg = Segmenter(PRESETS["collapsed"])
    rng = np.random.default_rng(0)
    base = L.build_map("c_pos", st, t.inv)
    maps = {"c_pos": base, "b_major12_slot": L.build_map("b_major12_slot", st, t.inv), "b_pentatonic_freq": L.build_map("b_pentatonic_freq", st, t.inv),
            "d_smooth": L.build_map("d_smooth", st, t.inv), "NULL_random_permutation_of_c_pos": rng.permutation(base)}
    meta = []
    for name, pv in maps.items():
        idx = {u: i for i, u in enumerate(t.inv)}
        words = [[fold(float(pv[idx[u]])) for w in ln for u in seg(w) if u in idx] for ln in lines]
        # one list per word
        wl = []
        for ln in lines:
            for w in ln:
                wl.append([fold(float(pv[idx[u]])) for u in seg(w) if u in idx])
        sig = render(wl)
        path = audio_dir / f"f1r_line1_{name}.wav"
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes((sig * 32767).astype("<i2").tobytes())
        meta.append((path.name, len(sig) / SR, path.stat().st_size))
    (audio_dir / "README.md").write_text(
        "# Audio illustrations (NOT evidence)\n\n"
        "Sine-tone renderings of the first text line of folio f1r (ZL 3b transcription, collapsed EVA units) under candidate unit-to-pitch maps "
        "from `results/map_table_wide_T1.csv`. Each unit is a 0.16 s note, words are separated by 0.10 s of silence, pitches above 1400 Hz are folded "
        "down by octaves. The maps are hypotheses invented for this study; the sound of a line says nothing about the manuscript unless the map "
        "beats the null tests in `../README.md` (it does not establish any meaning in any case). `NULL_random_permutation_of_c_pos` has the same "
        "pitches as `c_pos` assigned to random units: listen for the difference between contour-regular and arbitrary melodies.\n\n"
        + "\n".join(f"- `{n}`: {d:.1f} s, {s/1024:.0f} KB" for n, d, s in meta) + "\n")
    print(meta)


if __name__ == "__main__":
    main()
