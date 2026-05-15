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


class CNN:
    def __init__(self):
        rng = np.random.RandomState(42)
        self.conv1_w = (rng.randn(8, 1, 3, 3) * 0.1).astype(np.float32)
        self.conv1_b = np.zeros(8, dtype=np.float32)
        self.fc1_w = (rng.randn(64, 392) * 0.01).astype(np.float32)
        self.fc1_b = np.zeros(64, dtype=np.float32)
        self.fc2_w = (rng.randn(10, 64) * 0.01).astype(np.float32)
        self.fc2_b = np.zeros(10, dtype=np.float32)

    def _conv_forward(self, X, w, b):
        N, C_in, H, W = X.shape
        C_out, _, KH, KW = w.shape
        OH = H - KH + 1
        OW = W - KW + 1
        out = np.zeros((N, C_out, OH, OW), dtype=np.float32)
        for f in range(C_out):
            for i in range(OH):
                for j in range(OW):
                    patch = X[:, :, i:i+KH, j:j+KW]
                    out[:, f, i, j] = np.sum(patch * w[f], axis=(1, 2, 3)) + b[f]
        return out

    def _maxpool_forward(self, X, size=2):
        N, C, H, W = X.shape
        OH = H // size
        OW = W // size
        out = np.zeros((N, C, OH, OW), dtype=np.float32)
        self.pool_mask = np.zeros_like(X)
        for i in range(OH):
            for j in range(OW):
                patch = X[:, :, i*size:(i+1)*size, j*size:(j+1)*size]
                idx = np.argmax(patch.reshape(N, C, -1), axis=2)
                for n in range(N):
                    for c in range(C):
                        mi = i * size + idx[n, c] // size
                        mj = j * size + idx[n, c] % size
                        out[n, c, i, j] = X[n, c, mi, mj]
                        self.pool_mask[n, c, mi, mj] = 1
        return out

    def forward(self, X_flat):
        self.X_flat = X_flat
        N = X_flat.shape[0]
        self.X2d = X_flat.reshape(N, 1, 16, 16)

        self.z1 = self._conv_forward(self.X2d, self.conv1_w, self.conv1_b)
        self.a1 = np.maximum(0, self.z1)
        self.p1 = self._maxpool_forward(self.a1)

        self.flat = self.p1.reshape(N, -1)
        if self.flat.shape[1] != 392:
            self.flat = self.flat[:, :392]

        self.z2 = self.flat @ self.fc1_w.T + self.fc1_b
        self.a2 = np.maximum(0, self.z2)

        self.z3 = self.a2 @ self.fc2_w.T + self.fc2_b
        shifted = self.z3 - np.max(self.z3, axis=1, keepdims=True)
        exps = np.exp(shifted)
        self.probs = exps / np.sum(exps, axis=1, keepdims=True)
        return self.probs

    def loss(self, y):
        N = len(y)
        correct = self.probs[np.arange(N), y]
        return -np.mean(np.log(correct + 1e-8))

    def backward(self, X_flat, y):
        N = len(y)
        dout = self.probs.copy()
        dout[np.arange(N), y] -= 1
        dout /= N

        dfc2_w = dout.T @ self.a2
        dfc2_b = np.sum(dout, axis=0)

        da2 = dout @ self.fc2_w
        da2[self.a2 <= 0] = 0

        dfc1_w = da2.T @ self.flat
        dfc1_b = np.sum(da2, axis=0)

        dflat = da2 @ self.fc1_w
        dp1 = dflat.reshape(self.p1.shape)

        da1 = np.zeros_like(self.z1)
        N, C, H, W = self.p1.shape
        for i in range(H):
            for j in range(W):
                for n in range(N):
                    for c in range(C):
                        mi = i * 2
                        mj = j * 2
                        da1[n, c, mi, mj] = dp1[n, c, i, j] * self.pool_mask[n, c, mi, mj]
        da1[self.z1 <= 0] = 0

        dconv1_w = np.zeros_like(self.conv1_w)
        dconv1_b = np.zeros_like(self.conv1_b)
        OH = 14
        for f in range(8):
            for n in range(N):
                for i in range(OH):
                    for j in range(OH):
                        patch = self.X2d[n, :, i:i+3, j:j+3]
                        dconv1_w[f] += da1[n, f, i, j] * patch
            dconv1_b[f] = np.sum(da1[:, f])

        return dconv1_w, dconv1_b, dfc1_w, dfc1_b, dfc2_w, dfc2_b


def augment(X, y):
    N = X.shape[0]
    X_aug = X.copy()
    noise = np.random.uniform(-0.02, 0.02, X_aug.shape).astype(np.float32)
    X_aug += noise
    X_aug = np.clip(X_aug, 0.0, 1.0)
    X_aug2d = X_aug.reshape(N, 1, 16, 16)
    shift_y = np.random.randint(-1, 2)
    shift_x = np.random.randint(-1, 2)
    X_aug2d = np.roll(X_aug2d, shift_y, axis=2)
    X_aug2d = np.roll(X_aug2d, shift_x, axis=3)
    X_aug = X_aug2d.reshape(N, 256)
    return X_aug, y


def train(data_dir="num_samples", epochs=800, lr=0.01, momentum=0.9):
    X, y = load_samples(data_dir)
    print(f"Loaded {len(X)} samples")

    net = CNN()
    v_cw1 = np.zeros_like(net.conv1_w)
    v_cb1 = np.zeros_like(net.conv1_b)
    v_fw1 = np.zeros_like(net.fc1_w)
    v_fb1 = np.zeros_like(net.fc1_b)
    v_fw2 = np.zeros_like(net.fc2_w)
    v_fb2 = np.zeros_like(net.fc2_b)

    for epoch in range(epochs):
        if epoch > 0 and epoch % 200 == 0:
            lr *= 0.5

        X_batch, y_batch = augment(X, y)

        net.forward(X_batch)
        loss_val = net.loss(y_batch)

        grads = net.backward(X_batch, y_batch)
        dcw, dcb, dfw1, dfb1, dfw2, dfb2 = grads

        dcw += 0.001 * net.conv1_w
        dfw1 += 0.001 * net.fc1_w
        dfw2 += 0.001 * net.fc2_w

        v_cw1 = momentum * v_cw1 - lr * dcw
        v_cb1 = momentum * v_cb1 - lr * dcb
        v_fw1 = momentum * v_fw1 - lr * dfw1
        v_fb1 = momentum * v_fb1 - lr * dfb1
        v_fw2 = momentum * v_fw2 - lr * dfw2
        v_fb2 = momentum * v_fb2 - lr * dfb2

        net.conv1_w += v_cw1
        net.conv1_b += v_cb1
        net.fc1_w += v_fw1
        net.fc1_b += v_fb1
        net.fc2_w += v_fw2
        net.fc2_b += v_fb2

        if epoch % 50 == 0:
            preds = np.argmax(net.probs, axis=1)
            acc = np.mean(preds == y_batch)
            print(f"  Epoch {epoch:3d}  loss={loss_val:.4f}  acc={acc:.3f}  lr={lr:.4f}")

    return net


def save_weights(net, path="num_weights.json"):
    w = {
        "conv1_w": net.conv1_w.tolist(),
        "conv1_b": net.conv1_b.tolist(),
        "fc1_w": net.fc1_w.tolist(),
        "fc1_b": net.fc1_b.tolist(),
        "fc2_w": net.fc2_w.tolist(),
        "fc2_b": net.fc2_b.tolist(),
        "arch": "cnn",
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(w, f, separators=(",", ":"))
    size_kb = os.path.getsize(path) / 1024
    print(f"Weights saved to {path} ({size_kb:.1f} KB)")


def collect_samples(screenshot_path, config_path="num_config.json", output_dir="num_samples"):
    """Collect raw digit crops from a screenshot for later manual sorting.

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