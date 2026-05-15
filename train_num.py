import numpy as np
import json
import os
from PIL import Image


def load_samples(data_dir="num_samples"):
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
            img = img.resize((16, 16), Image.Resampling.LANCZOS)
            pixels = np.asarray(img, dtype=np.float32).ravel() / 255.0
            X.append(pixels)
            y.append(label)
    if not X:
        raise RuntimeError(f"No .png samples found under {data_dir}/0/ through {data_dir}/9/")
    rng = np.random.RandomState(42)
    indices = rng.permutation(len(X))
    return np.array(X)[indices], np.array(y)[indices]


class Net:
    def __init__(self, input_dim=256, hidden_dim=32, output_dim=10):
        rng = np.random.RandomState(42)
        self.w1 = rng.randn(input_dim, hidden_dim).astype(np.float32) * 0.01
        self.b1 = np.zeros(hidden_dim, dtype=np.float32)
        self.w2 = rng.randn(hidden_dim, output_dim).astype(np.float32) * 0.01
        self.b2 = np.zeros(output_dim, dtype=np.float32)

    def forward(self, X):
        self.h = np.maximum(0, X @ self.w1 + self.b1)
        scores = self.h @ self.w2 + self.b2
        shifted = scores - np.max(scores, axis=1, keepdims=True)
        exps = np.exp(shifted)
        self.probs = exps / np.sum(exps, axis=1, keepdims=True)
        return self.probs

    def loss(self, y):
        N = len(y)
        correct_probs = self.probs[np.arange(N), y]
        return -np.mean(np.log(correct_probs + 1e-8))

    def backward(self, X, y):
        N = len(y)
        dout = self.probs.copy()
        dout[np.arange(N), y] -= 1
        dout /= N

        dw2 = self.h.T @ dout
        db2 = np.sum(dout, axis=0)
        dh = dout @ self.w2.T
        dh[self.h <= 0] = 0

        dw1 = X.T @ dh
        db1 = np.sum(dh, axis=0)

        return dw1, db1, dw2, db2


def augment(X, y):
    N = X.shape[0]
    X_aug = X.copy()
    noise = np.random.uniform(-0.02, 0.02, X_aug.shape).astype(np.float32)
    X_aug += noise
    X_aug = np.clip(X_aug, 0.0, 1.0)
    X_aug2d = X_aug.reshape(N, 16, 16)
    shift_y = np.random.randint(-1, 2)
    shift_x = np.random.randint(-1, 2)
    X_aug2d = np.roll(X_aug2d, shift_y, axis=1)
    X_aug2d = np.roll(X_aug2d, shift_x, axis=2)
    X_aug = X_aug2d.reshape(N, 256)
    return X_aug, y


def train(data_dir="num_samples", epochs=400, lr=0.01, momentum=0.9):
    X, y = load_samples(data_dir)
    print(f"Loaded {len(X)} samples")

    net = Net()
    v_w1, v_b1, v_w2, v_b2 = 0, 0, 0, 0

    for epoch in range(epochs):
        if epoch > 0 and epoch % 100 == 0:
            lr *= 0.5

        X_batch, y_batch = augment(X, y)

        net.forward(X_batch)
        loss_val = net.loss(y_batch)

        dw1, db1, dw2, db2 = net.backward(X_batch, y_batch)

        # L2 regularization
        dw2 += 0.001 * net.w2
        dw1 += 0.001 * net.w1

        # Momentum update
        v_w2 = momentum * v_w2 - lr * dw2
        v_b2 = momentum * v_b2 - lr * db2
        v_w1 = momentum * v_w1 - lr * dw1
        v_b1 = momentum * v_b1 - lr * db1

        net.w2 += v_w2
        net.b2 += v_b2
        net.w1 += v_w1
        net.b1 += v_b1

        if epoch % 50 == 0:
            preds = np.argmax(net.probs, axis=1)
            acc = np.mean(preds == y_batch)
            print(f"  Epoch {epoch:3d}  loss={loss_val:.4f}  acc={acc:.3f}  lr={lr:.4f}")

    return net


def save_weights(net, path="num_weights.json"):
    w = {
        "w1": net.w1.T.tolist(),
        "b1": net.b1.tolist(),
        "w2": net.w2.T.tolist(),
        "b2": net.b2.tolist(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(w, f, separators=(",", ":"))
    size_kb = os.path.getsize(path) / 1024
    print(f"Weights saved to {path} ({size_kb:.1f} KB)")


def collect_samples(screenshot_path, config_path="num_config.json", output_dir="num_samples"):
    """Collect raw digit crops from a screenshot for later manual sorting.

    Crops are saved to output_dir/ as {region_name}.png.
    User should then sort them into output_dir/0/ ... output_dir/9/ by digit label.

    Supports new config format with "targets" and "grid" blocks.
    Each grid cell is saved and also split into left/right halves for individual digits.
    """
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
                        choices=["train", "collect"])
    parser.add_argument("--data-dir", default="num_samples")
    parser.add_argument("--weights", default="num_weights.json")
    parser.add_argument("--screenshot")
    args = parser.parse_args()

    if args.command == "collect":
        if not args.screenshot:
            print("Usage: python train_num.py collect --screenshot shot.png")
            exit(1)
        collect_samples(args.screenshot)
    else:
        net = train(args.data_dir)
        save_weights(net, args.weights)
