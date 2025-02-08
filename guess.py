import os
import tkinter as tk
from tkinter import ttk, messagebox
from pypinyin import pinyin, Style

def get_pronunciations(ch):
    """
    返回一个汉字所有可能的拼音拆分结果，每个结果为字典：
    {"initial": 声母, "final": 韵母, "tone": 声调}
    例如：'毛'可能返回 [{"initial": "m", "final": "ao", "tone": "2"}, ...]
    """
    py_list = pinyin(ch, style=Style.TONE3, heteronym=True)[0]
    results = []
    # 声母列表，注意多音节声母优先匹配
    initials_list = ['zh', 'ch', 'sh', 'b', 'p', 'm', 'f', 'd', 't', 'n', 'l',
                     'g', 'k', 'h', 'j', 'q', 'x', 'r', 'z', 'c', 's','y','w']
    for py in set(py_list):
        if not py:
            continue
        if py[-1] in "12345":
            tone = py[-1]
            syllable = py[:-1]
        else:
            tone = ""
            syllable = py
        initial = ""
        for ini in initials_list:
            if syllable.startswith(ini):
                initial = ini
                break
        final = syllable[len(initial):]
        results.append({"initial": initial, "final": final, "tone": tone})
    return results

def word_matches(word, specific_reqs, ambiguous_reqs, exclude_reqs, exact_char_reqs, ambiguous_chars, non_exist_chars):
    """
    检查词语是否满足所有要求：
      - specific_reqs: 指定位置的拼音要求，格式 {0: {"initial": "m", "final": "ao", "tone": "2"}, …}
      - ambiguous_reqs: 模糊的拼音要求（存在但位置不确定），格式 {"initial": set(...), "final": set(...), "tone": set(...)}
      - exclude_reqs: 一定不存在的拼音要求，格式同上
      - exact_char_reqs: 每个位置中确定的汉字，格式 {0: "字", …}
      - ambiguous_chars: 词中必须包含的汉字集合（位置不确定）
      - non_exist_chars: 词中必须不包含的汉字集合
    利用回溯搜索考虑多音字情况。
    """
    n = len(word)
    # 检查每个位置确定的汉字是否匹配
    for i, char in exact_char_reqs.items():
        if word[i] != char:
            return False

    possibilities = []
    for i, ch in enumerate(word):
        poss = get_pronunciations(ch)
        if i in specific_reqs:
            req = specific_reqs[i]
            filtered = []
            for p in poss:
                ok = True
                if req.get("initial") and p["initial"] != req["initial"]:
                    ok = False
                if req.get("final") and p["final"] != req["final"]:
                    ok = False
                if req.get("tone") and p["tone"] != req["tone"]:
                    ok = False
                if ok:
                    filtered.append(p)
            poss = filtered
        if not poss:
            return False
        possibilities.append(poss)

    # 回溯搜索一种组合满足模糊和排除要求
    chosen = [None] * n
    def backtrack(i):
        if i == n:
            initials = set(p["initial"] for p in chosen)
            finals = set(p["final"] for p in chosen)
            tones = set(p["tone"] for p in chosen)
            for param in ambiguous_reqs.get("initial", set()):
                if param not in initials:
                    return False
            for param in ambiguous_reqs.get("final", set()):
                if param not in finals:
                    return False
            for param in ambiguous_reqs.get("tone", set()):
                if param not in tones:
                    return False
            return True
        for p in possibilities[i]:
            if "initial" in exclude_reqs and p["initial"] in exclude_reqs["initial"]:
                continue
            if "final" in exclude_reqs and p["final"] in exclude_reqs["final"]:
                continue
            if "tone" in exclude_reqs and p["tone"] in exclude_reqs["tone"]:
                continue
            chosen[i] = p
            if backtrack(i + 1):
                return True
        return False

    if not backtrack(0):
        return False

    # 检查词中必须包含的汉字
    for char in ambiguous_chars:
        if char not in word:
            return False

    # 检查词中不能包含的汉字
    for char in non_exist_chars:
        if char in word:
            return False

    return True

class GuessGameGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("猜词游戏助手")
        self.geometry("800x600")
        # 词库配置，可根据实际情况调整路径
        self.dict_options = {
            "THUOCL_animal.txt": "动物词库",
            "THUOCL_car.txt": "汽车词库",
            "THUOCL_law.txt": "法律词库",
            "THUOCL_food.txt": "食品词库",
            "THUOCL_medical.txt": "医疗词库",
            "THUOCL_poem.txt": "诗词词库",
            "THUOCL_lishimingren.txt": "历史名人词库",
            "THUOCL_diming.txt": "地名词库",
            "THUOCL_chengyu.txt": "成语词库",
            "THUOCL_it.txt": "IT词库",
            "THUOCL_caijing.txt": "财经词库",
            "wiki.txt": "维基百科"
        }
        self.create_widgets()

    def create_widgets(self):
        # 词库选择区
        vocab_frame = ttk.LabelFrame(self, text="词库选择")
        vocab_frame.pack(fill=tk.X, padx=10, pady=5)
        self.dict_vars = {}
        for file, name in self.dict_options.items():
            var = tk.BooleanVar()
            chk = ttk.Checkbutton(vocab_frame, text=name, variable=var)
            chk.pack(side=tk.LEFT, padx=5, pady=5)
            self.dict_vars[file] = var

        # 词语字数及生成位置输入
        length_frame = ttk.Frame(self)
        length_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(length_frame, text="词语字数：").pack(side=tk.LEFT)
        self.length_entry = ttk.Entry(length_frame, width=5)
        self.length_entry.pack(side=tk.LEFT)
        self.generate_btn = ttk.Button(length_frame, text="生成位置输入", command=self.generate_position_inputs)
        self.generate_btn.pack(side=tk.LEFT, padx=10)

        # 每个字的输入（拼音要求与确定汉字）
        self.position_frame = ttk.LabelFrame(self, text="每个字的要求")
        self.position_frame.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)
        self.position_inputs = []

        # 模糊拼音要求
        ambiguous_frame = ttk.LabelFrame(self, text="模糊拼音要求")
        ambiguous_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(ambiguous_frame, text="存在的声母（逗号分隔）：").grid(row=0, column=0, sticky=tk.W)
        self.amb_initial_entry = ttk.Entry(ambiguous_frame, width=30)
        self.amb_initial_entry.grid(row=0, column=1, sticky=tk.W)
        ttk.Label(ambiguous_frame, text="存在的韵母（逗号分隔）：").grid(row=1, column=0, sticky=tk.W)
        self.amb_final_entry = ttk.Entry(ambiguous_frame, width=30)
        self.amb_final_entry.grid(row=1, column=1, sticky=tk.W)
        ttk.Label(ambiguous_frame, text="存在的声调（逗号分隔）：").grid(row=2, column=0, sticky=tk.W)
        self.amb_tone_entry = ttk.Entry(ambiguous_frame, width=30)
        self.amb_tone_entry.grid(row=2, column=1, sticky=tk.W)

        # 排除拼音要求
        exclude_frame = ttk.LabelFrame(self, text="排除拼音要求")
        exclude_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(exclude_frame, text="不存在的声母（逗号分隔）：").grid(row=0, column=0, sticky=tk.W)
        self.exc_initial_entry = ttk.Entry(exclude_frame, width=30)
        self.exc_initial_entry.grid(row=0, column=1, sticky=tk.W)
        ttk.Label(exclude_frame, text="不存在的韵母（逗号分隔）：").grid(row=1, column=0, sticky=tk.W)
        self.exc_final_entry = ttk.Entry(exclude_frame, width=30)
        self.exc_final_entry.grid(row=1, column=1, sticky=tk.W)
        ttk.Label(exclude_frame, text="不存在的声调（逗号分隔）：").grid(row=2, column=0, sticky=tk.W)
        self.exc_tone_entry = ttk.Entry(exclude_frame, width=30)
        self.exc_tone_entry.grid(row=2, column=1, sticky=tk.W)

        # 汉字要求（存在但位置不确定的汉字及不存在的汉字）
        char_frame = ttk.LabelFrame(self, text="汉字要求")
        char_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(char_frame, text="存在但位置不确定的汉字：").grid(row=0, column=0, sticky=tk.W)
        self.amb_chars_entry = ttk.Entry(char_frame, width=50)
        self.amb_chars_entry.grid(row=0, column=1, sticky=tk.W)
        ttk.Label(char_frame, text="不存在的汉字：").grid(row=1, column=0, sticky=tk.W)
        self.nonexist_chars_entry = ttk.Entry(char_frame, width=50)
        self.nonexist_chars_entry.grid(row=1, column=1, sticky=tk.W)

        # 搜索按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        self.search_btn = ttk.Button(btn_frame, text="搜索符合条件的词语", command=self.search_words)
        self.search_btn.pack(side=tk.LEFT, padx=10)
        # 新增“清除全部”按钮，清除所有输入
        self.reset_btn = ttk.Button(btn_frame, text="清除全部", command=self.reset_all)
        self.reset_btn.pack(side=tk.LEFT, padx=10)

        # 结果显示区域
        result_frame = ttk.LabelFrame(self, text="结果")
        result_frame.pack(fill=tk.BOTH, padx=10, pady=5, expand=True)
        self.result_text = tk.Text(result_frame, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True)

    def generate_position_inputs(self):
        """根据词语字数生成每个字的输入区域"""
        # 清除原有控件
        for child in self.position_frame.winfo_children():
            child.destroy()
        self.position_inputs = []
        try:
            length = int(self.length_entry.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的词语字数")
            return
        # 为每个字创建一行输入，包含声母、韵母、声调和确定汉字
        for i in range(length):
            frame = ttk.Frame(self.position_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"第{i+1}个字 - 声母:").grid(row=0, column=0)
            initial_entry = ttk.Entry(frame, width=5)
            initial_entry.grid(row=0, column=1)
            ttk.Label(frame, text="韵母:").grid(row=0, column=2)
            final_entry = ttk.Entry(frame, width=5)
            final_entry.grid(row=0, column=3)
            ttk.Label(frame, text="声调:").grid(row=0, column=4)
            tone_entry = ttk.Entry(frame, width=5)
            tone_entry.grid(row=0, column=5)
            ttk.Label(frame, text="确定汉字:").grid(row=0, column=6)
            exact_entry = ttk.Entry(frame, width=5)
            exact_entry.grid(row=0, column=7)
            self.position_inputs.append({
                "initial": initial_entry,
                "final": final_entry,
                "tone": tone_entry,
                "exact": exact_entry
            })

    def load_selected_words(self):
        """加载已选词库中的词语，返回列表，每项为 (word, 词库名称)"""
        selected_files = [file for file, var in self.dict_vars.items() if var.get()]
        if not selected_files:
            messagebox.showerror("错误", "请至少选择一个词库")
            return []
        words = []
        for filename in selected_files:
            if not os.path.exists(filename):
                continue
            with open(filename, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    word = parts[0]
                    words.append((word, self.dict_options[filename]))
        return words

    def search_words(self):
        """根据所有条件筛选符合条件的词语并显示"""
        words = self.load_selected_words()
        if not words:
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, "没有加载到词语。")
            return
        try:
            length = int(self.length_entry.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的词语字数")
            return
        # 筛选出指定字数的词语
        words = [(w, t) for w, t in words if len(w) == length]

        # 每个位置的拼音要求和确定汉字（由生成的位置输入中获取）
        specific_reqs = {}
        exact_char_reqs = {}
        for i, inputs in enumerate(self.position_inputs):
            initial = inputs["initial"].get().strip().lower()
            final = inputs["final"].get().strip().lower()
            tone = inputs["tone"].get().strip()
            if initial or final or tone:
                req = {}
                if initial:
                    req["initial"] = initial
                if final:
                    req["final"] = final
                if tone:
                    req["tone"] = tone
                specific_reqs[i] = req
            exact = inputs["exact"].get().strip()
            if exact:
                exact_char_reqs[i] = exact[0]
        # 模糊拼音要求
        amb_initial = self.amb_initial_entry.get().strip().lower()
        amb_final = self.amb_final_entry.get().strip().lower()
        amb_tone = self.amb_tone_entry.get().strip()
        ambiguous_reqs = {"initial": set(), "final": set(), "tone": set()}
        if amb_initial:
            ambiguous_reqs["initial"] = set(x.strip() for x in amb_initial.split(",") if x.strip())
        if amb_final:
            ambiguous_reqs["final"] = set(x.strip() for x in amb_final.split(",") if x.strip())
        if amb_tone:
            ambiguous_reqs["tone"] = set(x.strip() for x in amb_tone.split(",") if x.strip())
        # 排除拼音要求
        ex_initial = self.exc_initial_entry.get().strip().lower()
        ex_final = self.exc_final_entry.get().strip().lower()
        ex_tone = self.exc_tone_entry.get().strip()
        exclude_reqs = {"initial": set(), "final": set(), "tone": set()}
        if ex_initial:
            exclude_reqs["initial"] = set(x.strip() for x in ex_initial.split(",") if x.strip())
        if ex_final:
            exclude_reqs["final"] = set(x.strip() for x in ex_final.split(",") if x.strip())
        if ex_tone:
            exclude_reqs["tone"] = set(x.strip() for x in ex_tone.split(",") if x.strip())
        # 存在但位置不确定的汉字要求（逐字拆分）
        amb_chars_input = self.amb_chars_entry.get().strip()
        ambiguous_chars = set(amb_chars_input) if amb_chars_input else set()
        # 不存在的汉字要求
        nonexist_chars_input = self.nonexist_chars_entry.get().strip()
        non_exist_chars = set(nonexist_chars_input) if nonexist_chars_input else set()

        # 开始筛选
        results = []
        for word, dict_type in words:
            if word_matches(word, specific_reqs, ambiguous_reqs, exclude_reqs, exact_char_reqs, ambiguous_chars, non_exist_chars):
                results.append((word, dict_type))
        # 显示结果
        self.result_text.delete("1.0", tk.END)
        if results:
            for w, t in results:
                self.result_text.insert(tk.END, f"{w}  （词库：{t}）\n")
        else:
            self.result_text.insert(tk.END, "没有符合条件的词语。")

    def reset_all(self):
        """清除所有输入，重置界面，开始新一局游戏"""
        # 重置词库选择
        for var in self.dict_vars.values():
            var.set(False)
        # 清空词语字数
        self.length_entry.delete(0, tk.END)
        # 清空生成的每个字的输入
        for child in self.position_frame.winfo_children():
            child.destroy()
        self.position_inputs = []
        # 清空模糊拼音要求
        self.amb_initial_entry.delete(0, tk.END)
        self.amb_final_entry.delete(0, tk.END)
        self.amb_tone_entry.delete(0, tk.END)
        # 清空排除拼音要求
        self.exc_initial_entry.delete(0, tk.END)
        self.exc_final_entry.delete(0, tk.END)
        self.exc_tone_entry.delete(0, tk.END)
        # 清空汉字要求
        self.amb_chars_entry.delete(0, tk.END)
        self.nonexist_chars_entry.delete(0, tk.END)
        # 清空结果显示
        self.result_text.delete("1.0", tk.END)

if __name__ == "__main__":
    # 切换到脚本所在目录，确保能找到词库文件
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    app = GuessGameGUI()
    app.mainloop()
