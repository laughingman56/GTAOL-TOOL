# pc_settings.bin 管理功能 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 ka_085.py 中增加 pc_settings.bin 的删除、备份和断网后自动恢复功能，按钮放在断网设置弹窗的定时控制行右侧。

**架构：** 在 ka_085.py 中新增4个文件操作函数（搜索、删除、备份、恢复），修改 `show_settings_ui()` 在 timer_frame 右侧加两个按钮，修改 `main()` 在 `recover_natdown()` 之后自动恢复。

**技术栈：** Python, customtkinter, tkinter.messagebox, shutil, os

---

### 任务 1：新增文件操作核心函数

**文件：**
- 修改：`ka_085.py`

- [ ] **步骤 1：在 ka_085.py 顶部添加 import**

在文件头部 import 区添加 `shutil` 和 `tkinter.messagebox`：

```python
import shutil
from tkinter import messagebox
```

- [ ] **步骤 2：在文件末尾（`main()` 函数之前）添加4个核心函数**

```python
def find_pc_settings_bin():
    docs = os.path.join(os.path.expanduser("~"), "Documents", "Rockstar Games")
    if not os.path.exists(docs):
        return None
    for root, dirs, files in os.walk(docs):
        for f in files:
            if f.lower() == "pc_settings.bin":
                return os.path.join(root, f)
    return None

def delete_pc_settings_bin():
    path = find_pc_settings_bin()
    if not path:
        messagebox.showwarning("提示", "未找到 pc_settings.bin")
        return
    try:
        os.remove(path)
        print(f"[pc_settings] 已删除: {path}")
    except Exception as e:
        messagebox.showerror("错误", f"删除失败: {e}")

def backup_pc_settings_bin():
    path = find_pc_settings_bin()
    if not path:
        messagebox.showwarning("提示", "未找到 pc_settings.bin")
        return
    desktop = os.path.join(os.path.expanduser("~"), "Desktop", "pc_settings.bin")
    try:
        shutil.copy2(path, desktop)
        print(f"[pc_settings] 已备份到: {desktop}")
        messagebox.showinfo("提示", "已备份到桌面")
    except Exception as e:
        messagebox.showerror("错误", f"备份失败: {e}")

def restore_pc_settings_bin():
    path = find_pc_settings_bin()
    if not path:
        return
    desktop = os.path.join(os.path.expanduser("~"), "Desktop", "pc_settings.bin")
    if not os.path.exists(desktop):
        return
    try:
        shutil.copy2(desktop, path)
        print(f"[pc_settings] 已从桌面恢复: {desktop} -> {path}")
    except Exception as e:
        print(f"[pc_settings] 恢复失败: {e}")
```

- [ ] **步骤 3：Commit**

```bash
git add ka_085.py
git commit -m "feat: 新增pc_settings.bin核心函数（搜索/删除/备份/恢复）"
```

---

### 任务 2：在断网设置弹窗添加删除和备份按钮

**文件：**
- 修改：`ka_085.py`（`show_settings_ui` 函数内的 timer_frame）

- [ ] **步骤 1：在 timer_frame 的 "秒" label pack 之后，添加两个按钮**

在 `ctk.CTkLabel(timer_frame, text="秒", ...).pack(side="left")` 之后（约第140行），添加：

```python
    btn_delete_pc = ctk.CTkButton(
        timer_frame,
        text="删除pc_settings.bin",
        font=("Microsoft YaHei", 12, "bold"),
        width=80,
        height=30,
        fg_color="transparent",
        text_color="#FF474C",
        hover_color="#FFE0E0",
        border_width=2,
        border_color="#FF474C",
        corner_radius=6,
        command=delete_pc_settings_bin
    )
    btn_delete_pc.pack(side="right", padx=(10, 2))

    btn_backup_pc = ctk.CTkButton(
        timer_frame,
        text="备份pc_settings.bin",
        font=("Microsoft YaHei", 12, "bold"),
        width=80,
        height=30,
        fg_color="transparent",
        text_color="#4CC768",
        hover_color="#E0FFE0",
        border_width=2,
        border_color="#4CC768",
        corner_radius=6,
        command=backup_pc_settings_bin
    )
    btn_backup_pc.pack(side="right", padx=(2, 0))
```

- [ ] **步骤 2：Commit**

```bash
git add ka_085.py
git commit -m "feat: 断网设置弹窗增加删除和备份pc_settings.bin按钮"
```

---

### 任务 3：在断网恢复后自动恢复 pc_settings.bin

**文件：**
- 修改：`ka_085.py`（`main()` 函数）

- [ ] **步骤 1：在 main() 的两个 recover_natdown() 调用之后添加 restore_pc_settings_bin()**

有两处 `recover_natdown()` 调用需要添加：

**第一处**（定时到期后恢复，约第509行）：
```python
        if time.time() - start_time > times:
            print("超过时间，跳出循环")
            recover_natdown()
            restore_pc_settings_bin()  # <-- 新增

            if _overlay:
                _overlay.destroy()
```

**第二处**（手动恢复，约第530行）：
```python
    else:
        recover_natdown()
        restore_pc_settings_bin()  # <-- 新增

        if _overlay:
            _overlay.destroy()
```

- [ ] **步骤 2：Commit**

```bash
git add ka_085.py
git commit -m "feat: 断网恢复后自动从桌面恢复pc_settings.bin"
```

---

### 验证

完成所有任务后，手动验证：
1. 打开断网设置弹窗，确认"删除pc_settings.bin"和"备份pc_settings.bin"按钮出现在定时控制行右侧
2. 点击备份按钮，确认桌面出现 pc_settings.bin
3. 触发一次断网并恢复，检查控制台是否有恢复日志
4. 确认原位置的 pc_settings.bin 已被桌面备份替换
