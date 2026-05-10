#!/usr/bin/env python3
"""
silo-tui — cliente TUI para Silo
Requiere: pip install textual httpx
"""

import os
import sys
import httpx
import subprocess
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label,
    ListView, ListItem, Select, Static, LoadingIndicator
)
from textual.reactive import reactive

# ── Config ────────────────────────────────────────────
SILO_HOST = os.getenv("SILO_HOST", "http://192.168.1.10:7123").rstrip("/")
SILO_TOKEN = os.getenv("SILO_TOKEN", "changeme")
HEADERS = {"Authorization": f"Bearer {SILO_TOKEN}"}
TIMEOUT = 8.0


# ── API ───────────────────────────────────────────────
class SiloAPI:
    def __init__(self):
        self.client = httpx.Client(headers=HEADERS, timeout=TIMEOUT)

    def get_collections(self):
        r = self.client.get(f"{SILO_HOST}/collections")
        r.raise_for_status()
        return r.json()

    def get_links(self, collection_id=None, q=None):
        params = {}
        if collection_id:
            params["collection_id"] = collection_id
        if q:
            params["q"] = q
        r = self.client.get(f"{SILO_HOST}/links", params=params)
        r.raise_for_status()
        return r.json()

    def add_link(self, url, title=None, collection_id=None):
        body = {"url": url, "title": title, "collection_id": collection_id}
        r = self.client.post(f"{SILO_HOST}/links", json=body)
        r.raise_for_status()
        return r.json()

    def delete_link(self, link_id):
        r = self.client.delete(f"{SILO_HOST}/links/{link_id}")
        r.raise_for_status()

    def fetch_title(self, url):
        try:
            r = self.client.get(f"{SILO_HOST}/links/fetch-title", params={"url": url}, timeout=6)
            if r.status_code == 200:
                return r.json().get("title")
        except Exception:
            pass
        return None


api = SiloAPI()


# ── Modals ────────────────────────────────────────────
class AddLinkModal(ModalScreen):
    CSS = """
    AddLinkModal {
        align: center middle;
    }
    #modal-container {
        width: 60;
        height: auto;
        background: $surface;
        border: tall $primary;
        padding: 1 2;
    }
    #modal-container Label {
        margin-bottom: 1;
        color: $text-muted;
    }
    #modal-title {
        text-align: center;
        color: $primary;
        margin-bottom: 1;
    }
    #modal-container Input {
        margin-bottom: 1;
    }
    #modal-container Select {
        margin-bottom: 1;
    }
    #modal-buttons {
        margin-top: 1;
        height: 3;
    }
    #btn-save {
        width: 1fr;
    }
    #btn-cancel {
        width: 1fr;
    }
    #status-label {
        text-align: center;
        color: $warning;
        height: 1;
    }
    """

    def __init__(self, collections):
        super().__init__()
        self.collections = collections

    def compose(self) -> ComposeResult:
        col_options = [("— sin colección —", "")] + [
            (c["name"], str(c["id"])) for c in self.collections
        ]
        with Container(id="modal-container"):
            yield Label("▶ NUEVO ENLACE", id="modal-title")
            yield Label("URL")
            yield Input(placeholder="https://...", id="input-url")
            yield Label("Título (opcional — se obtiene automáticamente)")
            yield Input(placeholder="dejar vacío para autodetectar", id="input-title")
            yield Label("Colección")
            yield Select(col_options, id="input-collection", allow_blank=False)
            yield Label("", id="status-label")
            with Horizontal(id="modal-buttons"):
                yield Button("GUARDAR", variant="primary", id="btn-save")
                yield Button("CANCELAR", id="btn-cancel")

    @on(Button.Pressed, "#btn-cancel")
    def cancel(self):
        self.dismiss(None)

    @on(Button.Pressed, "#btn-save")
    def save(self):
        url = self.query_one("#input-url", Input).value.strip()
        title = self.query_one("#input-title", Input).value.strip() or None
        col_val = self.query_one("#input-collection", Select).value
        collection_id = int(col_val) if col_val else None

        if not url:
            self.query_one("#status-label", Label).update("⚠ La URL es obligatoria")
            return

        self.query_one("#status-label", Label).update("● Guardando...")
        self.query_one("#btn-save", Button).disabled = True

        self._do_save(url, title, collection_id)

    @work(thread=True)
    def _do_save(self, url, title, collection_id):
        try:
            if not title:
                title = api.fetch_title(url)
            link = api.add_link(url, title, collection_id)
            self.app.call_from_thread(self.dismiss, link)
        except Exception as e:
            self.app.call_from_thread(
                self.query_one("#status-label", Label).update,
                f"✕ Error: {e}"
            )
            self.app.call_from_thread(
                lambda: setattr(self.query_one("#btn-save", Button), "disabled", False)
            )


class ConfirmModal(ModalScreen):
    CSS = """
    ConfirmModal { align: center middle; }
    #confirm-container {
        width: 50;
        height: auto;
        background: $surface;
        border: tall $error;
        padding: 1 2;
    }
    #confirm-msg { text-align: center; margin-bottom: 1; }
    #confirm-buttons { height: 3; }
    #btn-yes { width: 1fr; }
    #btn-no { width: 1fr; }
    """

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-container"):
            yield Label(self.message, id="confirm-msg")
            with Horizontal(id="confirm-buttons"):
                yield Button("SÍ, ELIMINAR", variant="error", id="btn-yes")
                yield Button("CANCELAR", id="btn-no")

    @on(Button.Pressed, "#btn-yes")
    def yes(self):
        self.dismiss(True)

    @on(Button.Pressed, "#btn-no")
    def no(self):
        self.dismiss(False)


# ── Main App ──────────────────────────────────────────
class SiloTUI(App):
    TITLE = "SILO // Link Storage"
    CSS = """
    Screen {
        background: #030a05;
        color: #a0ffcc;
    }

    Header {
        background: #060f08;
        color: #00ff9f;
    }

    Footer {
        background: #060f08;
        color: #4a8a65;
    }

    #sidebar {
        width: 22;
        background: #060f08;
        border-right: tall #00ff9f33;
        padding: 1 0;
    }

    #sidebar-title {
        text-align: center;
        color: #4a8a65;
        padding: 0 1;
        margin-bottom: 1;
    }

    #col-list {
        background: #060f08;
        border: none;
    }

    #col-list > ListItem {
        background: #060f08;
        color: #4a8a65;
        padding: 0 2;
        height: 1;
    }

    #col-list > ListItem:hover {
        background: #00ff9f18;
        color: #00ff9f;
    }

    #col-list > ListItem.--highlight {
        background: #00ff9f18;
        color: #00ff9f;
    }

    #col-list > ListItem Label {
        width: 100%;
    }

    #main {
        background: #030a05;
    }

    #toolbar {
        height: 3;
        background: #060f08;
        border-bottom: tall #00ff9f33;
        padding: 0 1;
        align: left middle;
    }

    #search-input {
        width: 30;
        background: #0a1a0d;
        border: tall #00ff9f33;
        color: #00ff9f;
    }

    #search-input:focus {
        border: tall #00ff9f;
    }

    #btn-add {
        margin-left: 1;
        background: #00ff9f18;
        border: tall #00ff9f;
        color: #00ff9f;
    }

    #btn-add:hover {
        background: #00ff9f33;
    }

    #btn-refresh {
        margin-left: 1;
        background: #060f08;
        border: tall #00ff9f33;
        color: #4a8a65;
    }

    #status-bar {
        height: 1;
        background: #060f08;
        border-top: tall #00ff9f33;
        padding: 0 1;
        color: #4a8a65;
    }

    DataTable {
        background: #030a05;
        color: #a0ffcc;
    }

    DataTable > .datatable--header {
        background: #060f08;
        color: #4a8a65;
        text-style: none;
    }

    DataTable > .datatable--cursor {
        background: #00ff9f18;
        color: #00ff9f;
    }

    DataTable > .datatable--hover {
        background: #00ff9f0a;
    }
    """

    BINDINGS = [
        Binding("a", "add_link", "Agregar"),
        Binding("d", "delete_link", "Borrar"),
        Binding("o", "open_link", "Abrir"),
        Binding("r", "refresh", "Refrescar"),
        Binding("/", "focus_search", "Buscar"),
        Binding("escape", "clear_search", "Limpiar"),
        Binding("q", "quit", "Salir"),
    ]

    collections = reactive([])
    links = reactive([])
    current_collection_id = reactive(None)
    status_msg = reactive("Listo")

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("COLECCIONES", id="sidebar-title")
                yield ListView(id="col-list")
            with Vertical(id="main"):
                with Horizontal(id="toolbar"):
                    yield Input(placeholder="▶ buscar...", id="search-input")
                    yield Button("+ AGREGAR", id="btn-add")
                    yield Button("↺ REFRESCAR", id="btn-refresh")
                yield DataTable(id="links-table", cursor_type="row", zebra_stripes=True)
                yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self):
        table = self.query_one("#links-table", DataTable)
        table.add_columns("ID", "Título / URL", "Colección", "Fecha", "Sync")
        table.fixed_columns = 1
        self.load_data()

    @work(thread=True)
    def load_data(self):
        try:
            self.app.call_from_thread(self.set_status, "● Cargando...")
            cols = api.get_collections()
            self.app.call_from_thread(self._update_collections, cols)
            self._load_links()
        except Exception as e:
            self.app.call_from_thread(self.set_status, f"✕ Error de conexión: {e}")

    def _load_links(self):
        try:
            q = self.query_one("#search-input", Input).value.strip() or None
            links = api.get_links(
                collection_id=self.current_collection_id,
                q=q
            )
            self.app.call_from_thread(self._update_table, links)
        except Exception as e:
            self.app.call_from_thread(self.set_status, f"✕ Error: {e}")

    def _update_collections(self, cols):
        self.collections = cols
        col_list = self.query_one("#col-list", ListView)
        col_list.clear()
        col_list.append(ListItem(Label("// TODOS"), id="col-all"))
        for col in cols:
            col_list.append(ListItem(Label(col['name']), id=f"col-{col['id']}"))

    def _update_table(self, links):
        self.links = links
        table = self.query_one("#links-table", DataTable)
        table.clear()
        for l in links:
            title = l.get("title") or l["url"]
            if len(title) > 45:
                title = title[:42] + "..."
            url_short = l["url"]
            if len(url_short) > 45:
                url_short = url_short[:42] + "..."
            col_name = l.get("collection_name") or "—"
            date = (l.get("created_at") or "")[:10]
            sync = "● sync" if l.get("synced_to_raindrop") else "○ pend"
            table.add_row(
                str(l["id"]),
                title,
                col_name,
                date,
                sync,
                key=str(l["id"])
            )
        self.set_status(f"● {len(links)} enlace(s)")

    def set_status(self, msg):
        self.query_one("#status-bar", Static).update(msg)

    # ── Collection filter ──────────────────────────────
    @on(ListView.Selected, "#col-list")
    def on_col_selected(self, event):
        item_id = event.item.id
        if item_id == "col-all":
            self.current_collection_id = None
        else:
            col_id = int(item_id.replace("col-", ""))
            self.current_collection_id = col_id
        self._load_links_async()

    @work(thread=True)
    def _load_links_async(self):
        self._load_links()

    # ── Search ─────────────────────────────────────────
    @on(Input.Changed, "#search-input")
    def on_search(self, event):
        self._load_links_async()

    def action_focus_search(self):
        self.query_one("#search-input", Input).focus()

    def action_clear_search(self):
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        inp.blur()

    # ── Add ────────────────────────────────────────────
    @on(Button.Pressed, "#btn-add")
    def on_add_btn(self):
        self.action_add_link()

    def action_add_link(self):
        def after_add(result):
            if result:
                self.set_status(f"✔ Enlace guardado: {result.get('title') or result['url']}")
                self._load_links_async()

        self.push_screen(AddLinkModal(self.collections), after_add)

    # ── Delete ─────────────────────────────────────────
    def action_delete_link(self):
        table = self.query_one("#links-table", DataTable)
        if table.cursor_row < 0 or not self.links:
            return
        try:
            row_key = table.get_row_at(table.cursor_row)
            link_id = int(row_key[0])
            link = next((l for l in self.links if l["id"] == link_id), None)
            if not link:
                return
            title = link.get("title") or link["url"]
            msg = f"¿Eliminar?\n{title[:40]}"

            def after_confirm(confirmed):
                if confirmed:
                    self._do_delete(link_id)

            self.push_screen(ConfirmModal(msg), after_confirm)
        except Exception:
            pass

    @work(thread=True)
    def _do_delete(self, link_id):
        try:
            api.delete_link(link_id)
            self.app.call_from_thread(self.set_status, f"✔ Enlace {link_id} eliminado")
            self._load_links()
        except Exception as e:
            self.app.call_from_thread(self.set_status, f"✕ Error al eliminar: {e}")

    # ── Open ───────────────────────────────────────────
    def action_open_link(self):
        table = self.query_one("#links-table", DataTable)
        if table.cursor_row < 0 or not self.links:
            return
        try:
            row_key = table.get_row_at(table.cursor_row)
            link_id = int(row_key[0])
            link = next((l for l in self.links if l["id"] == link_id), None)
            if link:
                subprocess.Popen(["xdg-open", link["url"]])
                self.set_status(f"↗ Abriendo: {link['url'][:60]}")
        except Exception as e:
            self.set_status(f"✕ No se pudo abrir: {e}")

    # ── Refresh ────────────────────────────────────────
    @on(Button.Pressed, "#btn-refresh")
    def on_refresh_btn(self):
        self.action_refresh()

    def action_refresh(self):
        self.load_data()


if __name__ == "__main__":
    app = SiloTUI()
    app.run()
