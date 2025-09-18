import tkinter as tk
from tkinter import scrolledtext
import getpass
import socket
import sys
import os
import argparse


class ShellEmulator:
    def __init__(self, root, vfs_path = None, script_path = None):
        self.username = getpass.getuser()
        self.hostname = socket.gethostname()
        self.cwd = "~"
        self.prompt = f"[{self.username}@{self.hostname}]$ "

        self.vfs_path = vfs_path
        self.script_path = script_path


        root.title(f"Эмулятор - [{self.username}@{self.hostname}]")
        root.resizable(False, False)
    

        self.output_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=20, width=80, state="disabled")
        self.output_area.pack(padx=10, pady=10, fill="both", expand=True)

        self.input_field = tk.Entry(root, width=80)
        self.input_field.pack(padx=10, pady=(0, 10), fill="x")
        self.input_field.bind("<Return>", self.execute_command)

        self.write_output(self.prompt, newline=False)
        self.write_output(f"[DEBUG] vfs-path: {self.vfs_path if self.vfs_path else '<none>'}")
        self.write_output(f"[DEBUG] script: {self.script_path if self.script_path else '<none>'}")

        if self.script_path:
            self.run_script(self.script_path)


    def write_output(self, text, newline=True):
        self.output_area.config(state="normal")
        self.output_area.insert(tk.END, text + ("\n" if newline else ""))
        self.output_area.see(tk.END)
        self.output_area.config(state="disabled")


    def run_script(self, path):
        if not os.path.exists(path):
            self.write_output(f"Ошибка: не найден скрипт '{path}'")
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    self.execute_command_from_script(line)
        except Exception as e:
            self.write_output(f"Ошибка при выполнении скрипта: {e}")


    def execute_command_from_script(self, line):
        self.write_output(line)

        tokens = [t for t in line.split(" ") if t]
        cmd, args = tokens[0], tokens[1:]

        if cmd == "ls":
            self.write_output(f"ls: args: {' '.join(args) if args else '<none>'}")
        elif cmd == "cd":
            if len(args) == 0:
                self.write_output("cd: args: <none>")
            elif len(args) == 1:
                self.cwd = args[0]
                self.write_output(f"cd: args: {args[0]}")
            else:
                self.write_output("Ошибка: неверные аргументы для 'cd' (ожидалось не более 1)")
        elif cmd == "exit":
            self.write_output("Выход из эмулятора... Нажмите любую клавишу для закрытия окна.")
            self.input_field.unbind("<Return>")
            self.input_field.bind("<Key>", lambda e: sys.exit())
            return
        else:
            self.write_output(f"Ошибка: неизвестная команда '{cmd}'")

        self.write_output(self.prompt, newline=False)


    def execute_command(self, event=None):
        line = self.input_field.get().strip()
        self.input_field.delete(0, tk.END)

        if not line:
            self.write_output(self.prompt, newline=False)
            return

        self.execute_command_from_script(line)

    
def parse_args():
    parser = argparse.ArgumentParser(description="Эмулятор командной строки (Этап 2)")
    parser.add_argument("--vfs-path", type=str, help="Путь к виртуальной файловой системе")
    parser.add_argument("--script", type=str, help="Путь к стартовому скрипту")
    return parser.parse_args()
        


if __name__ == "__main__":
    args = parse_args()

    root = tk.Tk()
    app = ShellEmulator(root, vfs_path=args.vfs_path, script_path=args.script)
    root.mainloop()
