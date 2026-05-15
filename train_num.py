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


def load_mnist(npz_path="mnist.npz", sample_per_class=2000):
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
            img = img.resize((16, 16), Image.Resampling.LANCZOS)
            pixels = np.asarray(img, dtype=np.float32).ravel() / 255.0
            X_out.append(pixels)
            y_out.append(label)

    X_arr = np.array(X_out, dtype=np.float32)
    y_arr = np.array(y_out, dtype=np.int64)
    rng2 = np.random.RandomState(123)
    indices = rng2.permutation(len(X_arr))
    return X_arr[indices], y_arr[indices]


def _im2col(X, KH, KW, stride=1):
    N, C, H, W = X.shape
    OH = (H - KH) // stride + 1
    OW = (W - KW) // stride + 1
    cols = np.zeros((N, C * KH * KW, OH * OW), dtype=np.float32)
    for i in range(OH):
        for j in range(OW):
            patch = X[:, :, i:i+KH, j:j+KW]
            cols[:, :, i * OW + j] = patch.reshape(N, -1)
    return cols, OH, OW


def _col2im(cols, X_shape, KH, KW, stride=1):
    N, C, H, W = X_shape
    OH = (H - KH) // stride + 1
    OW = (W - KW) // stride + 1
    X = np.zeros(X_shape, dtype=np.float32)
    for i in range(OH):
        for j in range(OW):
            patch = cols[:, :, i * OW + j].reshape(N, C, KH, KW)
            X[:, :, i:i+KH, j:j+KW] += patch
    return X


class CNN:
    def __init__(self):
        rng = np.random.RandomState(42)
        self.conv1_w = (rng.randn(8, 1, 3, 3) * np.sqrt(2.0 / (1 * 3 * 3))).astype(np.float32)
        self.conv1_b = np.zeros(8, dtype=np.float32)
        fc1_in = 8 * 7 * 7
        self.fc1_w = (rng.randn(64, fc1_in) * np.sqrt(2.0 / fc1_in)).astype(np.float32)
        self.fc1_b = np.zeros(64, dtype=np.float32)
        self.fc2_w = (rng.randn(10, 64) * np.sqrt(2.0 / 64)).astype(np.float32)
        self.fc2_b = np.zeros(10, dtype=np.float32)

    def forward(self, X_flat):
        N = X_flat.shape[0]
        self.X2d = X_flat.reshape(N, 1, 16, 16)

        self.cols1, OH1, OW1 = _im2col(self.X2d, 3, 3)
        w1_row = self.conv1_w.reshape(8, -1)
        conv1_out = w1_row @ self.cols1 + self.conv1_b.reshape(8, 1)
        self.z1 = conv1_out.reshape(N, 8, OH1, OW1)
        self.a1 = np.maximum(0, self.z1)

        N2, C2, H2, W2_ = self.a1.shape
        a1_6d = self.a1.reshape(N2, C2, H2 // 2, 2, W2_ // 2, 2)
        self.p1 = a1_6d.max(axis=3).max(axis=4)
        a1_flat = a1_6d.reshape(N2, C2, H2 // 2, 2, W2_ // 2 * 2)
        self.p1_idx = a1_flat.argmax(axis=3)

        self.flat = self.p1.reshape(N, -1)
        if self.flat.shape[1] != 8 * 7 * 7:
            self.flat = self.flat[:, :8 * 7 * 7]

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

        da1 = np.zeros_like(self.a1)
        N2, C2, H2, W2_ = self.a1.shape
        pH, pW = H2 // 2, W2_ // 2
        for i in range(pH):
            for j in range(pW):
                idx = self.p1_idx[:, :, i, j]
                for n in range(N2):
                    for c in range(C2):
                        mi = 2 * i + (idx[n, c] // 2)
                        mj = 2 * j + (idx[n, c] % 2)
                        da1[n, c, mi, mj] += dp1[n, c, i, j]
        da1[self.z1 <= 0] = 0

        dconv1_cols = da1.reshape(N, 8, -1)

        dconv1_w = np.einsum('nof,nif->oi', dconv1_cols, self.cols1).reshape(8, 1, 3, 3)
        dconv1_b = np.sum(da1.reshape(N, 8, -1), axis=(0, 2))

        return dconv1_w, dconv1_b, dfc1_w, dfc1_b, dfc2_w, dfc2_b


def augment_strong(X, y):
    N = X.shape[0]
    X_aug = X.copy()
    noise = np.random.uniform(-0.03, 0.03, X_aug.shape).astype(np.float32)
    X_aug += noise
    X_aug = np.clip(X_aug, 0.0, 1.0)
    X_aug2d = X_aug.reshape(N, 1, 16, 16)
    shift_y = np.random.randint(-2, 3)
    shift_x = np.random.randint(-2, 3)
    X_aug2d = np.roll(X_aug2d, shift_y, axis=2)
    X_aug2d = np.roll(X_aug2d, shift_x, axis=3)
    X_aug = X_aug2d.reshape(N, 256)
    return X_aug, y


def augment_light(X):
    noise = np.random.uniform(-0.01, 0.01, X.shape).astype(np.float32)
    X = X + noise
    return np.clip(X, 0.0, 1.0)


def train(data_dir="num_samples", mnist_path="mnist.npz", epochs=600, lr=0.01, momentum=0.9):
    X_game, y_game = load_samples(data_dir)
    print(f"Loaded {len(X_game)} game samples from {data_dir}")

    use_mnist = os.path.exists(mnist_path)
    if use_mnist:
        X_mnist, y_mnist = load_mnist(mnist_path)
        print(f"Loaded {len(X_mnist)} MNIST samples from {mnist_path}")
        mnist_per_epoch = min(3000, len(X_mnist))
    else:
        print(f"[warn] {mnist_path} not found, training with game samples only")
        X_mnist, y_mnist = None, None

    net = CNN()
    v_cw = np.zeros_like(net.conv1_w)
    v_cb = np.zeros_like(net.conv1_b)
    v_f1w = np.zeros_like(net.fc1_w)
    v_f1b = np.zeros_like(net.fc1_b)
    v_f2w = np.zeros_like(net.fc2_w)
    v_f2b = np.zeros_like(net.fc2_b)

    for epoch in range(epochs):
        if epoch > 0 and epoch % 200 == 0:
            lr *= 0.5

        X_game_aug, y_game_aug = augment_strong(X_game, y_game)

        if use_mnist:
            epoch_rng = np.random.RandomState(epoch)
            idx = epoch_rng.choice(len(X_mnist), mnist_per_epoch, replace=False)
            X_mnist_batch, y_mnist_batch = X_mnist[idx], y_mnist[idx]
            X_mnist_batch = augment_light(X_mnist_batch)

            X_batch = np.vstack([X_game_aug, X_mnist_batch])
            y_batch = np.hstack([y_game_aug, y_mnist_batch])
            perm = epoch_rng.permutation(len(X_batch))
            X_batch = X_batch[perm]
            y_batch = y_batch[perm]
        else:
            X_batch, y_batch = X_game_aug, y_game_aug

        net.forward(X_batch)
        loss_val = net.loss(y_batch)

        grads = net.backward(X_batch, y_batch)
        dcw, dcb, df1w, df1b, df2w, df2b = grads

        dcw += 0.001 * net.conv1_w
        df1w += 0.001 * net.fc1_w
        df2w += 0.001 * net.fc2_w

        v_cw = momentum * v_cw - lr * dcw
        v_cb = momentum * v_cb - lr * dcb
        v_f1w = momentum * v_f1w - lr * df1w
        v_f1b = momentum * v_f1b - lr * df1b
        v_f2w = momentum * v_f2w - lr * df2w
        v_f2b = momentum * v_f2b - lr * df2b

        net.conv1_w += v_cw
        net.conv1_b += v_cb
        net.fc1_w += v_f1w
        net.fc1_b += v_f1b
        net.fc2_w += v_f2w
        net.fc2_b += v_f2b

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