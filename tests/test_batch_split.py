"""Batch narration split test (no network): synthetic 'lines' of noise with
2 s gaps between lines and 0.5 s pauses inside lines."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from pipeline.narration import _split_batch


def _make(path: Path, pattern: list[tuple[str, float]]) -> None:
    parts, filt = [], []
    for i, (kind, d) in enumerate(pattern):
        src = f"anoisesrc=d={d}:a=0.3" if kind == "speech" else f"anullsrc=d={d}"
        parts += ["-f", "lavfi", "-i", src]
        filt.append(f"[{i}]aformat=sample_rates=24000:channel_layouts=mono[a{i}]")
    filt.append("".join(f"[a{i}]" for i in range(len(pattern))) + f"concat=n={len(pattern)}:v=0:a=1[o]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *parts, "-filter_complex", ";".join(filt),
                    "-map", "[o]", str(path)], check=True)


class BatchSplitTests(unittest.TestCase):
    def test_splits_at_long_gaps_not_inner_pauses(self):
        with tempfile.TemporaryDirectory() as d:
            wav = Path(d) / "b.wav"
            _make(wav, [("speech", 2.5), ("gap", 0.5), ("speech", 2.0),   # line 1 with inner pause
                        ("gap", 2.0), ("speech", 3.0),                     # line 2
                        ("gap", 2.0), ("speech", 2.0), ("gap", 0.5), ("speech", 2.0)])  # line 3
            spans = _split_batch(wav, ["x" * 45, "x" * 30, "x" * 40])
            self.assertIsNotNone(spans)
            self.assertEqual(len(spans), 3)
            self.assertAlmostEqual(spans[0][1], 6.0, delta=0.3)   # middle of first 2 s gap
            self.assertAlmostEqual(spans[1][1], 11.0, delta=0.3)

    def test_rejects_when_too_few_gaps(self):
        with tempfile.TemporaryDirectory() as d:
            wav = Path(d) / "b.wav"
            _make(wav, [("speech", 5.0)])
            self.assertIsNone(_split_batch(wav, ["a" * 10, "b" * 10, "c" * 10]))


if __name__ == "__main__":
    unittest.main()
