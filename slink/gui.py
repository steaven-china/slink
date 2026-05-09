"""
Simple tkinter GUI for slink.
Usage: slink-ui
"""
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from .crypto import DecryptError
import json

from .ssh_wrapper import connect as ssh_connect, connect_chain
from .store import add_host, get_host, list_hosts, remove_host, upsert_host


class PasswordDialog(tk.Toplevel):
    """Modal dialog to ask for the master password."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Master Password")
        self.password = None
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        tk.Label(self, text="Enter master password:").pack(padx=10, pady=(10, 5))
        self.entry = tk.Entry(self, show="*", width=30)
        self.entry.pack(padx=10, pady=5)
        self.entry.focus()
        self.entry.bind("<Return>", lambda _e: self._ok())

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=(5, 10))
        tk.Button(btn_frame, text="OK", width=8, command=self._ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", width=8, command=self.destroy).pack(side=tk.LEFT, padx=5)

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_visibility()
        self.geometry(
            "+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50)
        )

    def _ok(self):
        pw = self.entry.get()
        if pw:
            self.password = pw
        self.destroy()


class HostDialog(tk.Toplevel):
    """Modal dialog to add or edit a host."""

    def __init__(self, parent, password, name=None, info=None):
        super().__init__(parent)
        self.title("Edit Host" if name else "Add Host")
        self.result = None
        self.transient(parent)
        self.grab_set()
        self.resizable(True, False)

        info = info or {}
        row = 0

        # Name
        tk.Label(self, text="Name:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        self.name_var = tk.StringVar(value=name or "")
        name_state = "readonly" if name else "normal"
        tk.Entry(self, textvariable=self.name_var, state=name_state).grid(
            row=row, column=1, sticky="we", padx=5, pady=3
        )
        row += 1

        # Hostname
        tk.Label(self, text="Hostname:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        self.hostname_var = tk.StringVar(value=info.get("hostname", ""))
        tk.Entry(self, textvariable=self.hostname_var).grid(
            row=row, column=1, sticky="we", padx=5, pady=3
        )
        row += 1

        # Port
        tk.Label(self, text="Port:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        self.port_var = tk.StringVar(value=str(info.get("port", 22)))
        tk.Entry(self, textvariable=self.port_var, width=8).grid(
            row=row, column=1, sticky="w", padx=5, pady=3
        )
        row += 1

        # Username
        tk.Label(self, text="Username:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        self.username_var = tk.StringVar(value=info.get("username", ""))
        tk.Entry(self, textvariable=self.username_var).grid(
            row=row, column=1, sticky="we", padx=5, pady=3
        )
        row += 1

        # SSH Password
        tk.Label(self, text="SSH Password:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        self.password_var = tk.StringVar(value=info.get("password", ""))
        tk.Entry(self, textvariable=self.password_var, show="*").grid(
            row=row, column=1, sticky="we", padx=5, pady=3
        )
        row += 1

        # Key file
        tk.Label(self, text="Key file:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        key_frame = tk.Frame(self)
        key_frame.grid(row=row, column=1, sticky="we", padx=5, pady=3)
        self.key_file_var = tk.StringVar(value=info.get("key_file", ""))
        tk.Entry(key_frame, textvariable=self.key_file_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(key_frame, text="Browse...", command=self._browse_key).pack(side=tk.LEFT, padx=(5, 0))
        row += 1

        # Key text
        tk.Label(self, text="Key text:").grid(row=row, column=0, sticky="ne", padx=5, pady=3)
        self.key_text = tk.Text(self, height=5, width=40)
        self.key_text.grid(row=row, column=1, sticky="we", padx=5, pady=3)
        if info.get("key"):
            self.key_text.insert("1.0", info["key"])
        row += 1

        # Extra args
        tk.Label(self, text="Extra args:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        extra = info.get("extra_args", [])
        self.extra_args_var = tk.StringVar(value=" ".join(extra) if isinstance(extra, list) else str(extra))
        tk.Entry(self, textvariable=self.extra_args_var).grid(
            row=row, column=1, sticky="we", padx=5, pady=3
        )
        row += 1

        # Buttons
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Save", width=10, command=self._save).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", width=10, command=self.destroy).pack(side=tk.LEFT, padx=5)

        self.columnconfigure(1, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_visibility()
        self.geometry(
            "+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50)
        )

    def _browse_key(self):
        path = filedialog.askopenfilename(title="Select private key file")
        if path:
            self.key_file_var.set(path)

    def _save(self):
        name = self.name_var.get().strip()
        hostname = self.hostname_var.get().strip()
        port_str = self.port_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get()
        key_file = self.key_file_var.get().strip()
        key_text = self.key_text.get("1.0", tk.END).strip()
        extra_raw = self.extra_args_var.get().strip()
        extra_args = extra_raw.split() if extra_raw else []

        if not name:
            messagebox.showwarning("Validation", "Name is required.")
            return
        if not hostname:
            messagebox.showwarning("Validation", "Hostname is required.")
            return
        try:
            port = int(port_str) if port_str else 22
        except ValueError:
            messagebox.showwarning("Validation", "Port must be an integer.")
            return

        info = {
            "hostname": hostname,
            "port": port,
            "username": username,
        }
        if password:
            info["password"] = password
        if key_text:
            info["key"] = key_text
        elif key_file:
            info["key_file"] = key_file
        if extra_args:
            info["extra_args"] = extra_args

        self.result = {"name": name, "info": info}
        self.destroy()


class SlinkGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("slink - Secure SSH Manager")
        self.geometry("900x550")
        self.minsize(600, 400)
        self.password = None
        self.hosts = {}
        self.selected_name = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        self.after(50, self._ask_password)

    def _build_ui(self):
        # Left panel
        left = tk.Frame(self, width=240)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left.pack_propagate(False)

        tk.Label(left, text="Hosts", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))

        # Search box
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        search_entry = tk.Entry(left, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, pady=(0, 5))
        search_entry.insert(0, "Search...")
        search_entry.bind("<FocusIn>", lambda e: search_entry.select_range(0, tk.END) if search_entry.get() == "Search..." else None)
        search_entry.bind("<FocusOut>", lambda e: search_entry.insert(0, "Search...") if not search_entry.get() else None)

        list_frame = tk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, exportselection=False, activestyle="dotbox")
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self.listbox.bind("<Double-Button-1>", lambda _e: self._connect())
        self.listbox.bind("<Return>", lambda _e: self._connect())
        self.listbox.bind("<Delete>", lambda _e: self._delete_host())
        self.listbox.bind("<F2>", lambda _e: self._edit_host())
        self.bind("j", lambda _e: self._jump_list())
        self.bind("<Control-f>", lambda _e: search_entry.focus_set())
        self.bind("<Control-n>", lambda _e: self._add_host())

        btn_frame = tk.Frame(left)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        for label, cmd in [
            ("Add (Ctrl+N)", self._add_host),
            ("Edit (F2)", self._edit_host),
            ("Delete (Del)", self._delete_host),
            ("Connect (Enter)", self._connect),
            ("Jump List (J)", self._jump_list),
            ("Open Chain", self._open_chain),
            ("Export Chain", self._export_chain),
        ]:
            tk.Button(btn_frame, text=label, command=cmd).pack(fill=tk.X, pady=2)

        # Right panel
        right = tk.Frame(self, relief=tk.SUNKEN, bd=1)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.detail_text = tk.Text(
            right, wrap=tk.WORD, state=tk.DISABLED, padx=10, pady=10, font=("Consolas", 10)
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(self, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Default focus
        self.after(100, lambda: self.listbox.focus_set())

    def _ask_password(self):
        dialog = PasswordDialog(self)
        self.wait_window(dialog)
        if dialog.password:
            self.password = dialog.password
            self._load_hosts()
        else:
            self.destroy()

    def _load_hosts(self):
        try:
            self.hosts = list_hosts(password=self.password)
        except DecryptError:
            messagebox.showerror("Error", "Invalid master password.")
            self._ask_password()
            return
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load hosts: {exc}")
            self._ask_password()
            return
        self._refresh_list()
        self._clear_detail()
        self.status_var.set(f"Loaded {len(self.hosts)} host(s)")

    def _refresh_list(self):
        if not hasattr(self, "listbox"):
            return
        self.listbox.delete(0, tk.END)
        self._list_names = []
        search = self.search_var.get().lower()
        if search == "search...":
            search = ""
        selected_idx = None
        for name in sorted(self.hosts):
            if search in name.lower():
                idx = self.listbox.size()
                self.listbox.insert(tk.END, name)
                self._list_names.append(name)
                if name == getattr(self, "selected_name", None):
                    selected_idx = idx
        if selected_idx is not None:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(selected_idx)
            self.listbox.see(selected_idx)
        else:
            self.selected_name = None

    def _on_search(self, *args):
        if not hasattr(self, "listbox"):
            return
        self._refresh_list()

    def _clear_detail(self):
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, "Select a host to view details.")
        self.detail_text.config(state=tk.DISABLED)
        self.selected_name = None

    def _on_select(self, _event):
        sel = self.listbox.curselection()
        if not sel:
            return
        name = self.listbox.get(sel[0])
        self.selected_name = name
        info = self.hosts.get(name, {})
        self._show_detail(name, info)

    def _show_detail(self, name, info):
        lines = [
            f"Name:      {name}",
            f"Hostname:  {info.get('hostname', '')}",
            f"Port:      {info.get('port', 22)}",
            f"Username:  {info.get('username', '')}",
            f"Key file:  {info.get('key_file') or ('<inline key>' if info.get('key') else 'None')}",
            f"Password:  {'<set>' if info.get('password') else 'None'}",
            f"Extra:     {' '.join(info.get('extra_args', [])) or 'None'}",
        ]
        jump_host = info.get("jump_host")
        if jump_host:
            lines.append(f"Jumps:     {', '.join(str(j) for j in jump_host)}")
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, "\n".join(lines))
        self.detail_text.config(state=tk.DISABLED)

    def _add_host(self):
        dialog = HostDialog(self, password=self.password)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            add_host(dialog.result["name"], dialog.result["info"], password=self.password)
            self._load_hosts()
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))

    def _edit_host(self):
        if not self.selected_name:
            messagebox.showwarning("Select", "Please select a host to edit.")
            return
        info = self.hosts.get(self.selected_name, {})
        dialog = HostDialog(
            self, password=self.password, name=self.selected_name, info=info
        )
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            upsert_host(dialog.result["name"], dialog.result["info"], password=self.password)
            self._load_hosts()
            # Reselect
            names = list(self.listbox.get(0, tk.END))
            if dialog.result["name"] in names:
                idx = names.index(dialog.result["name"])
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(idx)
                self.listbox.see(idx)
                self._on_select(None)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _delete_host(self):
        if not self.selected_name:
            messagebox.showwarning("Select", "Please select a host to delete.")
            return
        if not messagebox.askyesno("Confirm", f"Delete host '{self.selected_name}'?"):
            return
        try:
            remove_host(self.selected_name, password=self.password)
            self._load_hosts()
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))

    def _connect(self):
        if not self.selected_name:
            messagebox.showwarning("Select", "Please select a host to connect.")
            return
        info = self.hosts.get(self.selected_name)
        if not info:
            return
        self.status_var.set(f"Connecting to {self.selected_name}...")
        self.update_idletasks()
        def _do_connect():
            try:
                if info.get("_chain"):
                    connect_chain(info["_chain"]["jumps"], info["_chain"]["endpoint"])
                else:
                    ssh_connect(info)
            finally:
                self.after(0, lambda: self.status_var.set("Ready"))
        threading.Thread(target=_do_connect, daemon=True).start()

    def _open_chain(self):
        path = filedialog.askopenfilename(
            title="Open Chain File",
            filetypes=[("Chain files", "*.chain *.chain.enc"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            from .cli import _try_load_file
            loaded = _try_load_file(path)
            if "_chain" in loaded:
                self.status_var.set(f"Connecting chain {os.path.basename(path)}...")
                self.update_idletasks()
                def _do():
                    try:
                        connect_chain(loaded["_chain"]["jumps"], loaded["_chain"]["endpoint"])
                    finally:
                        self.after(0, lambda: self.status_var.set("Ready"))
                threading.Thread(target=_do, daemon=True).start()
            elif loaded.get("hostname"):
                self.status_var.set(f"Connecting {os.path.basename(path)}...")
                self.update_idletasks()
                def _do():
                    try:
                        ssh_connect(loaded)
                    finally:
                        self.after(0, lambda: self.status_var.set("Ready"))
                threading.Thread(target=_do, daemon=True).start()
            else:
                messagebox.showerror("Error", "Invalid chain or host file.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    @staticmethod
    def _parse_jump_spec(spec: str) -> dict:
        username = None
        port = 22
        if "@" in spec:
            username, spec = spec.split("@", 1)
        if ":" in spec:
            spec, port_str = spec.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                pass
        return {"hostname": spec, "username": username, "port": port}

    def _export_chain(self):
        if not self.selected_name:
            messagebox.showwarning("Select", "Please select a host to export.")
            return
        info = self.hosts.get(self.selected_name, {})
        endpoint = {
            "hostname": info.get("hostname"),
            "username": info.get("username"),
            "port": info.get("port", 22),
        }
        jumps = []
        for spec in info.get("jump_host", []):
            jump_info = get_host(spec, password=self.password)
            if jump_info:
                jumps.append({
                    "hostname": jump_info.get("hostname", spec),
                    "username": jump_info.get("username"),
                    "port": jump_info.get("port", 22),
                })
            else:
                jumps.append(self._parse_jump_spec(spec))
        chain_data = {"jumps": jumps, "endpoint": endpoint}
        path = filedialog.asksaveasfilename(
            title="Export as Chain",
            defaultextension=".chain",
            filetypes=[("Chain files", "*.chain"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(chain_data, f, ensure_ascii=False, indent=2)
                f.write("\n")
            messagebox.showinfo("Exported", f"Chain saved to {path}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _on_close(self):
        from .ssh_wrapper import terminate_all
        terminate_all()
        self.destroy()

    def _jump_list(self):
        if self.selected_name:
            name = self.selected_name
        else:
            name = simpledialog.askstring("Jump List", "Enter jump host name:", parent=self)
            if not name:
                return
        threading.Thread(target=self._do_jump_list, args=(name,), daemon=True).start()

    def _do_jump_list(self, name):
        try:
            info = get_host(name, password=self.password)
            if not info:
                self.after(0, lambda: messagebox.showwarning("Not found", f"Host '{name}' not found."))
                return

            ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=accept-new"]
            user = info.get("username")
            host = info.get("hostname", name)
            port = info.get("port", 22)
            target = f"{user}@{host}" if user else host
            if port != 22:
                ssh_cmd.extend(["-p", str(port)])

            ssh_cmd.extend([target, "cat", "~/.slink/.show_direct"])
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                self.after(0, lambda: messagebox.showerror("Error", f"SSH failed:\n{result.stderr.strip()}"))
                return

            output = result.stdout.strip() or "(empty .show_direct)"
            self.after(0, lambda: self._show_jump_list(name, output))
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Error", str(exc)))

    def _show_jump_list(self, name, output):
        lines = [
            f"Jump host: {name}",
            "=" * 40,
            output,
        ]
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, "\n".join(lines))
        self.detail_text.config(state=tk.DISABLED)


def main():
    app = SlinkGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
