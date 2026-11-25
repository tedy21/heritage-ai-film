# %% [markdown]
# # ACE-Step 1.5 score candidates on Kaggle/Colab (T4)
# Generates 3 instrumental candidates from the storyboard's music caption.
# Output: /kaggle/working/music/*.flac + timings.json -> download into the repo's
# outputs/music/candidates/, listen UNDER the narration, then set
# `music.chosen` in storyboard.json and note the choice in EXPERIMENTS.md.
# API per docs/en/INFERENCE.md (checked 2026-11-25). T4 = 16 GB tier: LM 0.6B/1.7B,
# batch <= 4, CPU offload. We use backend "pt" to avoid vllm install issues.

# %%
# uv via pip is reliable on Kaggle (the curl installer's path varies)
%cd /kaggle/working
!pip install -q uv
!test -d ACE-Step-1.5 || git clone -q https://github.com/ACE-Step/ACE-Step-1.5.git
%cd /kaggle/working/ACE-Step-1.5
!uv sync

# %%
import glob, json
from pathlib import Path
sb_path = sorted(glob.glob("/kaggle/input/**/storyboard.json", recursive=True))[0]
music = json.loads(Path(sb_path).read_text())["music"]
Path("/kaggle/working/music").mkdir(parents=True, exist_ok=True)
gen = f'''
import json, time, torch
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import GenerationParams, GenerationConfig, generate_music
music = json.loads(open("{sb_path}").read())["music"]
dit, llm = AceStepHandler(), LLMHandler()
dit.initialize_service(project_root=".", config_path="acestep-v15-turbo", device="cuda")
llm.initialize(checkpoint_dir="./checkpoints", lm_model_path="acestep-5Hz-lm-0.6B", backend="pt", device="cuda")
timings = []
for seed in (301, 302, 303):          # one candidate per seed so each is reproducible
    t0 = time.time()
    params = GenerationParams(caption=music["caption"], instrumental=True, lyrics="[Instrumental]",
                              bpm=music["bpm"], keyscale=music["key"], duration=85, seed=seed)
    cfg = GenerationConfig(batch_size=1, use_random_seed=False, seeds=[seed], audio_format="flac")
    res = generate_music(dit, llm, params, cfg, save_dir="/kaggle/working/music")
    timings.append({{"stage": "music", "item": f"cand_{{seed}}", "provider": "kaggle-t4",
                    "model": "ACE-Step 1.5 turbo + lm-0.6B", "seed": seed,
                    "params": {{"caption": music["caption"], "bpm": music["bpm"], "key": music["key"], "duration": 85}},
                    "status": "ok" if res.success else "error", "error": None if res.success else str(res.error),
                    "latency_s": round(time.time() - t0, 1), "gpu_s": round(time.time() - t0, 1),
                    "outputs": [a["path"] for a in res.audios] if res.success else []}})
    json.dump(timings, open("/kaggle/working/music/timings.json", "w"), indent=2)
    print(timings[-1])
'''
Path("/kaggle/working/ACE-Step-1.5/gen.py").write_text(gen)

# %%
%cd /kaggle/working/ACE-Step-1.5
!uv run python gen.py
!ls -la /kaggle/working/music
