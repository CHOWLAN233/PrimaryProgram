#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令行“备忘录”程序（类 macOS 备忘录核心能力）

核心特性：
- 文件夹：新增/重命名/删除/列表
- 笔记：新增/编辑/查看/删除/列表/搜索/置顶（pin/unpin）
- 标签：为笔记设置标签（以统一列表存储）
- 清单：在笔记内维护清单条目（勾选/取消/删除）

数据存储：同目录文件 `便签_data.json`，内含版本与实体列表。
兼容迁移：若检测到旧版“任务”结构，会自动迁移为默认文件夹中的笔记。

示例：
  python 便签 folder list
  python 便签 folder add "工作"
  python 便签 note new 1 "会议记录" --body "明早10点" --tags 会议 日程
  python 便签 note list --folder 1
  python 便签 note pin 2
  python 便签 checklist add 2 "准备PPT"
  python 便签 checklist check 2 1
  python 便签 note search "PPT"
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
import sys
from typing import List, Optional, Dict, Any
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import traceback


DATA_FILE_NAME = "便签_data.json"
DATA_VERSION = 2


@dataclass
class ChecklistItem:
    item_id: int
    text: str
    checked: bool = False


@dataclass
class Note:
    note_id: int
    folder_id: int
    title: str
    body: str
    tags: List[str]
    pinned: bool
    created_at: str
    updated_at: str
    checklist: List[ChecklistItem] = field(default_factory=list)


@dataclass
class Folder:
    folder_id: int
    name: str
    created_at: str


class Store:
    def __init__(self, data_path: Path) -> None:
        self.data_path = data_path
        self.version: int = DATA_VERSION
        self.folders: List[Folder] = []
        self.notes: List[Note] = []
        self._load()

    def _load(self) -> None:
        if not self.data_path.exists():
            # 初始化默认文件夹
            self._init_defaults()
            self._save()
            return
        try:
            raw = json.loads(self.data_path.read_text(encoding="utf-8"))
        except Exception:
            # 若数据损坏，避免崩溃并备份
            backup_path = self.data_path.with_suffix(self.data_path.suffix + ".bak")
            try:
                self.data_path.replace(backup_path)
            except Exception:
                pass
            self._init_defaults()
            self._save()
            return

        # 兼容旧版（纯 tasks 列表）
        if isinstance(raw, list) and (len(raw) == 0 or (isinstance(raw[0], dict) and "task_id" in raw[0])):
            self._init_defaults()
            self._migrate_tasks_to_notes(raw)
            self._save()
            return

        # 新版结构
        if isinstance(raw, dict):
            self.version = int(raw.get("version", 1))
            folders_raw = raw.get("folders", [])
            notes_raw = raw.get("notes", [])

            self.folders = [Folder(**f) for f in folders_raw]
            self.notes = []
            for n in notes_raw:
                checklist_raw = n.get("checklist", [])
                checklist = [ChecklistItem(**c) for c in checklist_raw]
                note_copy = dict(n)
                note_copy["checklist"] = checklist
                self.notes.append(Note(**note_copy))

            # 若版本较旧，可在此追加迁移
            if self.version < DATA_VERSION:
                self.version = DATA_VERSION
                self._save()
            return

        # 无法识别，重置
        self._init_defaults()
        self._save()

    def _save(self) -> None:
        data = {
            "version": self.version,
            "folders": [asdict(f) for f in self.folders],
            "notes": [self._note_to_dict(n) for n in self.notes],
        }
        self.data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _init_defaults(self) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self.version = DATA_VERSION
        self.folders = [Folder(folder_id=1, name="快速备忘录", created_at=now)]
        self.notes = []

    def _migrate_tasks_to_notes(self, raw_tasks: List[Dict[str, Any]]) -> None:
        # 将旧 Task 列表迁移为默认文件夹中的 Note
        now = datetime.now().isoformat(timespec="seconds")
        for t in raw_tasks:
            text = str(t.get("text", "")).strip()
            title = text[:20] or "未命名"
            self.notes.append(
                Note(
                    note_id=self._next_id(self.notes, "note_id"),
                    folder_id=1,
                    title=title,
                    body=text,
                    tags=[],
                    pinned=False,
                    created_at=t.get("created_at", now),
                    updated_at=now,
                    checklist=[],
                )
            )

    @staticmethod
    def _next_id(items: List[Any], field_name: str) -> int:
        max_id = 0
        for it in items:
            max_id = max(max_id, int(getattr(it, field_name)))
        return max_id + 1

    @staticmethod
    def _note_to_dict(note: Note) -> Dict[str, Any]:
        d = asdict(note)
        d["checklist"] = [asdict(c) for c in note.checklist]
        return d

    # ------------- 文件夹 -------------
    def folder_list(self) -> List[Folder]:
        return list(self.folders)

    def folder_add(self, name: str) -> Folder:
        now = datetime.now().isoformat(timespec="seconds")
        folder = Folder(folder_id=self._next_id(self.folders, "folder_id"), name=name.strip(), created_at=now)
        self.folders.append(folder)
        self._save()
        return folder

    def folder_rename(self, folder_id: int, new_name: str) -> Folder:
        for f in self.folders:
            if f.folder_id == folder_id:
                f.name = new_name.strip()
                self._save()
                return f
        raise ValueError(f"未找到文件夹ID {folder_id}")

    def folder_delete(self, folder_id: int) -> None:
        if folder_id == 1:
            raise ValueError("默认文件夹不可删除")
        self.notes = [n for n in self.notes if n.folder_id != folder_id]
        before = len(self.folders)
        self.folders = [f for f in self.folders if f.folder_id != folder_id]
        if len(self.folders) == before:
            raise ValueError(f"未找到文件夹ID {folder_id}")
        self._save()

    # ------------- 笔记 -------------
    def note_new(self, folder_id: int, title: str, body: str, tags: List[str]) -> Note:
        if not any(f.folder_id == folder_id for f in self.folders):
            raise ValueError(f"文件夹不存在: {folder_id}")
        now = datetime.now().isoformat(timespec="seconds")
        note = Note(
            note_id=self._next_id(self.notes, "note_id"),
            folder_id=folder_id,
            title=title.strip() or "未命名",
            body=body,
            tags=[t.strip() for t in tags if t.strip()],
            pinned=False,
            created_at=now,
            updated_at=now,
            checklist=[],
        )
        self.notes.append(note)
        self._save()
        return note

    def note_edit(
        self,
        note_id: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        folder_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> Note:
        for n in self.notes:
            if n.note_id == note_id:
                if title is not None:
                    n.title = title.strip() or n.title
                if body is not None:
                    n.body = body
                if folder_id is not None:
                    if not any(f.folder_id == folder_id for f in self.folders):
                        raise ValueError(f"文件夹不存在: {folder_id}")
                    n.folder_id = folder_id
                if tags is not None:
                    n.tags = [t.strip() for t in tags if t.strip()]
                n.updated_at = datetime.now().isoformat(timespec="seconds")
                self._save()
                return n
        raise ValueError(f"未找到笔记ID {note_id}")

    def note_delete(self, note_id: int) -> None:
        before = len(self.notes)
        self.notes = [n for n in self.notes if n.note_id != note_id]
        if len(self.notes) == before:
            raise ValueError(f"未找到笔记ID {note_id}")
        self._save()

    def note_view(self, note_id: int) -> Note:
        for n in self.notes:
            if n.note_id == note_id:
                return n
        raise ValueError(f"未找到笔记ID {note_id}")

    def note_pin(self, note_id: int, pinned: bool) -> Note:
        for n in self.notes:
            if n.note_id == note_id:
                n.pinned = pinned
                n.updated_at = datetime.now().isoformat(timespec="seconds")
                self._save()
                return n
        raise ValueError(f"未找到笔记ID {note_id}")

    def note_list(
        self,
        folder_id: Optional[int] = None,
        only_pinned: bool = False,
        tag: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Note]:
        notes = list(self.notes)
        if folder_id is not None:
            notes = [n for n in notes if n.folder_id == folder_id]
        if only_pinned:
            notes = [n for n in notes if n.pinned]
        if tag is not None:
            notes = [n for n in notes if tag in n.tags]
        if query:
            q = query.lower()
            notes = [n for n in notes if q in n.title.lower() or q in n.body.lower()]
        # 置顶优先，其次更新时间倒序
        notes.sort(key=lambda n: (not n.pinned, n.updated_at), reverse=True)
        return notes

    # ------------- 清单 -------------
    def checklist_add(self, note_id: int, text: str) -> ChecklistItem:
        note = self.note_view(note_id)
        item = ChecklistItem(item_id=self._next_id(note.checklist, "item_id"), text=text.strip(), checked=False)
        note.checklist.append(item)
        note.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return item

    def checklist_set(self, note_id: int, item_id: int, checked: bool) -> ChecklistItem:
        note = self.note_view(note_id)
        for it in note.checklist:
            if it.item_id == item_id:
                it.checked = checked
                note.updated_at = datetime.now().isoformat(timespec="seconds")
                self._save()
                return it
        raise ValueError("清单项不存在")

    def checklist_remove(self, note_id: int, item_id: int) -> None:
        note = self.note_view(note_id)
        before = len(note.checklist)
        note.checklist = [it for it in note.checklist if it.item_id != item_id]
        if len(note.checklist) == before:
            raise ValueError("清单项不存在")
        note.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()

    # 旧版 Task 相关遗留接口已移除


def print_overview(store: 'Store') -> None:
    print("文件夹：")
    for f in store.folder_list():
        count = len([n for n in store.notes if n.folder_id == f.folder_id])
        print(f"  [{f.folder_id}] {f.name} ({count})")
    print("\n最近笔记：")
    for n in store.note_list()[:10]:
        pin = "📌 " if n.pinned else ""
        tags = (" #" + " #".join(n.tags)) if n.tags else ""
        print(f"  [{n.note_id}] {pin}{n.title}{tags}  (更新:{n.updated_at})")


def install_exception_logging(log_path: Path) -> None:
    def _hook(exc_type, exc, tb):
        try:
            text = "\n".join(
                [
                    datetime.now().isoformat(timespec="seconds"),
                    "Unhandled exception:",
                    "".join(traceback.format_exception(exc_type, exc, tb)),
                    "-" * 60,
                ]
            )
            log_path.write_text(text, encoding="utf-8")
        except Exception:
            pass
        try:
            messagebox.showerror("错误", f"程序发生错误，详情见日志:\n{log_path}")
        except Exception:
            pass
    sys.excepthook = _hook

def launch_gui(store: 'Store') -> None:
    # Tkinter GUI：左侧文件夹，中间笔记列表，右侧笔记详情与清单
    root = tk.Tk()
    root.title("Memo 备忘录")
    root.geometry("1000x640")
    try:
        root.iconbitmap(default='')
    except Exception:
        pass

    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    elif "clam" in style.theme_names():
        style.theme_use("clam")

    # Layout
    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=2)
    root.columnconfigure(2, weight=3)
    root.rowconfigure(0, weight=1)

    # 左：文件夹
    frame_folders = ttk.Frame(root, padding=8)
    frame_folders.grid(row=0, column=0, sticky="nsew")
    ttk.Label(frame_folders, text="文件夹", font=(None, 11, 'bold')).pack(anchor="w")
    folders_wrap = ttk.Frame(frame_folders)
    folders_wrap.pack(fill="both", expand=True, pady=(6, 4))
    folders_scroll = ttk.Scrollbar(folders_wrap, orient="vertical")
    folders_list = tk.Listbox(folders_wrap, exportselection=False, yscrollcommand=folders_scroll.set)
    folders_scroll.config(command=folders_list.yview)
    folders_list.pack(side="left", fill="both", expand=True)
    folders_scroll.pack(side="right", fill="y")
    btn_folder_add = ttk.Button(frame_folders, text="新增文件夹")
    btn_folder_add.pack(fill="x")
    btn_folder_rename = ttk.Button(frame_folders, text="重命名文件夹")
    btn_folder_rename.pack(fill="x", pady=(4, 0))
    btn_folder_delete = ttk.Button(frame_folders, text="删除文件夹")
    btn_folder_delete.pack(fill="x", pady=(4, 0))

    # 中：笔记列表与搜索
    frame_notes = ttk.Frame(root, padding=8)
    frame_notes.grid(row=0, column=1, sticky="nsew")
    frame_notes.rowconfigure(2, weight=1)
    ttk.Label(frame_notes, text="笔记", font=(None, 11, 'bold')).grid(row=0, column=0, sticky="w")
    search_var = tk.StringVar()
    entry_search = ttk.Entry(frame_notes, textvariable=search_var)
    entry_search.grid(row=1, column=0, sticky="ew", pady=4)
    notes_tree = ttk.Treeview(frame_notes, columns=("title", "updated"), show="headings")
    notes_tree.heading("title", text="标题")
    notes_tree.heading("updated", text="更新时间")
    notes_tree.column("title", width=240, anchor="w")
    notes_tree.column("updated", width=140, anchor="center")
    notes_scroll = ttk.Scrollbar(frame_notes, orient="vertical", command=notes_tree.yview)
    notes_tree.configure(yscrollcommand=notes_scroll.set)
    notes_tree.grid(row=2, column=0, sticky="nsew")
    notes_scroll.grid(row=2, column=1, sticky="ns")
    frame_notes.columnconfigure(0, weight=1)
    btn_note_new = ttk.Button(frame_notes, text="新建笔记")
    btn_note_new.grid(row=3, column=0, sticky="ew", pady=(6, 0))

    # 右：详情区（标题、标签、正文、清单）
    frame_detail = ttk.Frame(root, padding=8)
    frame_detail.grid(row=0, column=2, sticky="nsew")
    # 让正文和清单随窗体伸缩
    frame_detail.rowconfigure(3, weight=2)
    frame_detail.rowconfigure(5, weight=3)
    frame_detail.columnconfigure(1, weight=1)
    frame_detail.columnconfigure(2, weight=1)
    ttk.Label(frame_detail, text="详情", font=(None, 11, 'bold')).grid(row=0, column=0, columnspan=3, sticky="w")
    ttk.Label(frame_detail, text="标题").grid(row=1, column=0, sticky="w")
    title_var = tk.StringVar()
    entry_title = ttk.Entry(frame_detail, textvariable=title_var)
    entry_title.grid(row=1, column=1, columnspan=2, sticky="ew")
    ttk.Label(frame_detail, text="标签(空格分隔)").grid(row=2, column=0, sticky="w")
    tags_var = tk.StringVar()
    entry_tags = ttk.Entry(frame_detail, textvariable=tags_var)
    entry_tags.grid(row=2, column=1, columnspan=2, sticky="ew")
    ttk.Label(frame_detail, text="正文").grid(row=3, column=0, sticky="nw")
    body_frame = ttk.Frame(frame_detail)
    body_frame.grid(row=3, column=1, columnspan=2, sticky="nsew")
    body_frame.rowconfigure(0, weight=1)
    body_frame.columnconfigure(0, weight=1)
    text_body = tk.Text(body_frame, height=12, wrap="word")
    body_scroll = ttk.Scrollbar(body_frame, orient="vertical", command=text_body.yview)
    text_body.configure(yscrollcommand=body_scroll.set)
    text_body.grid(row=0, column=0, sticky="nsew")
    body_scroll.grid(row=0, column=1, sticky="ns")
    btn_save = ttk.Button(frame_detail, text="保存")
    btn_save.grid(row=4, column=2, sticky="e", pady=6)
    btn_delete_note = ttk.Button(frame_detail, text="删除笔记")
    btn_delete_note.grid(row=4, column=1, sticky="w", pady=6)

    ttk.Label(frame_detail, text="清单").grid(row=5, column=0, sticky="nw", pady=(6, 0))
    checklist_frame = ttk.Frame(frame_detail)
    checklist_frame.grid(row=5, column=1, columnspan=2, sticky="nsew", pady=(6, 0))
    checklist_frame.rowconfigure(0, weight=1)
    checklist_frame.columnconfigure(0, weight=1)
    # 可滚动清单容器
    checklist_canvas = tk.Canvas(checklist_frame, highlightthickness=0)
    checklist_scroll = ttk.Scrollbar(checklist_frame, orient="vertical", command=checklist_canvas.yview)
    checklist_canvas.configure(yscrollcommand=checklist_scroll.set)
    checklist_canvas.grid(row=0, column=0, sticky="nsew")
    checklist_scroll.grid(row=0, column=1, sticky="ns")
    checklist_items_container = ttk.Frame(checklist_canvas)
    checklist_window = checklist_canvas.create_window((0, 0), window=checklist_items_container, anchor="nw")
    def _on_checklist_configure(event=None):
        checklist_canvas.configure(scrollregion=checklist_canvas.bbox("all"))
        checklist_canvas.itemconfigure(checklist_window, width=checklist_canvas.winfo_width())
    checklist_items_container.bind("<Configure>", _on_checklist_configure)
    add_item_var = tk.StringVar()
    entry_item = ttk.Entry(checklist_frame, textvariable=add_item_var)
    entry_item.pack(fill="x", pady=(6, 4))
    btn_item_add = ttk.Button(checklist_frame, text="添加清单项")
    btn_item_add.grid(row=1, column=0, columnspan=2, sticky="e", pady=(6, 0))

    # 状态
    current_folder_id: Optional[int] = None
    current_note_id: Optional[int] = None

    def refresh_folders() -> None:
        folders_list.delete(0, tk.END)
        for f in store.folder_list():
            count = len([n for n in store.notes if n.folder_id == f.folder_id])
            folders_list.insert(tk.END, f"[{f.folder_id}] {f.name} ({count})")

    def refresh_notes() -> None:
        notes_tree.delete(*notes_tree.get_children())
        query = search_var.get().strip() or None
        notes = store.note_list(folder_id=current_folder_id, query=query)
        for n in notes:
            pin = "📌 " if n.pinned else ""
            notes_tree.insert("", tk.END, iid=str(n.note_id), values=(pin + n.title, n.updated_at))

    def refresh_detail(note_id: int) -> None:
        nonlocal current_note_id
        try:
            n = store.note_view(note_id)
        except Exception:
            return
        current_note_id = note_id
        title_var.set(n.title)
        tags_var.set(" ".join(n.tags))
        text_body.delete("1.0", tk.END)
        text_body.insert("1.0", n.body)
        # checklist
        for w in checklist_items_container.winfo_children():
            w.destroy()
        for it in n.checklist:
            row = ttk.Frame(checklist_items_container)
            row.pack(fill="x", pady=2)
            var = tk.BooleanVar(value=it.checked)
            cb = ttk.Checkbutton(row, text=f"({it.item_id}) {it.text}", variable=var)
            cb.var = var  # attach
            cb.item_id = it.item_id  # type: ignore[attr-defined]
            cb.pack(side="left", anchor="w")
            def _make_remove(item_id: int):
                def _remove():
                    if current_note_id is None:
                        return
                    try:
                        store.checklist_remove(current_note_id, item_id)
                        refresh_detail(current_note_id)
                        refresh_notes()
                    except Exception as e:
                        messagebox.showerror("错误", str(e))
                return _remove
            btn_rm = ttk.Button(row, text="删除", width=6, command=_make_remove(it.item_id))
            btn_rm.pack(side="right")

        def on_check_toggle():
            if current_note_id is None:
                return
            try:
                for w in checklist_items_container.winfo_children():
                    if isinstance(w, ttk.Checkbutton) and hasattr(w, 'item_id'):
                        store.checklist_set(current_note_id, getattr(w, 'item_id'), bool(getattr(w, 'var').get()))
                refresh_notes()
            except Exception as e:
                messagebox.showerror("错误", str(e))

        # 绑定每次点击后保存状态
        for w in checklist_items_container.winfo_children():
            if isinstance(w, ttk.Checkbutton):
                w.configure(command=on_check_toggle)

    def on_folder_select(event=None):
        nonlocal current_folder_id
        sel = folders_list.curselection()
        if not sel:
            current_folder_id = None
        else:
            # 通过显示文本解析 ID
            text = folders_list.get(sel[0])
            try:
                fid = int(text.split(']')[0].split('[')[1])
                current_folder_id = fid
            except Exception:
                current_folder_id = None
        refresh_notes()

    def on_note_select(event=None):
        sel = notes_tree.selection()
        if not sel:
            return
        note_id = int(sel[0])
        refresh_detail(note_id)

    def on_search_change(*_):
        refresh_notes()

    def create_folder():
        name = simpledialog.askstring("新增文件夹", "输入文件夹名称：", parent=root)
        if not name:
            return
        try:
            f = store.folder_add(name)
            refresh_folders()
            # 选中新建
            for idx in range(folders_list.size()):
                if folders_list.get(idx).startswith(f"[{f.folder_id}]"):
                    folders_list.selection_clear(0, tk.END)
                    folders_list.selection_set(idx)
                    on_folder_select()
                    break
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def rename_folder():
        if current_folder_id is None:
            messagebox.showinfo("提示", "请先选择一个文件夹")
            return
        new_name = simpledialog.askstring("重命名文件夹", "新的名称：", parent=root)
        if not new_name:
            return
        try:
            store.folder_rename(current_folder_id, new_name)
            refresh_folders()
            # 保持当前选中
            for idx in range(folders_list.size()):
                if folders_list.get(idx).startswith(f"[{current_folder_id}]"):
                    folders_list.selection_clear(0, tk.END)
                    folders_list.selection_set(idx)
                    break
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def delete_folder():
        nonlocal current_folder_id
        if current_folder_id is None:
            messagebox.showinfo("提示", "请先选择一个文件夹")
            return
        if not messagebox.askyesno("确认", "确定删除该文件夹及其所有笔记？此操作不可恢复"):
            return
        try:
            store.folder_delete(current_folder_id)
            current_folder_id = None
            refresh_folders()
            folders_list.selection_clear(0, tk.END)
            if folders_list.size() > 0:
                folders_list.selection_set(0)
                on_folder_select()
            else:
                notes_tree.delete(*notes_tree.get_children())
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def create_note():
        if current_folder_id is None:
            messagebox.showinfo("提示", "请先选择一个文件夹")
            return
        title = simpledialog.askstring("新建笔记", "标题：", parent=root) or "未命名"
        try:
            n = store.note_new(current_folder_id, title, "", [])
            refresh_notes()
            notes_tree.selection_set(str(n.note_id))
            refresh_detail(n.note_id)
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def save_note():
        if current_note_id is None:
            return
        try:
            title = title_var.get().strip()
            body = text_body.get("1.0", tk.END).rstrip()
            tags = [t for t in tags_var.get().split(" ") if t.strip()]
            store.note_edit(current_note_id, title=title, body=body, tags=tags)
            refresh_notes()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def add_check_item():
        if current_note_id is None:
            return
        text = add_item_var.get().strip()
        if not text:
            return
        try:
            store.checklist_add(current_note_id, text)
            add_item_var.set("")
            refresh_detail(current_note_id)
            refresh_notes()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def delete_note():
        nonlocal current_note_id
        if current_note_id is None:
            return
        if not messagebox.askyesno("确认", "确定删除当前笔记？此操作不可恢复"):
            return
        try:
            store.note_delete(current_note_id)
            current_note_id = None
            # 清空详情
            title_var.set("")
            tags_var.set("")
            text_body.delete("1.0", tk.END)
            for w in checklist_items_container.winfo_children():
                w.destroy()
            refresh_notes()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    folders_list.bind("<<ListboxSelect>>", on_folder_select)
    notes_tree.bind("<<TreeviewSelect>>", on_note_select)
    search_var.trace_add('write', on_search_change)
    btn_folder_add.configure(command=create_folder)
    btn_folder_rename.configure(command=rename_folder)
    btn_folder_delete.configure(command=delete_folder)
    btn_note_new.configure(command=create_note)
    btn_save.configure(command=save_note)
    btn_delete_note.configure(command=delete_note)
    btn_item_add.configure(command=add_check_item)

    # 快捷键：Ctrl+S 保存
    root.bind_all('<Control-s>', lambda e: save_note())

    # 初始化
    refresh_folders()
    if folders_list.size() > 0:
        folders_list.selection_set(0)
        on_folder_select()

    root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="命令行备忘录：文件夹/笔记/清单/标签/搜索/置顶")
    sub = parser.add_subparsers(dest="command")

    # folder
    p_folder = sub.add_parser("folder", help="文件夹相关命令")
    sub_folder = p_folder.add_subparsers(dest="action")
    sub_folder.add_parser("list", help="列出文件夹")
    p_folder_add = sub_folder.add_parser("add", help="新增文件夹")
    p_folder_add.add_argument("name", type=str)
    p_folder_rename = sub_folder.add_parser("rename", help="重命名文件夹")
    p_folder_rename.add_argument("id", type=int)
    p_folder_rename.add_argument("name", type=str)
    p_folder_del = sub_folder.add_parser("delete", help="删除文件夹")
    p_folder_del.add_argument("id", type=int)

    # note
    p_note = sub.add_parser("note", help="笔记相关命令")
    sub_note = p_note.add_subparsers(dest="action")
    p_note_new = sub_note.add_parser("new", help="新增笔记")
    p_note_new.add_argument("folder", type=int, help="文件夹ID")
    p_note_new.add_argument("title", type=str)
    p_note_new.add_argument("--body", type=str, default="")
    p_note_new.add_argument("--tags", nargs='*', default=[])

    p_note_edit = sub_note.add_parser("edit", help="编辑笔记")
    p_note_edit.add_argument("id", type=int)
    p_note_edit.add_argument("--title", type=str)
    p_note_edit.add_argument("--body", type=str)
    p_note_edit.add_argument("--folder", type=int)
    p_note_edit.add_argument("--set-tags", nargs='*')

    p_note_view = sub_note.add_parser("view", help="查看笔记")
    p_note_view.add_argument("id", type=int)

    p_note_del = sub_note.add_parser("delete", help="删除笔记")
    p_note_del.add_argument("id", type=int)

    p_note_list = sub_note.add_parser("list", help="列出笔记")
    p_note_list.add_argument("--folder", type=int)
    p_note_list.add_argument("--pinned", action="store_true")
    p_note_list.add_argument("--tag", type=str)
    p_note_list.add_argument("--search", type=str)

    p_note_pin = sub_note.add_parser("pin", help="置顶笔记")
    p_note_pin.add_argument("id", type=int)
    p_note_unpin = sub_note.add_parser("unpin", help="取消置顶")
    p_note_unpin.add_argument("id", type=int)

    # checklist
    p_check = sub.add_parser("checklist", help="清单相关命令")
    sub_check = p_check.add_subparsers(dest="action")
    p_check_add = sub_check.add_parser("add", help="新增清单项")
    p_check_add.add_argument("note", type=int)
    p_check_add.add_argument("text", type=str)
    p_check_check = sub_check.add_parser("check", help="勾选清单项")
    p_check_check.add_argument("note", type=int)
    p_check_check.add_argument("item", type=int)
    p_check_uncheck = sub_check.add_parser("uncheck", help="取消勾选")
    p_check_uncheck.add_argument("note", type=int)
    p_check_uncheck.add_argument("item", type=int)
    p_check_rm = sub_check.add_parser("remove", help="删除清单项")
    p_check_rm.add_argument("note", type=int)
    p_check_rm.add_argument("item", type=int)

    # gui
    p_gui = sub.add_parser("gui", help="启动图形界面")

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # 兼容 PyInstaller 冻结环境的数据文件路径
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent
    data_path = base_dir / DATA_FILE_NAME
    # 安装全局异常记录（双击无控制台时可定位问题）
    install_exception_logging(base_dir / "memo_error.log")
    store = Store(data_path)

    # 若为打包后的 exe，且未提供任何子命令，默认启动 GUI，
    # 以避免无控制台(-w)双击时看起来无响应
    if getattr(sys, "frozen", False) and args.command is None:
        launch_gui(store)
        return

    # GUI 启动
    if args.command == "gui":
        launch_gui(store)
        return

    # 命令：folder
    if args.command == "folder":
        if args.action == "list":
            for f in store.folder_list():
                count = len([n for n in store.notes if n.folder_id == f.folder_id])
                print(f"[{f.folder_id}] {f.name} ({count})")
            return
        if args.action == "add":
            f = store.folder_add(args.name)
            print(f"已新增文件夹 [{f.folder_id}]: {f.name}")
            return
        if args.action == "rename":
            try:
                f = store.folder_rename(args.id, args.name)
                print(f"已重命名文件夹 [{f.folder_id}] -> {f.name}")
            except ValueError as e:
                print(str(e))
            return
        if args.action == "delete":
            try:
                store.folder_delete(args.id)
                print("已删除文件夹")
            except ValueError as e:
                print(str(e))
            return

    # 命令：note
    if args.command == "note":
        if args.action == "new":
            try:
                n = store.note_new(args.folder, args.title, args.body, args.tags)
                print(f"已新增笔记 [{n.note_id}] 于文件夹 {n.folder_id}")
            except ValueError as e:
                print(str(e))
            return
        if args.action == "edit":
            try:
                n = store.note_edit(
                    args.id,
                    title=args.title,
                    body=args.body,
                    folder_id=args.folder,
                    tags=args.set_tags,
                )
                print(f"已更新笔记 [{n.note_id}]")
            except ValueError as e:
                print(str(e))
            return
        if args.action == "view":
            try:
                n = store.note_view(args.id)
                pin = "📌 " if n.pinned else ""
                print(f"[{n.note_id}] {pin}{n.title}")
                if n.tags:
                    print("标签:", " ".join(f"#{t}" for t in n.tags))
                print("文件夹:", n.folder_id)
                print("创建:", n.created_at, " 更新:", n.updated_at)
                if n.checklist:
                    print("清单:")
                    for it in n.checklist:
                        mark = "[x]" if it.checked else "[ ]"
                        print(f"  ({it.item_id}) {mark} {it.text}")
                if n.body:
                    print("\n正文:")
                    print(n.body)
            except ValueError as e:
                print(str(e))
            return
        if args.action == "delete":
            try:
                store.note_delete(args.id)
                print("已删除笔记")
            except ValueError as e:
                print(str(e))
            return
        if args.action == "list":
            notes = store.note_list(folder_id=args.folder, only_pinned=args.pinned, tag=args.tag, query=args.search)
            for n in notes:
                pin = "📌 " if n.pinned else ""
                tags = (" #" + " #".join(n.tags)) if n.tags else ""
                print(f"[{n.note_id}] {pin}{n.title}{tags} (文件夹:{n.folder_id} 更新:{n.updated_at})")
            return
        if args.action == "pin":
            try:
                n = store.note_pin(args.id, True)
                print(f"已置顶 [{n.note_id}] {n.title}")
            except ValueError as e:
                print(str(e))
            return
        if args.action == "unpin":
            try:
                n = store.note_pin(args.id, False)
                print(f"已取消置顶 [{n.note_id}] {n.title}")
            except ValueError as e:
                print(str(e))
            return

    # 命令：checklist
    if args.command == "checklist":
        if args.action == "add":
            try:
                it = store.checklist_add(args.note, args.text)
                print(f"已添加清单项 ({it.item_id})")
            except ValueError as e:
                print(str(e))
            return
        if args.action == "check":
            try:
                it = store.checklist_set(args.note, args.item, True)
                print(f"已勾选清单项 ({it.item_id})")
            except ValueError as e:
                print(str(e))
            return
        if args.action == "uncheck":
            try:
                it = store.checklist_set(args.note, args.item, False)
                print(f"已取消勾选清单项 ({it.item_id})")
            except ValueError as e:
                print(str(e))
            return
        if args.action == "remove":
            try:
                store.checklist_remove(args.note, args.item)
                print("已删除清单项")
            except ValueError as e:
                print(str(e))
            return

    # 默认：显示概览
    print_overview(store)


if __name__ == "__main__":
    main()


