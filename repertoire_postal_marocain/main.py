"""Répertoire postal marocain : recherche et modification hors ligne."""
import csv
import os
import sqlite3
from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
CSV_FILE = os.path.join(DATA, "localites_postales.csv")


def connect_database(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE IF NOT EXISTS localites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        region_postale TEXT NOT NULL DEFAULT '',
        province TEXT NOT NULL DEFAULT '',
        localite TEXT NOT NULL,
        code_postal TEXT NOT NULL DEFAULT '',
        site_destination TEXT NOT NULL DEFAULT ''
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_localite ON localites(localite)")
    conn.commit()
    return conn


def csv_rows(path):
    """Lit un CSV UTF-8 avec séparateur virgule, point-virgule ou tabulation."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        if not reader.fieldnames:
            return []
        fields = {str(k).strip().lower(): k for k in reader.fieldnames}

        def field(*names):
            for name in names:
                if name.lower() in fields:
                    return fields[name.lower()]
            return None

        region_key = field("region_postale", "region")
        province_key = field("province")
        localite_key = field("localite", "localité", "ville", "commune")
        code_key = field("code_postal", "nouveau code postal", "code postal", "code")
        site_key = field("site_destination", "site de destination", "destination")
        rows = []
        for row in reader:
            localite = (row.get(localite_key) or "").strip() if localite_key else ""
            if localite:
                rows.append((
                    (row.get(region_key) or "").strip() if region_key else "",
                    (row.get(province_key) or "").strip() if province_key else "",
                    localite,
                    (row.get(code_key) or "").strip() if code_key else "",
                    (row.get(site_key) or "").strip() if site_key else ""
                ))
        return rows


def import_csv(path, conn):
    rows = csv_rows(path)
    with conn:
        conn.execute("DELETE FROM localites")
        conn.executemany(
            "INSERT INTO localites(region_postale,province,localite,code_postal,site_destination) "
            "VALUES(?,?,?,?,?)", rows
        )
    return len(rows)


class PostalApp(App):
    title = "Répertoire postal marocain"

    def build(self):
        # La base Android est stockée dans le répertoire privé de l'application.
        self.db_path = os.path.join(self.user_data_dir, "localites_postales.db")
        self.db = connect_database(self.db_path)
        count = self.db.execute("SELECT COUNT(*) FROM localites").fetchone()[0]
        if count == 0 and os.path.exists(CSV_FILE):
            try:
                import_csv(CSV_FILE, self.db)
            except Exception as exc:
                self.popup("Erreur d'importation", str(exc))

        page = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(7))
        page.add_widget(Label(text="[b]Répertoire postal marocain[/b]", markup=True,
                              font_size="21sp", size_hint_y=None, height=dp(40)))

        self.search = TextInput(
            hint_text="Rechercher localité, code, province, région…",
            multiline=False, size_hint_y=None, height=dp(46)
        )
        self.search.bind(text=lambda *_: self.refresh())
        page.add_widget(self.search)

        filters = BoxLayout(size_hint_y=None, height=dp(43), spacing=dp(6))
        self.region_filter = Spinner(text="Toutes les régions", values=(), size_hint_x=0.65)
        self.region_filter.bind(text=lambda *_: self.refresh())
        filters.add_widget(self.region_filter)
        add_btn = Button(text="+ Ajouter", size_hint_x=0.35)
        add_btn.bind(on_release=lambda *_: self.edit_record())
        filters.add_widget(add_btn)
        page.add_widget(filters)

        self.status = Label(text="", size_hint_y=None, height=dp(26))
        page.add_widget(self.status)
        scroll = ScrollView()
        self.results = GridLayout(cols=1, spacing=dp(6), padding=(0, dp(4)), size_hint_y=None)
        self.results.bind(minimum_height=self.results.setter("height"))
        scroll.add_widget(self.results)
        page.add_widget(scroll)

        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        export_btn = Button(text="Exporter CSV")
        export_btn.bind(on_release=lambda *_: self.export_csv())
        actions.add_widget(export_btn)
        import_btn = Button(text="Réimporter CSV")
        import_btn.bind(on_release=lambda *_: self.confirm_import())
        actions.add_widget(import_btn)
        page.add_widget(actions)

        self.refresh_regions()
        self.refresh()
        return page

    def refresh_regions(self):
        regions = [r[0] for r in self.db.execute(
            "SELECT DISTINCT region_postale FROM localites "
            "WHERE region_postale<>'' ORDER BY region_postale"
        ).fetchall()]
        self.region_filter.values = ["Toutes les régions"] + regions
        if self.region_filter.text not in self.region_filter.values:
            self.region_filter.text = "Toutes les régions"

    def refresh(self):
        if not hasattr(self, "results"):
            return
        self.results.clear_widgets()
        q = self.search.text.strip()
        like = f"%{q}%"
        sql = """SELECT id, region_postale, province, localite, code_postal, site_destination
                 FROM localites WHERE (region_postale LIKE ? OR province LIKE ?
                 OR localite LIKE ? OR code_postal LIKE ? OR site_destination LIKE ?)"""
        params = [like] * 5
        if hasattr(self, "region_filter") and self.region_filter.text != "Toutes les régions":
            sql += " AND region_postale=?"
            params.append(self.region_filter.text)
        sql += " ORDER BY localite COLLATE NOCASE LIMIT 600"
        rows = self.db.execute(sql, params).fetchall()
        total = self.db.execute("SELECT COUNT(*) FROM localites").fetchone()[0]
        self.status.text = f"{len(rows)} résultat(s) affiché(s) • {total} localité(s)"
        if not rows:
            self.results.add_widget(Label(text="Aucun résultat.", size_hint_y=None, height=dp(60)))
            return
        for record in rows:
            rid, region, province, localite, code, site = record
            details = f"[b]{localite}[/b]"
            if code:
                details += f"   •   Code postal : {code}"
            details += f"\\nProvince : {province or 'Non renseignée'}"
            details += f"\\nRégion : {region or 'Non renseignée'}"
            details += f"\\nDestination : {site or 'À compléter'}"
            card = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(130),
                             padding=dp(6), spacing=dp(4))
            label = Label(text=details, markup=True, halign="left", valign="middle")
            label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
            card.add_widget(label)
            edit = Button(text="Modifier cette fiche", size_hint_y=None, height=dp(38))
            edit.bind(on_release=lambda _btn, data=record: self.edit_record(data))
            card.add_widget(edit)
            self.results.add_widget(card)

    def edit_record(self, record=None):
        """Formulaire d'ajout/modification d'une localité."""
        is_edit = record is not None
        rid, region, province, localite, code, site = record if is_edit else (None, "", "", "", "", "")
        body = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(7))
        fields = {}
        for key, caption, value in [
            ("localite", "Localité *", localite),
            ("code", "Code postal", code),
            ("province", "Province", province),
            ("region", "Région postale", region),
            ("site", "Site de destination", site),
        ]:
            body.add_widget(Label(text=caption, size_hint_y=None, height=dp(22), halign="left"))
            inp = TextInput(text=str(value or ""), multiline=False, size_hint_y=None, height=dp(40))
            fields[key] = inp
            body.add_widget(inp)
        buttons = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        save = Button(text="Enregistrer")
        cancel = Button(text="Annuler")
        buttons.add_widget(save)
        buttons.add_widget(cancel)
        body.add_widget(buttons)
        popup = Popup(title="Modifier une fiche" if is_edit else "Ajouter une localité",
                      content=body, size_hint=(0.94, 0.88), auto_dismiss=False)

        def save_record(*_):
            name = fields["localite"].text.strip()
            if not name:
                self.popup("Champ obligatoire", "Le nom de la localité est obligatoire.")
                return
            values = (
                fields["region"].text.strip(),
                fields["province"].text.strip(),
                name,
                fields["code"].text.strip(),
                fields["site"].text.strip()
            )
            with self.db:
                if is_edit:
                    self.db.execute(
                        "UPDATE localites SET region_postale=?, province=?, localite=?, "
                        "code_postal=?, site_destination=? WHERE id=?", values + (rid,)
                    )
                else:
                    self.db.execute(
                        "INSERT INTO localites(region_postale,province,localite,code_postal,site_destination) "
                        "VALUES(?,?,?,?,?)", values
                    )
            popup.dismiss()
            self.refresh_regions()
            self.refresh()

        save.bind(on_release=save_record)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def export_csv(self):
        """Exporte les modifications dans le dossier privé de l'application."""
        output = os.path.join(self.user_data_dir, "localites_postales_modifiees.csv")
        rows = self.db.execute(
            "SELECT region_postale,province,localite,code_postal,site_destination "
            "FROM localites ORDER BY localite"
        ).fetchall()
        with open(output, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["region_postale", "province", "localite", "code_postal", "site_destination"])
            writer.writerows(rows)
        self.popup("Export terminé", "CSV exporté dans le dossier privé de l'application :\\n" + output)

    def confirm_import(self):
        self.popup(
            "Réimporter le CSV",
            "Pour éviter d'effacer des modifications par erreur, cette version ne remplace pas "
            "les données depuis l'interface. Modifiez le CSV source puis recompilez l'application. "
            "Les changements faits dans l'application sont conservés dans SQLite."
        )

    def popup(self, title, message):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        label = Label(text=message, halign="left", valign="middle")
        label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        box.add_widget(label)
        close = Button(text="Fermer", size_hint_y=None, height=dp(42))
        box.add_widget(close)
        popup = Popup(title=title, content=box, size_hint=(0.9, 0.58))
        close.bind(on_release=popup.dismiss)
        popup.open()

    def on_stop(self):
        try:
            self.db.close()
        except Exception:
            pass


if __name__ == "__main__":
    PostalApp().run()
