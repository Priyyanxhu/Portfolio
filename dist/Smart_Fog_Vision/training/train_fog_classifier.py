"""
Smart Fog Vision — Fog vs Non-Fog Classifier Training
Dataset: D:\Foggyimages\fog_dataset\{fog images, non-fog images}
Model: MobileNetV2 transfer (ImageNet) -> 2 classes
Exports: PyTorch .pt + ONNX (for browser via onnxruntime-web)
"""

import pathlib
import random
import json
import time
from collections import Counter
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
import torchvision.transforms as T
import torchvision.models as models
from PIL import Image
import numpy as np

# --- Config ---
DATA_ROOT = Path(r"D:\Foggyimages\fog_dataset")
FOG_DIR = DATA_ROOT / "fog images"
NONFOG_DIR = DATA_ROOT / "non-fog images"
OUT_DIR = Path(r"D:\Smart_Fog_Vision\models")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
IMG_SIZE = 224
BATCH = 16
EPOCHS = 30
LR = 3e-4
WD = 1e-4
PATIENCE = 7
NUM_WORKERS = 0  # Windows + CPU => 0 is safest
DEVICE = torch.device("cpu")  # torch 2.13+cpu

CLASS_NAMES = ["non-fog", "fog"]  # 0=non-fog, 1=fog
NUM_CLASSES = 2

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

print(f"Device: {DEVICE}")
print(f"Fog dir: {FOG_DIR} exists={FOG_DIR.exists()}")
print(f"NonFog dir: {NONFOG_DIR} exists={NONFOG_DIR.exists()}")

# --- Collect files ---
fog_files = sorted(FOG_DIR.glob("*.jpg")) + sorted(FOG_DIR.glob("*.jpeg")) + sorted(FOG_DIR.glob("*.png"))
non_files = sorted(NONFOG_DIR.glob("*.jpg")) + sorted(NONFOG_DIR.glob("*.jpeg")) + sorted(NONFOG_DIR.glob("*.png"))
print(f"Found fog={len(fog_files)} non-fog={len(non_files)} total={len(fog_files)+len(non_files)}")

# Filter out potential non-images
def is_valid(p):
    try:
        with Image.open(p) as im:
            im.verify()
        return True
    except:
        return False

# quick validation - sample 10% for speed
# full check would be slow, but do full if needed
# We'll trust earlier check that none corrupt; skip full verify for speed

all_items = [(str(p), 1) for p in fog_files] + [(str(p), 0) for p in non_files]
random.shuffle(all_items)

# --- Stratified split manually (80 / 10 / 10 per class) ---
def stratified_split(items, ratios=(0.8, 0.1, 0.1), seed=SEED):
    # items: list of (path, label)
    random.Random(seed).shuffle(items)
    per_class = {0: [], 1: []}
    for p, l in items:
        per_class[l].append((p, l))
    splits = {"train": [], "val": [], "test": []}
    for label, lst in per_class.items():
        n = len(lst)
        n_train = int(n * ratios[0])
        n_val = int(n * ratios[1])
        # remainder goes to test
        splits["train"].extend(lst[:n_train])
        splits["val"].extend(lst[n_train:n_train+n_val])
        splits["test"].extend(lst[n_train+n_val:])
    for k in splits:
        random.Random(seed).shuffle(splits[k])
    return splits

splits = stratified_split(all_items)
for k, v in splits.items():
    cnt = Counter([l for _, l in v])
    print(f"{k}: {len(v)} total — fog={cnt[1]} non-fog={cnt[0]}")

# --- Transforms ---
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

train_tf = T.Compose([
    T.Resize(256),
    T.RandomResizedCrop(IMG_SIZE, scale=(0.75, 1.0), ratio=(0.85, 1.15)),
    T.RandomHorizontalFlip(p=0.5),
    T.RandomRotation(15),
    T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1, hue=0.02),
    T.RandomPerspective(distortion_scale=0.1, p=0.15),
    T.ToTensor(),
    T.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])

eval_tf = T.Compose([
    T.Resize(256),
    T.CenterCrop(IMG_SIZE),
    T.ToTensor(),
    T.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])

class FogDataset(Dataset):
    def __init__(self, items, transform=None):
        self.items = items
        self.transform = transform
    def __len__(self):
        return len(self.items)
    def __getitem__(self, idx):
        path, label = self.items[idx]
        # PIL handles all JPEG variations
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label, path

train_ds = FogDataset(splits["train"], train_tf)
val_ds   = FogDataset(splits["val"], eval_tf)
test_ds  = FogDataset(splits["test"], eval_tf)

print(f"Datasets — train {len(train_ds)} val {len(val_ds)} test {len(test_ds)}")

# --- Class weights for imbalanced ---
counts = Counter([l for _, l in splits["train"]])
total_train = len(splits["train"])
weights = []
for cls in range(NUM_CLASSES):
    cnt = counts[cls] if counts[cls]>0 else 1
    w = total_train / (NUM_CLASSES * cnt)
    weights.append(w)
print(f"Train counts {dict(counts)} weights {weights}")
class_weights = torch.tensor(weights, dtype=torch.float32).to(DEVICE)

# Optional Weighted sampler to balance batches (alternative to class weights) — we will use class weights in loss, but also use sampler for balanced sampling
# Compute sample weights for sampler
sample_weights = [ weights[label] for _, label in splits["train"] ]
sampler = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)

train_loader = DataLoader(train_ds, batch_size=BATCH, sampler=sampler, num_workers=NUM_WORKERS, pin_memory=False)
val_loader   = DataLoader(val_ds, batch_size=BATCH, shuffle=False, num_workers=NUM_WORKERS)
test_loader  = DataLoader(test_ds, batch_size=BATCH, shuffle=False, num_workers=NUM_WORKERS)

# --- Model ---
print("Loading MobileNetV2 pretrained...")
# Use new weights API; fallback if older torchvision
try:
    mnet = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
except:
    mnet = models.mobilenet_v2(pretrained=True)

# Freeze early? We'll fine-tune all with lower LR but keep backbone trainable
# Optionally freeze features for first 3 epochs via staged training; for now train all
in_features = mnet.classifier[1].in_features
# Add dropout + linear
mnet.classifier[1] = nn.Sequential(
    nn.Dropout(p=0.2),
    nn.Linear(in_features, NUM_CLASSES)
)
mnet = mnet.to(DEVICE)
print(mnet.classifier)

criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.05)
optimizer = torch.optim.AdamW(mnet.parameters(), lr=LR, weight_decay=WD)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)
# Alternative: ReduceLROnPlateau — we use cosine

# --- Helpers ---
def accuracy(logits, y):
    pred = logits.argmax(1)
    return (pred == y).float().mean().item()

def evaluate(loader, model):
    model.eval()
    total_loss = 0
    total_acc = 0
    total = 0
    all_preds = []
    all_labels = []
    all_logits = []
    with torch.no_grad():
        for imgs, labels, _ in loader:
            imgs = imgs.to(DEVICE)
            labels = labels.to(DEVICE)
            logits = model(imgs)
            loss = criterion(logits, labels)
            total_loss += loss.item() * imgs.size(0)
            total_acc += (logits.argmax(1) == labels).sum().item()
            total += imgs.size(0)
            all_preds.extend(logits.argmax(1).cpu().tolist())
            all_labels.extend(labels.cpu().tolist())
            all_logits.extend(logits.cpu().tolist())
    avg_loss = total_loss / total if total>0 else 0
    acc = total_acc / total if total>0 else 0
    return avg_loss, acc, all_preds, all_labels, all_logits

# Confusion + per class metrics without sklearn
def compute_metrics(preds, labels):
    # 2-class
    cm = [[0,0],[0,0]]  # rows true, cols pred
    for p, t in zip(preds, labels):
        cm[t][p] += 1
    # per class precision recall
    metrics = {}
    for cls in range(NUM_CLASSES):
        tp = cm[cls][cls]
        fp = sum(cm[r][cls] for r in range(NUM_CLASSES)) - tp
        fn = sum(cm[cls][c] for c in range(NUM_CLASSES)) - tp
        prec = tp / (tp+fp) if (tp+fp)>0 else 0
        rec = tp / (tp+fn) if (tp+fn)>0 else 0
        f1 = 2*prec*rec/(prec+rec) if (prec+rec)>0 else 0
        metrics[CLASS_NAMES[cls]] = {"precision": prec, "recall": rec, "f1": f1, "support": sum(cm[cls])}
    # overall
    acc = sum(cm[i][i] for i in range(NUM_CLASSES)) / max(1, sum(sum(row) for row in cm))
    # macro f1
    macro_f1 = np.mean([metrics[c]["f1"] for c in CLASS_NAMES])
    return cm, metrics, acc, macro_f1

# --- Training loop ---
best_val_acc = 0
best_val_f1 = 0
best_state = None
epochs_no_improve = 0

history = {"train_loss":[], "train_acc":[], "val_loss":[], "val_acc":[], "val_f1":[], "lr":[]}

t_start = time.time()
for epoch in range(1, EPOCHS+1):
    mnet.train()
    running_loss = 0
    running_acc = 0
    seen = 0
    # tqdm-like
    for i, (imgs, labels, _) in enumerate(train_loader):
        imgs = imgs.to(DEVICE)
        labels = labels.to(DEVICE)
        optimizer.zero_grad()
        logits = mnet(imgs)
        loss = criterion(logits, labels)
        loss.backward()
        # grad clip
        nn.utils.clip_grad_norm_(mnet.parameters(), 1.0)
        optimizer.step()

        running_loss += loss.item() * imgs.size(0)
        running_acc += (logits.argmax(1) == labels).sum().item()
        seen += imgs.size(0)
        if (i+1) % 20 == 0:
            print(f"  epoch {epoch} batch {i+1}/{len(train_loader)} loss {loss.item():.4f} acc {(logits.argmax(1)==labels).float().mean():.3f}")

    train_loss = running_loss / seen
    train_acc = running_acc / seen

    val_loss, val_acc, val_preds, val_labels, _ = evaluate(val_loader, mnet)
    _, val_metrics, _, val_f1 = compute_metrics(val_preds, val_labels)

    scheduler.step()
    cur_lr = optimizer.param_groups[0]["lr"]

    history["train_loss"].append(train_loss)
    history["train_acc"].append(train_acc)
    history["val_loss"].append(val_loss)
    history["val_acc"].append(val_acc)
    history["val_f1"].append(val_f1)
    history["lr"].append(cur_lr)

    print(f"Epoch {epoch:02d}/{EPOCHS} | train loss {train_loss:.4f} acc {train_acc:.3f} | val loss {val_loss:.4f} acc {val_acc:.3f} f1 {val_f1:.3f} lr {cur_lr:.2e}")
    print(f"  val per-class: " + " | ".join([f"{c}: P{val_metrics[c]['precision']:.2f} R{val_metrics[c]['recall']:.2f} F1{val_metrics[c]['f1']:.2f}" for c in CLASS_NAMES]))

    # checkpoint best by val_f1 (macro)
    if val_f1 > best_val_f1:
        best_val_f1 = val_f1
        best_val_acc = val_acc
        best_state = {k: v.cpu() for k, v in mnet.state_dict().items()}
        epochs_no_improve = 0
        # save immediately
        torch.save(mnet.state_dict(), OUT_DIR / "best_mobilenetv2_fog.pt")
        print(f"  >> New best val F1 {val_f1:.4f} saved to best_mobilenetv2_fog.pt")
    else:
        epochs_no_improve += 1
        if epochs_no_improve >= PATIENCE:
            print(f"Early stopping at epoch {epoch} (no improve {PATIENCE})")
            break

    # also save last
    torch.save(mnet.state_dict(), OUT_DIR / "last_mobilenetv2_fog.pt")

t_total = time.time() - t_start
print(f"Training done in {t_total/60:.1f} min. Best val acc {best_val_acc:.3f} f1 {best_val_f1:.3f}")

# Load best for final eval
if best_state is not None:
    mnet.load_state_dict({k: v.to(DEVICE) for k,v in best_state.items()})
else:
    # load from file if exists
    best_path = OUT_DIR / "best_mobilenetv2_fog.pt"
    if best_path.exists():
        mnet.load_state_dict(torch.load(best_path, map_location=DEVICE))

# --- Final eval on val and test ---
for split_name, loader in [("val", val_loader), ("test", test_loader)]:
    loss, acc, preds, labels, logits = evaluate(loader, mnet)
    cm, metrics, _, f1 = compute_metrics(preds, labels)
    print(f"\n=== {split_name.upper()} ===")
    print(f"Loss {loss:.4f} Acc {acc:.3f} MacroF1 {f1:.3f}")
    print(f"Confusion [[TN,FP],[FN,TP]] where rows true non-fog/fog:\n  {cm[0]}\n  {cm[1]}")
    for c in CLASS_NAMES:
        print(f"  {c}: prec {metrics[c]['precision']:.3f} rec {metrics[c]['recall']:.3f} f1 {metrics[c]['f1']:.3f} supp {metrics[c]['support']}")
    # Save JSON
    result = {
        "split": split_name,
        "loss": loss,
        "accuracy": acc,
        "macro_f1": f1,
        "confusion_matrix": cm,
        "per_class": metrics,
        "class_names": CLASS_NAMES
    }
    with open(OUT_DIR / f"metrics_{split_name}.json", "w") as f:
        json.dump(result, f, indent=2)

# Save history
with open(OUT_DIR / "history.json", "w") as f:
    json.dump(history, f, indent=2)

# Save labels
with open(OUT_DIR / "labels.json", "w") as f:
    json.dump({"labels": CLASS_NAMES, "indices": {c:i for i,c in enumerate(CLASS_NAMES)}}, f, indent=2)

# Also save a small model card
card = {
    "model": "mobilenet_v2",
    "num_classes": NUM_CLASSES,
    "labels": CLASS_NAMES,
    "image_size": IMG_SIZE,
    "mean": IMAGENET_MEAN,
    "std": IMAGENET_STD,
    "best_val_acc": best_val_acc,
    "best_val_f1": best_val_f1,
    "train_time_min": t_total/60,
    "epochs_trained": len(history["train_loss"]),
    "dataset": {"fog": len(fog_files), "non_fog": len(non_files), "total": len(fog_files)+len(non_files)},
    "splits": {k: len(v) for k,v in splits.items()}
}
with open(OUT_DIR / "model_card.json", "w") as f:
    json.dump(card, f, indent=2)
print(f"Saved card to {OUT_DIR/'model_card.json'}")

# --- Export ONNX ---
print("Exporting ONNX...")
mnet.eval()
dummy = torch.randn(1, 3, IMG_SIZE, IMG_SIZE, device=DEVICE)
onnx_path = OUT_DIR / "fog_classifier.onnx"
try:
    torch.onnx.export(
        mnet,
        dummy,
        str(onnx_path),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
        do_constant_folding=True
    )
    print(f"ONNX saved to {onnx_path} size {onnx_path.stat().st_size/1024:.1f} KB")
    # Quick check with onnx if available
    try:
        import onnx
        model = onnx.load(str(onnx_path))
        onnx.checker.check_model(model)
        print("ONNX checker passed")
    except Exception as e:
        print(f"ONNX check skipped/failed: {e}")
except Exception as e:
    print(f"ONNX export failed: {e}")

# --- Inference sanity test on a few images ---
print("\nSanity inference on 4 samples from test:")
mnet.eval()
with torch.no_grad():
    for i in range(min(4, len(test_ds))):
        img, label, path = test_ds[i]
        logits = mnet(img.unsqueeze(0).to(DEVICE))
        probs = torch.softmax(logits, 1).cpu().numpy()[0]
        pred = int(probs.argmax())
        print(f"  {Path(path).name} true={CLASS_NAMES[label]} pred={CLASS_NAMES[pred]} probs=[non={probs[0]:.3f} fog={probs[1]:.3f}]")

print("\nDone. Check models folder:", OUT_DIR)
print("Next: integrate fog_classifier.onnx with browser (fog_classifier.js)")
