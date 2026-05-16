import numpy as np
import json
import os
from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F


def load_samples(data_dir="num_samples", img_size=24):
    X, y = [], []
    for label in range(10):
        label_dir = os.path.join(data_dir, str(label))
        if not os.path.isdir(label_dir):
            continue
        for fname in os.listdir(label_dir):
            if not fname.lower().endswith(".png"):
                continue
            fpath = os.path.join(label_dir, fname)
            try:
                img = Image.open(fpath).convert("L")
            except Exception:
                print(f"  [warn] skipping corrupted image: {fpath}")
                continue
            img = img.resize((img_size, img_size), Image.Resampling.LANCZOS)
            pixels = np.asarray(img, dtype=np.float32).ravel() / 255.0
            X.append(pixels)
            y.append(label)
    if not X:
        raise RuntimeError(f"No .png samples found under {data_dir}/0/ through {data_dir}/9/")
    rng = np.random.RandomState(42)
    indices = rng.permutation(len(X))
    return np.array(X)[indices], np.array(y)[indices]


def load_mnist(npz_path="mnist.npz", sample_per_class=2000, img_size=24):
    data = np.load(npz_path)
    X_raw = data["x_train"].astype(np.float32) / 255.0
    y_raw = data["y_train"]
    data.close()

    X_out, y_out = [], []
    rng = np.random.RandomState(42)
    for label in range(10):
        idx = np.where(y_raw == label)[0]
        take = min(sample_per_class, len(idx))
        chosen = rng.choice(idx, take, replace=False)
        for i in chosen:
            img = Image.fromarray((X_raw[i] * 255).astype(np.uint8), mode="L")
            img = img.resize((img_size, img_size), Image.Resampling.LANCZOS)
            pixels = np.asarray(img, dtype=np.float32).ravel() / 255.0
            X_out.append(pixels)
            y_out.append(label)

    X_arr = np.array(X_out, dtype=np.float32)
    y_arr = np.array(y_out, dtype=np.int64)
    rng2 = np.random.RandomState(123)
    indices = rng2.permutation(len(X_arr))
    return X_arr[indices], y_arr[indices]


def augment_strong(X, y, img_size=24):
    N = X.shape[0]
    rng = np.random.RandomState()
    X_aug = X.copy()
    noise = rng.uniform(-0.03, 0.03, X_aug.shape).astype(np.float32)
    X_aug += noise
    X_aug = np.clip(X_aug, 0.0, 1.0)
    X_aug = X_aug.reshape(N, 1, img_size, img_size)
    shift_y = rng.randint(-2, 3)
    shift_x = rng.randint(-2, 3)
    X_aug = np.roll(X_aug, shift_y, axis=2)
    X_aug = np.roll(X_aug, shift_x, axis=3)
    return X_aug.reshape(N, 1, img_size, img_size), y


def augment_light(X, img_size=24):
    rng = np.random.RandomState()
    noise = rng.uniform(-0.01, 0.01, X.shape).astype(np.float32)
    X = X + noise
    X = X.reshape(-1, 1, img_size, img_size)
    return np.clip(X, 0.0, 1.0)


class CNNModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 8, 3, padding=0)
        self.fc1 = nn.Linear(8 * 11 * 11, 64)
        self.fc2 = nn.Linear(64, 10)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.max_pool2d(x, 2)
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x


def compute_acc(logits, y):
    preds = torch.argmax(logits, dim=1)
    return (preds == y).float().mean().item()


def pretrain_mnist(mnist_path="mnist.npz", epochs=100, lr=0.01, batch_size=256, img_size=24):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    X_all, y_all = load_mnist(mnist_path, sample_per_class=4000, img_size=img_size)
    print(f"Loaded {len(X_all)} MNIST samples")

    model = CNNModel().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=0.001)

    N = len(X_all)
    for epoch in range(epochs):
        rng = np.random.RandomState(epoch)
        idx = rng.choice(N, min(batch_size * 8, N), replace=False)
        X_batch = torch.tensor(X_all[idx], dtype=torch.float32, device=device)
        X_batch = X_batch.view(-1, 1, img_size, img_size)
        X_batch = X_batch + torch.randn_like(X_batch) * 0.02
        X_batch = torch.clamp(X_batch, 0, 1)
        y_batch = torch.tensor(y_all[idx], dtype=torch.long, device=device)

        optimizer.zero_grad()
        logits = model(X_batch)
        loss = F.cross_entropy(logits, y_batch)
        loss.backward()
        optimizer.step()

        if epoch % 10 == 0:
            acc = compute_acc(logits, y_batch)
            print(f"  MNIST epoch {epoch:3d}  loss={loss.item():.4f}  acc={acc:.3f}")

    return model, device


def train_mixed(data_dir="num_samples", mnist_path="mnist.npz",
                epochs=250, lr=0.01, batch_size=None, img_size=24):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    X_game, y_game = load_samples(data_dir, img_size=img_size)
    print(f"Loaded {len(X_game)} game samples")

    use_mnist = os.path.exists(mnist_path)
    if use_mnist:
        X_mnist, y_mnist = load_mnist(mnist_path, sample_per_class=3000, img_size=img_size)
        print(f"Loaded {len(X_mnist)} MNIST samples")
        mnist_per_epoch = min(4000, len(X_mnist))
    else:
        print(f"[warn] {mnist_path} not found, training with game samples only")
        X_mnist, y_mnist = None, None

    model = CNNModel().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=0.001)

    for epoch in range(epochs):
        X_ga, y_ga = augment_strong(X_game, y_game, img_size=img_size)

        if use_mnist:
            epoch_rng = np.random.RandomState(epoch)
            idx = epoch_rng.choice(len(X_mnist), mnist_per_epoch, replace=False)
            X_mb = augment_light(X_mnist[idx], img_size=img_size)
            y_mb = y_mnist[idx]

            X_all = np.vstack([X_ga, X_mb.reshape(-1, 1, img_size, img_size)])
            y_all = np.hstack([y_ga, y_mb])
            perm = epoch_rng.permutation(len(X_all))
            X_all = X_all[perm]
            y_all = y_all[perm]
        else:
            X_all, y_all = X_ga, y_ga

        X_batch = torch.tensor(X_all, dtype=torch.float32, device=device)
        X_batch = torch.clamp(X_batch, 0, 1)
        y_batch = torch.tensor(y_all, dtype=torch.long, device=device)

        optimizer.zero_grad()
        logits = model(X_batch)
        loss = F.cross_entropy(logits, y_batch)
        loss.backward()
        optimizer.step()

        if epoch % 10 == 0:
            acc = compute_acc(logits, y_batch)
            print(f"  Epoch {epoch:3d}  loss={loss.item():.4f}  acc={acc:.3f}")

    return model


def export_weights(model, path="num_weights.json", save_torch=True):
    w = {
        "conv1_w": model.conv1.weight.detach().cpu().numpy().tolist(),
        "conv1_b": model.conv1.bias.detach().cpu().numpy().tolist(),
        "fc1_w": model.fc1.weight.detach().cpu().numpy().tolist(),
        "fc1_b": model.fc1.bias.detach().cpu().numpy().tolist(),
        "fc2_w": model.fc2.weight.detach().cpu().numpy().tolist(),
        "fc2_b": model.fc2.bias.detach().cpu().numpy().tolist(),
        "arch": "cnn",
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(w, f, separators=(",", ":"))
    size_kb = os.path.getsize(path) / 1024
    print(f"Weights saved to {path} ({size_kb:.1f} KB)")
    if save_torch:
        pt_path = path.replace(".json", ".pt")
        torch.save(model.state_dict(), pt_path)
        print(f"Torch model saved to {pt_path}")


def load_pytorch_model(path):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = CNNModel().to(device)
    model.load_state_dict(torch.load(path, map_location=device, weights_only=True))
    print(f"Loaded PyTorch model from {path}")
    return model


def collect_samples(screenshot_path, config_path="num_config.json", output_dir="num_samples"):
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from find_num import load_config

    screenshot = Image.open(screenshot_path)
    config = load_config(config_path)
    os.makedirs(output_dir, exist_ok=True)

    targets_cfg = config.get("targets", {})
    grid_cfg = config.get("grid", {})

    for name, region in targets_cfg.items():
        x1 = region.get("x1")
        y1 = region.get("y1")
        x2 = region.get("x2")
        y2 = region.get("y2")
        if None in (x1, y1, x2, y2):
            print(f"  [warn] missing coords for target: {name}")
            continue
        crop = screenshot.crop((x1, y1, x2, y2))
        fpath = os.path.join(output_dir, f"{name}.png")
        crop.save(fpath)
        print(f"Saved {fpath}")

        mid_x = x1 + (x2 - x1) // 2
        left = screenshot.crop((x1, y1, mid_x, y2))
        right = screenshot.crop((mid_x, y1, x2, y2))
        left.save(os.path.join(output_dir, f"{name}_L.png"))
        right.save(os.path.join(output_dir, f"{name}_R.png"))
        print(f"Saved {name}_L.png, {name}_R.png")

    if grid_cfg:
        gx = grid_cfg["x"]
        gy = grid_cfg["y"]
        cw = grid_cfg["cell_w"]
        ch = grid_cfg["cell_h"]
        cols = grid_cfg["cols"]
        rows = grid_cfg["rows"]

        for r in range(rows):
            for c in range(cols):
                x1 = gx + c * cw
                y1 = gy + r * ch
                x2 = x1 + cw
                y2 = y1 + ch

                crop = screenshot.crop((x1, y1, x2, y2))
                fpath = os.path.join(output_dir, f"cell_{r}_{c}.png")
                crop.save(fpath)
                print(f"Saved {fpath}")

                mid_x = x1 + cw // 2
                left = screenshot.crop((x1, y1, mid_x, y2))
                right = screenshot.crop((mid_x, y1, x2, y2))
                left.save(os.path.join(output_dir, f"cell_{r}_{c}_L.png"))
                right.save(os.path.join(output_dir, f"cell_{r}_{c}_R.png"))
                print(f"Saved cell_{r}_{c}_L.png, cell_{r}_{c}_R.png")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", default="train",
                        choices=["train", "collect", "pretrain-mnist"])
    parser.add_argument("--data-dir", default="num_samples")
    parser.add_argument("--weights", default="num_weights.json")
    parser.add_argument("--screenshot")
    parser.add_argument("--pretrained", default=None,
                        help="Path to pretrained weights for fine-tuning")
    args = parser.parse_args()

    if args.command == "collect":
        if not args.screenshot:
            print("Usage: python train_num.py collect --screenshot shot.png")
            exit(1)
        collect_samples(args.screenshot)
    elif args.command == "pretrain-mnist":
        if not os.path.exists("mnist.npz"):
            print("mnist.npz not found.")
            exit(1)
        print("=== Phase 1: Pretraining on MNIST (GPU) ===")
        model, _ = pretrain_mnist("mnist.npz", epochs=500)
        export_weights(model, "mnist_weights.json")
    else:
        print("=== Training mixed MNIST + game samples (GPU) ===")
        model = train_mixed(args.data_dir, epochs=1000, lr=0.01)
        export_weights(model, args.weights)