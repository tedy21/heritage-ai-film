# %% [markdown]
# # Wan 2.2 TI2V-5B image-to-video on Kaggle (T4 x2)
# Paste each `# %%` cell into a Kaggle notebook (GPU T4 x2, Internet ON).
# Upload a dataset containing `storyboard.json` and `outputs/keyframes/` from the repo
# (or zip them: `zip -r kaggle_in.zip storyboard.json outputs/keyframes`).
# Output: /kaggle/working/clips/<shot>.mp4 and /kaggle/working/clips/timings.json
# -> download into the repo's outputs/clips/ and run `make import-gpu`.
#
# Status of the API (checked 2026-11-25): the HF repo is a `WanPipeline`
# (expand_timesteps=True); diffusers documents `image=` only on
# `WanImageToVideoPipeline`. Cell 3 tries I2V first and prints the call
# signature so the first run tells us which works (record it in FAILURES.md).

# %%
!pip install -q git+https://github.com/huggingface/diffusers transformers accelerate ftfy imageio imageio-ffmpeg
import diffusers, torch; print(diffusers.__version__, torch.__version__, torch.cuda.get_device_name(0))

# %%
import glob, inspect, json, os, time
from pathlib import Path
import numpy as np
from PIL import Image
from diffusers import AutoencoderKLWan
from diffusers.utils import export_to_video

IN = Path(sorted(glob.glob("/kaggle/input/**/storyboard.json", recursive=True))[0]).parent
OUTD = Path("/kaggle/working/clips"); OUTD.mkdir(parents=True, exist_ok=True)
sb = json.loads((IN / "storyboard.json").read_text())
kf = json.loads((IN / "outputs/keyframes/manifest.json").read_text())
MODEL = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
# Draft settings for a T4 (plan: draft low, finish only chosen shots)
W, H, FRAMES, STEPS, CFG, FPS = 832, 480, 97, 30, 5.0, 24   # 97 = 4*24+1 frames ~ 4 s
DTYPE = torch.float16  # T4 has no fast bf16; watch for NaN/black frames (then try bfloat16)

# %%
vae = AutoencoderKLWan.from_pretrained(MODEL, subfolder="vae", torch_dtype=torch.float32)
mode = None
try:
    from diffusers import WanImageToVideoPipeline
    pipe = WanImageToVideoPipeline.from_pretrained(MODEL, vae=vae, torch_dtype=DTYPE)
    mode = "WanImageToVideoPipeline"
except Exception as e:
    print("I2V pipeline failed to load:", repr(e)[:300])
    from diffusers import WanPipeline
    pipe = WanPipeline.from_pretrained(MODEL, vae=vae, torch_dtype=DTYPE)
    mode = "WanPipeline"
pipe.enable_model_cpu_offload()
try:
    pipe.vae.enable_tiling()
except Exception:
    pass
sig = inspect.signature(pipe.__call__)
print(mode, "accepts image=" , "image" in sig.parameters)

# %%
def load_keyframe(rel):
    img = Image.open(IN / rel).convert("RGB")
    # centre-crop the square keyframe to 16:9 then resize to the draft size
    w, h = img.size; ch = int(w * H / W)
    top = (h - ch) // 2
    return img.crop((0, top, w, top + ch)).resize((W, H), Image.LANCZOS)

timings_path = OUTD / "timings.json"
timings = json.loads(timings_path.read_text()) if timings_path.exists() else []
NEG = "static, blurry, distorted, deformed face, extra fingers, text, watermark, flicker, morphing"
todo = [s for s in sb["shots"] if s["render"] == "wan" and not (OUTD / f"{s['id']}.mp4").exists()]
print("to render:", [s["id"] for s in todo])
for s in todo:                                  # saves after every shot (sessions time out)
    t0 = time.time()
    kwargs = dict(prompt=s["motion_prompt"], negative_prompt=NEG, height=H, width=W,
                  num_frames=FRAMES, guidance_scale=CFG, num_inference_steps=STEPS,
                  generator=torch.Generator("cpu").manual_seed(s["seed"]))
    if "image" in sig.parameters:
        kwargs["image"] = load_keyframe(kf[s["id"]])
    try:
        frames = pipe(**kwargs).frames[0]
        export_to_video(frames, str(OUTD / f"{s['id']}.mp4"), fps=FPS)
        status, err = "ok", None
    except Exception as e:
        status, err = "error", repr(e)[:400]
        torch.cuda.empty_cache()
    rec = {"stage": "clips", "item": s["id"], "provider": "kaggle-t4", "model": MODEL, "pipeline": mode,
           "params": {k: v for k, v in kwargs.items() if k not in ("image", "generator")},
           "seed": s["seed"], "status": status, "latency_s": round(time.time() - t0, 1),
           "gpu_s": round(time.time() - t0, 1), "error": err,
           "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2)}
    timings.append(rec); timings_path.write_text(json.dumps(timings, indent=2))
    print(rec)

# %%
!cd /kaggle/working && zip -qr clips.zip clips && ls -la clips
