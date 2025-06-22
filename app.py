import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import sqlite3
import os
from datetime import datetime

from expensetracker.features.daily_journal import DailyJournalView
from expensetracker.features.habit_tracker import HabitTrackerView

class LifeJournalApp(toga.App):
    def startup(self):
        db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'database')
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, 'life_journal.db')
        self.conn = sqlite3.connect(self.db_path)
        self.create_tables()

        self.daily_journal_view = DailyJournalView(self)
        self.habit_tracker_view = HabitTrackerView(self)

        self.main_box = toga.Box(style=Pack(direction=COLUMN, flex=1))

        # Warna navigasi
        self.nav_box = toga.Box(style=Pack(direction=ROW, padding=10, background_color="#FDF3CD"))
        self.btn_daily_journal = toga.Button(
            'Catatan Harianku',
            on_press=self.show_daily_journal,
            style=Pack(flex=1, padding=5, font_size=14, background_color="#F2C889")
        )
        self.btn_habit_tracker = toga.Button(
            'Kebiasaanku 💪',
            on_press=self.show_habit_tracker,
            style=Pack(flex=1, padding=5, font_size=14, background_color="#F2C889")
        )

        self.nav_box.add(self.btn_daily_journal)
        self.nav_box.add(self.btn_habit_tracker)

        # Konten utama
        self.content_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=10, background_color="#FFFDE7"))
        self.main_box.add(self.nav_box)
        self.main_box.add(self.content_box)

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = self.main_box
        self.main_window.show()

        self.show_daily_journal()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS daily_journal
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, title TEXT NOT NULL, content TEXT, mood TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS habits
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, frequency TEXT NOT NULL, last_performed TEXT, target TEXT)''')
        self.conn.commit()

    def clear_content(self):
        for child in self.content_box.children[:]:
            self.content_box.remove(child)

    def update_nav_buttons(self, active_widget):
        default_style = {'background_color': "#F2C889"}
        active_style = {'background_color': '#FFB74D'}

        if self.btn_daily_journal.style:
            self.btn_daily_journal.style.update(**default_style)
        if self.btn_habit_tracker.style:
            self.btn_habit_tracker.style.update(**default_style)

        if active_widget.style:
            active_widget.style.update(**active_style)

    def show_daily_journal(self, widget=None):
        self.update_nav_buttons(self.btn_daily_journal)
        self.clear_content()
        self.current_view = self.daily_journal_view
        self.content_box.add(self.daily_journal_view.get_content())
        self.daily_journal_view.refresh_list()

    def show_habit_tracker(self, widget=None):
        self.update_nav_buttons(self.btn_habit_tracker)
        self.clear_content()
        self.current_view = self.habit_tracker_view
        self.content_box.add(self.habit_tracker_view.get_content())
        self.habit_tracker_view.refresh_list()

    def show_edit_dialog(self, table_name, row_id, refresh_callback, widget=None):
        if table_name not in ['daily_journal', 'habits']:
            self.main_window.error_dialog("Error", f"Tabel tidak valid: {table_name}")
            return

        cursor = self.conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} WHERE id=?", (row_id,))
        row_data = cursor.fetchone()
        if not row_data:
            self.main_window.error_dialog("Oops!", "Data tidak ditemukan 😢")
            return

        dialog_box = toga.Box(style=Pack(direction=COLUMN, padding=20, background_color="#FFFDE7"))
        dialog_box.add(toga.Label('Ubah Informasi', style=Pack(font_size=16, padding_bottom=10)))

        inputs = []
        if table_name == 'daily_journal':
            labels = ['Tanggal:', 'Judul Cerita:', 'Isi Cerita:', 'Suasana Hati:']
            initial_values = row_data[1:]
            mood_options = ['Sangat Bahagia', 'Bahagia', 'Biasa Saja', 'Sedih', 'Sangat Sedih']
        elif table_name == 'habits':
            labels = ['Nama Kebiasaan:', 'Seberapa Sering?', 'Terakhir Dicatat:', 'Target:']
            initial_values = row_data[1:]
            frequency_options = ['Harian', 'Mingguan', 'Bulanan', 'Sesuai Kebutuhan']

        for i, label_text in enumerate(labels):
            field_box = toga.Box(style=Pack(direction=ROW, padding_bottom=5, alignment='center'))
            field_box.add(toga.Label(label_text, style=Pack(width=140)))

            if "Tanggal" in label_text:
                input_field = toga.DateInput(value=datetime.fromisoformat(initial_values[i]).date(), style=Pack(flex=1))
            elif "Hati" in label_text:
                input_field = toga.Selection(items=mood_options, value=initial_values[i], style=Pack(flex=1))
            elif "Sering" in label_text:
                input_field = toga.Selection(items=frequency_options, value=initial_values[i], style=Pack(flex=1))
            else:
                input_field = toga.TextInput(value=initial_values[i] or '', style=Pack(flex=1))

            field_box.add(input_field)
            dialog_box.add(field_box)
            inputs.append(input_field)

        def save_changes(widget):
            cursor = self.conn.cursor()
            try:
                values = [inp.value.isoformat() if hasattr(inp.value, 'isoformat') else inp.value for inp in inputs]
                if table_name == 'daily_journal':
                    cursor.execute("UPDATE daily_journal SET date=?, title=?, content=?, mood=? WHERE id=?",
                                   (*values, row_id))
                elif table_name == 'habits':
                    cursor.execute("UPDATE habits SET name=?, frequency=?, last_performed=?, target=? WHERE id=?",
                                   (*values, row_id))
                self.conn.commit()
                refresh_callback()
                self._close_dialog_and_restore_main_content()
                self.main_window.info_dialog('Berhasil', 'Data berhasil diperbarui ✨')
            except Exception as e:
                self.main_window.error_dialog('Error', str(e))

        btn_box = toga.Box(style=Pack(direction=ROW, padding_top=10, alignment='center'))
        btn_box.add(toga.Button('Simpan', on_press=save_changes, style=Pack(padding=5, flex=1)))
        btn_box.add(toga.Button('Batal', on_press=self._close_dialog_and_restore_main_content, style=Pack(padding=5, flex=1)))
        dialog_box.add(btn_box)
        self.main_window.content = dialog_box

    def _close_dialog_and_restore_main_content(self, widget=None):
        self.main_window.content = self.main_box
        if self.current_view:
            self.current_view.refresh_list()

def main():
    return LifeJournalApp()
