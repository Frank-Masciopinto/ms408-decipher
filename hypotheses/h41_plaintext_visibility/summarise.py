"""Apply the h41 separation rule and write STATUS, summary, and the figure."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
FIG = HERE / "figures" / "plaintext_visibility.png"
STATS = ("new_type", "burst", "mi100", "block_js")
HANDS = ("1A", "2B", "3B")
SEP_ARMS = ("real", "shuffle", "zipf")
CIPHER_ARMS = ("shuffle", "zipf", "real_naibbe")

COLORS = {
    "real": "#4C78A8",
    "shuffle": "#F58518",
    "zipf": "#54A24B",
    "real_naibbe": "#B279A2",
    "C0": "#72B7B2",
    "MS": "#E45756",
}


def separates(real: list[float], shuffle: list[float], zipf: list[float]) -> bool:
    """Pass only when every real value sits strictly above both cipher arms."""
    if not real or not shuffle or not zipf:
        raise ValueError("separation needs real, shuffle, and zipf values")
    return min(real) > max(shuffle) and min(real) > max(zipf)


def closer_to_alt(ms: float, mean_plain: float, mean_c0: float, mean_cipher: float) -> bool:
    """True when ms is strictly closer to the nearer of C0 and the cipher-arm mean than to plain text."""
    dist_alt = min(abs(ms - mean_c0), abs(ms - mean_cipher))
    return dist_alt < abs(ms - mean_plain)


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _arm(xs: list[float]) -> dict:
    return {"n": len(xs), "min": min(xs), "max": max(xs), "mean": _mean(xs), "values": xs}


def _col(rows: list[dict], stat: str) -> list[float]:
    return [float(r[stat]) for r in rows]


def evaluate(scores: dict) -> dict:
    for key in ("real", "shuffle", "zipf", "real_naibbe", "C0"):
        if len(scores.get(key, [])) != 5:
            raise ValueError(f"{key} needs 5 streams, got {len(scores.get(key, []))}")
    if "MS" not in scores or not scores["MS"]:
        raise ValueError("scores missing MS")
    hands = {r["hand"]: r for r in scores["MS"]}
    missing = [h for h in HANDS if h not in hands]
    if missing:
        raise ValueError(f"MS missing {missing}")

    per_stat = {}
    passing = []
    for stat in STATS:
        real = _col(scores["real"], stat)
        shuffle = _col(scores["shuffle"], stat)
        zipf = _col(scores["zipf"], stat)
        ok = separates(real, shuffle, zipf)
        if ok:
            passing.append(stat)
        per_stat[stat] = {
            "pass": ok,
            "real": _arm(real),
            "shuffle": _arm(shuffle),
            "zipf": _arm(zipf),
            "real_naibbe": _arm(_col(scores["real_naibbe"], stat)),
            "C0": _arm(_col(scores["C0"], stat)),
            "MS": {h: float(hands[h][stat]) for h in HANDS},
        }

    v1 = len(passing) >= 1
    v2_detail = {}
    v2: bool | None = None
    if v1:
        v2 = True
        for stat in passing:
            block = per_stat[stat]
            mean_plain = block["real"]["mean"]
            mean_c0 = block["C0"]["mean"]
            mean_cipher = _mean([block[name]["mean"] for name in CIPHER_ARMS])
            hands_out = {}
            stat_ok = True
            for h in HANDS:
                ms = block["MS"][h]
                dist_plain = abs(ms - mean_plain)
                dist_c0 = abs(ms - mean_c0)
                dist_cipher = abs(ms - mean_cipher)
                closer = closer_to_alt(ms, mean_plain, mean_c0, mean_cipher)
                stat_ok = stat_ok and closer
                hands_out[h] = {
                    "value": ms,
                    "dist_plain": dist_plain,
                    "dist_c0": dist_c0,
                    "dist_cipher": dist_cipher,
                    "closer": closer,
                }
            v2_detail[stat] = {
                "mean_plain": mean_plain,
                "mean_c0": mean_c0,
                "mean_shuffle": block["shuffle"]["mean"],
                "mean_zipf": block["zipf"]["mean"],
                "mean_real_naibbe": block["real_naibbe"]["mean"],
                "mean_cipher_arms": mean_cipher,
                "hands": hands_out,
                "pass": stat_ok,
            }
            v2 = v2 and stat_ok

    return {
        "V1": v1,
        "V2": v2,
        "V2_scored": v1,
        "passing": passing,
        "stats": per_stat,
        "v2_detail": v2_detail,
    }


def _series_ys(scores: dict, stat: str) -> list[tuple[str, str, list[float]]]:
    out = []
    for key in ("real", "shuffle", "zipf", "real_naibbe", "C0"):
        out.append((key, key, _col(scores[key], stat)))
    for h in HANDS:
        ys = [float(r[stat]) for r in scores["MS"] if r["hand"] == h]
        out.append(("MS", h, ys))
    return out


def draw(scores: dict, verdict: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2), constrained_layout=True)
    v2 = verdict["V2"]
    v2_txt = "not scored" if v2 is None else ("pass" if v2 else "fail")
    fig.suptitle(f"h41 plaintext visibility    V1 {'pass' if verdict['V1'] else 'fail'}    V2 {v2_txt}")
    for ax, stat in zip(axes.ravel(), STATS):
        series = _series_ys(scores, stat)
        for i, (group, _label, ys) in enumerate(series):
            ax.scatter([i] * len(ys), ys, s=22, color=COLORS[group], zorder=3)
            ax.scatter([i], [_mean(ys)], marker="D", c="black", s=26, zorder=4)
        ax.set_title(f"{stat}  {'pass' if verdict['stats'][stat]['pass'] else 'fail'}")
        ax.set_xticks(range(len(series)))
        ax.set_xticklabels([lab if lab != "real_naibbe" else "naibbe" for _g, lab, _ys in series], rotation=45, ha="right")
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> None:
    scores_path = RES / "scores.json"
    scores = json.loads(scores_path.read_text())
    verdict = evaluate(scores)
    draw(scores, verdict, FIG)
    n_random = scores.get("n_random")
    payload = {
        "complete": True,
        "n_random": n_random,
        "n_stream": scores.get("n_stream"),
        "ms_n": {r["hand"]: r["n"] for r in scores["MS"]},
        "fit_secs": None if scores.get("fit") is None else scores["fit"].get("secs"),
        "fit_distance": None if scores.get("fit") is None else scores["fit"].get("fit_distance"),
        **verdict,
    }
    RES.mkdir(parents=True, exist_ok=True)
    (RES / "summary.json").write_text(json.dumps(payload, indent=1) + "\n")
    status = {
        "complete": True,
        "n_random": n_random,
        "V1": verdict["V1"],
        "V2": verdict["V2"],
        "V2_scored": verdict["V2_scored"],
        "passing": verdict["passing"],
        "ms_n": payload["ms_n"],
        "fit_secs": payload["fit_secs"],
        "fit_distance": payload["fit_distance"],
        "stats": {
            stat: {
                "pass": verdict["stats"][stat]["pass"],
                "real": {"min": verdict["stats"][stat]["real"]["min"], "max": verdict["stats"][stat]["real"]["max"]},
                "shuffle": {"min": verdict["stats"][stat]["shuffle"]["min"], "max": verdict["stats"][stat]["shuffle"]["max"]},
                "zipf": {"min": verdict["stats"][stat]["zipf"]["min"], "max": verdict["stats"][stat]["zipf"]["max"]},
            }
            for stat in STATS
        },
        "v2_detail": verdict["v2_detail"],
    }
    (RES / "STATUS.json").write_text(json.dumps(status, indent=1) + "\n")
    print(json.dumps(status, indent=1))


if __name__ == "__main__":
    main()
