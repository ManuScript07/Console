import tkinter as tk
from tkinter import scrolledtext
import getpass
import socket
import sys
import os
import argparse
import base64
import xml.etree.ElementTree as ET



class VFS:
    def __init__(self):
        self.root = {"type": "dir", "children": {}}
        self.cwd = []

    
    def load_from_xml(self, path):
        try:
            tree = ET.parse(path)
            root_elem = tree.getroot()

            if root_elem.tag != "vfs":
                raise ValueError("Некорректный формат: корень не <vfs>")
            
            dir_elem = root_elem.find("dir")
            if dir_elem is None:
                raise ValueError("VFS не содержит корневой директории")
            
            # root_name = dir_elem.get("name", "root")
            # self.root = self._parse_dir(dir_elem)
            # self.cwd = [root_name]
            self.root = self._parse_dir(dir_elem)
            self.cwd = []


        except FileNotFoundError:
            raise FileNotFoundError(f"Файл VFS '{path}' не найден")
        except ET.ParseError:
            raise ValueError(f"Ошибка разбора XML файла '{path}'")
        
    
    def save_to_xml(self, path):
        vfs_elem = ET.Element("vfs")
        root_name = self.cwd[0] if self.cwd else "root"
        vfs_elem.append(self._dir_to_xml(self.root, "root"))
        tree = ET.ElementTree(vfs_elem)
        tree.write(path, encoding="utf-8", xml_declaration=True)

    
    def _parse_dir(self, elem):
        node = {"type": "dir", "children": {}}
        for child in elem:
            if child.tag == "dir":
                node["children"][child.get("name")] = self._parse_dir(child)
            elif child.tag == "file":
                data = child.text or ""
                decoded = base64.b64decode(data).decode("utf-8", errors="ignore")
                node["children"][child.get("name")] = {
                    "type": "file",
                    "content": decoded,
                }
        return node
    

    def _dir_to_xml(self, node, name):
        dir_elem = ET.Element("dir", {"name": name})
        for child_name, child in node["children"].items():
            if child["type"] == "dir":
                dir_elem.append(self._dir_to_xml(child, child_name))
            elif child["type"] == "file":
                encoded = base64.b64encode(child["content"].encode("utf-8")).decode("utf-8")
                file_elem = ET.Element("file", {"name": child_name})
                file_elem.text = encoded
                dir_elem.append(file_elem)
        return dir_elem
    

    def list_dir(self):
        node = self._get_node(self.cwd)
        if node and node["type"] == "dir":
            return list(node["children"].keys())
        return []
    

    def change_dir(self, dirname):
        if dirname == "..":
            if self.cwd:
                self.cwd.pop()
        else:
            node = self._get_node(self.cwd)
            if (
                node
                and dirname in node["children"]
                and node["children"][dirname]["type"] == "dir"
            ):
                self.cwd.append(dirname)
                print(self.cwd)
            else:
                raise ValueError(f"Директория '{dirname}' не найдена")
            

    def _get_node(self, path):
        node = self.root
        for part in path:
            if part in node["children"]:
                node = node["children"][part]
            else:
                return None
        return node



class ShellEmulator:
    def __init__(self, root, vfs_path = None, script_path = None):
        self.username = getpass.getuser()
        self.hostname = socket.gethostname()
        self.prompt = f"[{self.username}@{self.hostname}]$ "

        self.vfs = VFS()
        if vfs_path:
            try:
                self.vfs.load_from_xml(vfs_path)
                vfs_status = f"VFS загружен из {vfs_path}"
            except Exception as e:
                vfs_status = f"Ошибка загрузки VFS: {e}"
        else:
            vfs_status = "VFS не загружен"

        self.script_path = script_path


        root.title(f"Эмулятор - [{self.username}@{self.hostname}]")
        root.resizable(False, False)
    

        self.output_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=20, width=80, state="disabled")
        self.output_area.pack(padx=10, pady=10, fill="both", expand=True)

        self.input_field = tk.Entry(root, width=80)
        self.input_field.pack(padx=10, pady=(0, 10), fill="x")
        self.input_field.bind("<Return>", self.execute_command)

        self.write_output(self.prompt, newline=False)
        self.write_output(f"[DEBUG] {vfs_status}")
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

        try:
            if cmd == "ls":
                # items = self.vfs.list_dir()
                self.write_output(f"ls: args: {' '.join(args) if args else '<none>'}")
            elif cmd == "cd":
                if len(args) == 0:
                    self.write_output("cd: args: <none>")
                else:
                    self.write_output("Неверные аргументы для cd")
                # else:
                #     self.vfs.change_dir(args[0])
            elif cmd == "vfs-save":
                if not args:
                    self.write_output("Ошибка: нужно указать путь для сохранения")
                else:
                    self.vfs.save_to_xml(args[0])
                    self.write_output(f"VFS сохранён в {args[0]}")
            elif cmd == "exit":
                self.write_output("Выход из эмулятора... Нажмите любую клавишу для закрытия окна.")
                self.input_field.unbind("<Return>")
                self.input_field.bind("<Key>", lambda e: sys.exit())
                return
            else:
                self.write_output(f"Ошибка: неизвестная команда '{cmd}'")
        except Exception as e:
            self.write_output(f"Ошибка выполнения команды: {e}")

        self.write_output(self.prompt, newline=False)


    def execute_command(self, event=None):
        line = self.input_field.get().strip()
        self.input_field.delete(0, tk.END)

        if not line:
            self.write_output(self.prompt, newline=False)
            return

        self.execute_command_from_script(line)

    
def parse_args():
    parser = argparse.ArgumentParser(description="Эмулятор командной строки (Этап 3)")
    parser.add_argument("--vfs-path", type=str, help="Путь к виртуальной файловой системе (XML)")
    parser.add_argument("--script", type=str, help="Путь к стартовому скрипту")
    return parser.parse_args()
        


if __name__ == "__main__":
    args = parse_args()
    root = tk.Tk()
    app = ShellEmulator(root, vfs_path=args.vfs_path, script_path=args.script)
    root.mainloop()
