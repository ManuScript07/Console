import tkinter as tk
from tkinter import scrolledtext
import getpass
import socket
import sys
import os
import argparse
import base64
import xml.etree.ElementTree as ET
import time


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
            
            self.root = self._parse_dir(dir_elem)
            self.cwd = []


        except FileNotFoundError:
            raise FileNotFoundError(f"Файл VFS '{path}' не найден")
        except ET.ParseError:
            raise ValueError(f"Ошибка разбора XML файла '{path}'")
        
    
    def save_to_xml(self, path):
        vfs_elem = ET.Element("vfs")
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
    
    #----------------------------------------------------------------------------------

    def resolve_path(self, path_str):
        if path_str is None:
            return list(self.cwd)
        s = path_str.replace("\\", "/").strip()

        if s == "":
            return []

        absolute = s.startswith("/")
        comps = [c for c in s.split("/") if c != ""]

        if absolute:
            path = []
        else:
            path = list(self.cwd)

        for comp in comps:
            if comp == ".":
                continue
            if comp == "..":
                if path:
                    path.pop()
                continue
            if comp.lower() == "root":
                path = []
                continue
            path.append(comp)
        return path


    def _get_node(self, path):
        node = self.root
        for part in path:
            if part in node["children"]:
                node = node["children"][part]
            else:
                return None
        return node


    def list_dir(self, path_str=None):
        path = self.resolve_path(path_str)
        node = self._get_node(path)
        if node and node["type"] == "dir":
            return list(node["children"].keys())
        return []
    

    def list_dir_details(self, path_str=None):
        path = self.resolve_path(path_str)
        node = self._get_node(path)
        details = []
        if node and node["type"] == "dir":
            for name, child in node["children"].items():
                if child["type"] == "dir":
                    details.append({"name": name, "type": "dir", "children": len(child["children"])})
                else:
                    size = len(child.get("content", ""))
                    details.append({"name": name, "type": "file", "size": size})
        return details


    def change_dir(self, path_str):
        target = self.resolve_path(path_str)
        node = self._get_node(target)
        if node and node["type"] == "dir":
            self.cwd = target
        else:
            raise ValueError(f"Директория '{path_str}' не найдена")
            

    



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
        self.start_time = time.time()
        self.history = []


        root.title(f"Эмулятор - [{self.username}@{self.hostname}]")
        # root.resizable(False, False)
    

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


    def get_uptime(self):
        elapsed = int(time.time() - self.start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"


    def execute_command_from_script(self, line):
        self.write_output(line)
        self.history.append(line)

        tokens = [t for t in line.split(" ") if t]
        cmd, args = tokens[0], tokens[1:]

        try:
            if cmd == "ls":
                long_format = False
                target = None
                for a in args:
                    if a == "-l":
                        long_format = True
                    elif a.startswith("-"):
                        pass
                    else:
                        target = a
                        break

                if long_format:
                    details = self.vfs.list_dir_details(target)
                    if not details:
                        self.write_output("<empty>")
                    else:
                        for d in details:
                            if d["type"] == "dir":
                                self.write_output(f"dr\t{d['name']}\t{d['children']} items")
                            else:
                                self.write_output(f"-f\t{d['name']}\t{d['size']} bytes")
                else:
                    names = self.vfs.list_dir(target)
                    self.write_output(" ".join(names) if names else "<empty>")

            elif cmd == "cd":
                if not args:
                    self.vfs.cwd = []
                else:
                    path_arg = " ".join(args)
                    try:
                        self.vfs.change_dir(path_arg)
                    except ValueError as e:
                        self.write_output(f"Ошибка выполнения команды: {e}")

            elif cmd == "vfs-save":
                if not args:
                    self.write_output("Ошибка: нужно указать путь для сохранения")
                else:
                    self.vfs.save_to_xml(args[0])
                    self.write_output(f"VFS сохранён в {args[0]}")
            
            elif cmd == "uptime":
                self.write_output(f"Uptime: {self.get_uptime()}")

            elif cmd == "history":
                for i, h in enumerate(self.history, 1):
                    self.write_output(f"{i} {h}")
            
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
