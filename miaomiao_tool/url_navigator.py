import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import json
import os
import sys
from PIL import Image, ImageTk, ImageDraw

# PyInstaller资源路径兼容
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 厦大马来西亚分校主色
XMUMBlue = '#003366'
XMUMGold = '#FFD700'
BGColor = '#F5F7FA'
FONT = ('PingFang SC', 12)
TITLE_FONT = ('PingFang SC', 18, 'bold')

class URLNavigator:
    def __init__(self, root):
        self.root = root
        self.root.title("厦门大学马来西亚分校网址导航")
        self.root.geometry("900x670")
        self.root.configure(bg=BGColor)
        
        # 顶部厦门大学马来西亚分校字样和校徽，三列布局
        top_frame = tk.Frame(self.root, bg=BGColor)
        top_frame.pack(fill=tk.X, pady=(18, 0))
        top_frame.columnconfigure(0, minsize=100)
        top_frame.columnconfigure(1, weight=1)
        top_frame.columnconfigure(2, weight=2)
        # 校徽图片（如有）
        logo_path = resource_path('xmum_logo.png')
        if os.path.exists(logo_path):
            logo_img = self.process_logo(logo_path, size=100)
            logo_label = tk.Label(top_frame, image=logo_img, bg=BGColor)
            logo_label.image = logo_img  # 防止被垃圾回收
            logo_label.grid(row=0, column=0, padx=(20, 10), sticky='w')
        else:
            tk.Label(top_frame, text="XMUM", font=("Arial", 20, "bold"), fg=XMUMBlue, bg=BGColor).grid(row=0, column=0, padx=(20, 10), sticky='w')
        # 标题
        tk.Label(top_frame, text="厦门大学马来西亚分校网址导航", font=TITLE_FONT, fg=XMUMBlue, bg=BGColor).grid(row=0, column=1, sticky='ew', pady=(0, 20))
        # 校训
        tk.Label(top_frame, text="自强不息，止于至善 | Pursue Excellence; Strive for Perfection", font=('PingFang SC', 12, 'italic'), fg=XMUMBlue, bg=BGColor, anchor='e').grid(row=0, column=2, sticky='e', padx=20, pady=(0, 20))
        
        # 主框架
        self.main_frame = tk.Frame(self.root, bg=BGColor)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 按钮区
        btn_frame = tk.Frame(self.main_frame, bg=BGColor)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('XMUM.TButton', font=FONT, background=XMUMBlue, foreground='white', borderwidth=0, focusthickness=3, focuscolor=XMUMGold)
        style.map('XMUM.TButton', background=[('active', XMUMGold)])
        ttk.Button(btn_frame, text="添加网址", style='XMUM.TButton', command=self.open_add_window).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除选中网址", style='XMUM.TButton', command=self.delete_selected_site).pack(side=tk.LEFT, padx=5)
        
        # 网址列表区
        self.create_site_list()
        self.load_sites()
        if not self.tree.get_children():
            self.add_default_sites()

    def process_logo(self, path, size=60):
        # 打开图片并缩放
        img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
        # 创建圆形遮罩
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        # 应用遮罩
        img = Image.composite(img, Image.new('RGBA', (size, size), (255,255,255,0)), mask)
        # 加白色边框
        border_size = 4
        bordered = Image.new('RGBA', (size+border_size*2, size+border_size*2), (255,255,255,0))
        draw = ImageDraw.Draw(bordered)
        draw.ellipse((0, 0, size+border_size*2-1, size+border_size*2-1), fill='white')
        bordered.paste(img, (border_size, border_size), img)
        # 转为Tk图片
        return ImageTk.PhotoImage(bordered)

    def open_add_window(self):
        add_win = tk.Toplevel(self.root)
        add_win.title("添加新网址 - 厦门大学马来西亚分校")
        add_win.geometry("400x220")
        add_win.configure(bg=BGColor)
        add_win.grab_set()
        
        tk.Label(add_win, text="网站名称:", font=FONT, bg=BGColor, fg=XMUMBlue).grid(row=0, column=0, sticky=tk.W, padx=18, pady=10)
        name_var = tk.StringVar()
        tk.Entry(add_win, textvariable=name_var, font=FONT).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        tk.Label(add_win, text="网站地址:", font=FONT, bg=BGColor, fg=XMUMBlue).grid(row=1, column=0, sticky=tk.W, padx=18, pady=10)
        url_var = tk.StringVar()
        tk.Entry(add_win, textvariable=url_var, font=FONT).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        tk.Label(add_win, text="网站描述:", font=FONT, bg=BGColor, fg=XMUMBlue).grid(row=2, column=0, sticky=tk.W, padx=18, pady=10)
        desc_var = tk.StringVar()
        tk.Entry(add_win, textvariable=desc_var, font=FONT).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        def add_site_and_close():
            name = name_var.get().strip()
            url = url_var.get().strip()
            desc = desc_var.get().strip()
            if not name or not url:
                messagebox.showwarning("警告", "请填写网站名称和地址！")
                return
            self.tree.insert("", tk.END, values=(name, url, desc))
            self.save_sites()
            add_win.destroy()
        style = ttk.Style()
        style.configure('XMUMAdd.TButton', font=FONT, background=XMUMBlue, foreground='white')
        ttk.Button(add_win, text="添加", style='XMUMAdd.TButton', command=add_site_and_close).grid(row=3, column=1, sticky=tk.E, padx=10, pady=10)
        add_win.columnconfigure(1, weight=1)

    def create_site_list(self):
        style = ttk.Style()
        style.configure('XMUM.Treeview.Heading', font=('PingFang SC', 13, 'bold'), background=XMUMBlue, foreground='white')
        style.configure('XMUM.Treeview', font=FONT, rowheight=28, background='white', fieldbackground='white')
        self.list_frame = ttk.LabelFrame(self.main_frame, text="网址列表", padding="5", style='XMUM.TLabelframe')
        self.list_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(self.list_frame, columns=("name", "url", "desc"), show="headings", style='XMUM.Treeview')
        self.tree.heading("name", text="网站名称", anchor=tk.W)
        self.tree.heading("url", text="网站地址", anchor=tk.W)
        self.tree.heading("desc", text="网站描述", anchor=tk.W)
        self.tree.column("name", width=150, anchor=tk.W)
        self.tree.column("url", width=300, anchor=tk.W)
        self.tree.column("desc", width=300, anchor=tk.W)
        scrollbar = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Double-1>", self.open_url)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="删除", command=self.delete_site)

    def delete_selected_site(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选中要删除的网址！")
            return
        for item in selected_items:
            self.tree.delete(item)
        self.save_sites()

    def open_url(self, event):
        item = self.tree.selection()[0]
        url = self.tree.item(item)["values"][1]
        webbrowser.open(url)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def delete_site(self):
        selected_item = self.tree.selection()[0]
        self.tree.delete(selected_item)
        self.save_sites()

    def save_sites(self):
        sites = []
        for item in self.tree.get_children():
            values = self.tree.item(item)["values"]
            sites.append({
                "name": values[0],
                "url": values[1],
                "desc": values[2]
            })
        # 用PyInstaller兼容路径保存
        json_path = resource_path('sites.json')
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(sites, f, ensure_ascii=False, indent=2)

    def load_sites(self):
        json_path = resource_path('sites.json')
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                sites = json.load(f)
                for site in sites:
                    self.tree.insert("", tk.END, values=(site["name"], site["url"], site["desc"]))

    def add_default_sites(self):
        default_sites = [
            ("Google", "https://www.google.com", "全球最大的搜索引擎"),
            ("GitHub", "https://www.github.com", "全球最大的代码托管平台"),
            ("知乎", "https://www.zhihu.com", "中文互联网高质量的问答社区"),
            ("哔哩哔哩", "https://www.bilibili.com", "国内知名的视频弹幕网站"),
            ("淘宝", "https://www.taobao.com", "中国最大的网上购物平台"),
            ("京东", "https://www.jd.com", "中国领先的电子商务平台")
        ]
        for name, url, desc in default_sites:
            self.tree.insert("", tk.END, values=(name, url, desc))
        self.save_sites()

if __name__ == "__main__":
    root = tk.Tk()
    app = URLNavigator(root)
    # 底部加欢迎语
    footer = tk.Label(root, text="Welcome to the beautiful XMUM campus! | Xiamen University Malaysia", font=('PingFang SC', 11), fg=XMUMBlue, bg=BGColor)
    footer.pack(side=tk.BOTTOM, pady=8)
    root.mainloop() 