"""Render the first line of folio f1r under slot-tied pitch maps. ILLUSTRATION ONLY: the map is a hypothesis with no evidential link to the
manuscript. Pitches above 1400 Hz are folded down by octaves."""
import wave

import numpy as np

import h03_lib as L

SR = 11025


def tone(f, dur, amp=0.3):
    n = int(SR * dur)
    t = np.arange(n) / SR
    env = np.minimum(1, np.minimum(t / 0.01, (dur - t) / 0.03))
    return amp * env * np.sin(2 * np.pi * f * t)


def fold(f):
    while f > 1400:
        f /= 2
    return f


def write(path, sig):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.clip(sig, -1, 1) * 32767).astype("<i2").tobytes())


def main():
    out = L.HERE / "audio"
    out.mkdir(exist_ok=True)
    c = L.ms_corpus()
    uw = L.segment_words(c.words, "learned", True)
    fit = L.SlotFit("learned").fit(uw, seed=1)
    paths = fit.decode(uw)
    tab = L.slot_unit_table(fit, uw, paths).set_index("unit")
    folios = L.H1.load_folios(L.TR / "ZL3b-n.txt", "P")
    line = [f for f in folios if f.folio == "f1r"][0].lines[0]
    rng = np.random.default_rng(0)
    perm = rng.permutation(L.K)
    files = []
    mel, chord, null = [], [], []
    for w in line:
        u = L.segment_words([w], "learned", True)[0]
        p = fit.decode_one(u)
        if p is None:
            continue
        for unit, s in zip(u, p):
            hz = tab.loc[unit, "hz_slot_rank"] if unit in tab.index else float(L.slot_hz_log(s))
            # pitch of THIS occurrence: slot of the occurrence + within-slot rank of the unit in that slot is approximated by the unit's table offset
            hz = float(L.slot_hz_log(s)) * (hz / float(L.slot_hz_log(tab.loc[unit, "modal_slot"] - 1)) if unit in tab.index else 1.0)
            mel.append(tone(fold(hz), 0.16))
            null.append(tone(fold(float(L.slot_hz_log(perm[s]))), 0.16))
        mel.append(np.zeros(int(SR * 0.10)))
        null.append(np.zeros(int(SR * 0.10)))
        n = int(SR * 0.45)
        ch = sum(tone(fold(float(L.slot_hz_log(s))), 0.45, 0.2) for s in p)
        chord.append(ch)
        chord.append(np.zeros(int(SR * 0.08)))
    for name, sig in (("slot_melody_rising_paths", mel), ("slot_chords_one_chord_per_word", chord), ("NULL_slot_pitches_permuted", null)):
        s = np.concatenate(sig)
        s = s / max(1.0, np.abs(s).max() / 0.9)
        path = out / f"f1r_line1_{name}.wav"
        write(path, s)
        files.append((path.name, len(s) / SR, path.stat().st_size))
    (out / "README.md").write_text(
        "# Audio illustrations (NOT evidence)\n\nRenderings of the first text line of folio f1r under the learned 12-slot grammar (fitted on all of MS 408), pitch tied to slot "
        "index (143 cents per slot, 174 Hz for slot 1 up to 433 Hz for slot 12; within-slot offsets by unit frequency rank). Pitches above 1.4 kHz are folded by octaves.\n\n"
        "* `slot_melody_rising_paths`: one note per unit, 0.16 s; every word rises, by the definition of a slot path (not a finding).\n"
        "* `slot_chords_one_chord_per_word`: one 0.45 s chord per word made of the pitches of the slots the word fills (the word's 'slot-occupancy pattern').\n"
        "* `NULL_slot_pitches_permuted`: same notes with the 12 slot pitches randomly permuted: the contour is no longer rising.\n\n"
        "Hearing a rising contour proves nothing: it is guaranteed by the grammar. Whether the slot patterns carry any information is tested in `../README.md`, and the sheet's values do not fix the map.\n\n"
        + "\n".join(f"- `{n}`: {d:.1f} s, {s / 1024:.0f} KB" for n, d, s in files) + "\n")
    print(files)


if __name__ == "__main__":
    main()
