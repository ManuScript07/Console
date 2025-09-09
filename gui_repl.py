import tkinter as tk
from tkinter import scrolledtext
import getpass
import socket
import sys


class ShellEmulator:
    def __init__(self, root):
        self.username = getpass.getuser()
        self.hostname = socket.gethostname()
        self.cwd = "~"
        self.prompt = f"[{self.username}@{self.hostname}]$ "

        root.title(f"Эмулятор - [{self.username}@{self.hostname}]")
        root.resizable(False, False)
    

        self.output_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=20, width=80, state="disabled")
        self.output_area.pack(padx=10, pady=10, fill="both", expand=True)

        self.input_field = tk.Entry(root, width=80)
        self.input_field.pack(padx=10, pady=(0, 10), fill="x")
        self.input_field.bind("<Return>", self.execute_command)

        self.write_output(self.prompt, newline=False)

    def write_output(self, text, newline=True):
        self.output_area.config(state="normal")
        self.output_area.insert(tk.END, text + ("\n" if newline else ""))
        self.output_area.see(tk.END)
        self.output_area.config(state="disabled")

    def execute_command(self, event=None):
        line = self.input_field.get().strip()
        self.input_field.delete(0, tk.END)

        if not line:
            self.write_output(self.prompt, newline=False)
            return


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
            self.write_output("Выход из эмулятора...")
            self.output_area.after(5000, sys.exit)
            return
        else:
            self.write_output(f"Ошибка: неизвестная команда '{cmd}'")

        self.write_output(self.prompt, newline=False)


if __name__ == "__main__":
    root = tk.Tk()
    app = ShellEmulator(root)
    root.mainloop()
