import json
import os
import time
import random
import csv
import webbrowser
from datetime import datetime, timedelta

from kivy.core.window import Window
from kivy.utils import platform
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.screenmanager import SlideTransition
from kivy.network.urlrequest import UrlRequest 
from kivy.core.audio import SoundLoader # <-- Native Kivy Audio

from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.toast import toast

DATA_FILE = "dictionary_memory.json"
STATS_FILE = "user_stats.json"
RECYCLE_FILE = "recycle_bin.json" 

def get_path(filename):
    try:
        app = MDApp.get_running_app()
        if app and app.user_data_dir:
            return os.path.join(app.user_data_dir, filename)
    except Exception: pass
    return filename

def load_words():
    path = get_path(DATA_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                for w, d in data.items():
                    if "mastery" not in d: d["mastery"] = 0
                return data
            except Exception: pass
    return {}

def save_words(data):
    path = get_path(DATA_FILE)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def load_recycle_bin():
    path = get_path(RECYCLE_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                current_time = time.time()
                return {w: d for w, d in data.items() if current_time - d.get("deleted_timestamp", current_time) <= 2592000}
            except Exception: pass
    return {}

def save_recycle_bin(data):
    path = get_path(RECYCLE_FILE)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

# 🟢 CRASH-PROOF SPEECH: Uses Google's web audio instead of phone's system voice
def speak_web(text):
    if not text: return
    url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={text.lower()}&tl=en&client=tw-ob"
    sound = SoundLoader.load(url)
    if sound:
        sound.play()

class AppLogic:
    @staticmethod
    def update_streak():
        stats = {"last_active": "", "streak": 0, "best_streak": 0}
        path = get_path(STATS_FILE)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try: stats = json.load(f)
                except Exception: pass
        today = datetime.now().date()
        last_date_str = stats.get("last_active", "")
        streak = stats.get("streak", 0)
        best = stats.get("best_streak", 0)
        if last_date_str:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            if today == last_date: pass 
            elif today == last_date + timedelta(days=1): streak += 1
            else: streak = 1 
        else: streak = 1
        if streak > best: best = streak
        stats["last_active"] = today.strftime("%Y-%m-%d")
        stats["streak"] = streak
        stats["best_streak"] = best
        with open(path, "w", encoding="utf-8") as f: json.dump(stats, f)
        return streak

def create_empty_state(text, icon="ghost-outline"):
    box = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(250), spacing=dp(10))
    box.add_widget(MDLabel(text="", size_hint_y=None, height=dp(40))) 
    icon_btn = MDIconButton(icon=icon, icon_size="80sp", pos_hint={"center_x": .5}, theme_text_color="Hint")
    box.add_widget(icon_btn)
    box.add_widget(MDLabel(text=text, halign="center", theme_text_color="Hint", font_style="H6"))
    return box

class ViewDictionaryScreen(MDScreen):
    web_dialog = None
    search_input_dialog = None
    active_filter = "All"
    def on_enter(self):
        streak = AppLogic.update_streak()
        if hasattr(self, 'ids') and 'streak_label' in self.ids:
            self.ids.streak_label.text = f"Streak: {streak} Days"
        self.refresh_list()
    def set_filter(self, category):
        self.active_filter = category
        self.refresh_list()
    def play_audio(self, word):
        speak_web(word)
    def search_word_web(self, word):
        if word: webbrowser.open(f"https://www.google.com/search?q=define+{word.lower()}")
    def open_web_search(self):
        if not self.web_dialog:
            self.search_input_dialog = MDTextField(hint_text="Type word to look up...")
            self.web_dialog = MDDialog(title="Google Web Search", type="custom", content_cls=self.search_input_dialog,
                buttons=[MDFlatButton(text="CLOSE", on_release=lambda x: self.web_dialog.dismiss()),
                MDRaisedButton(text="SEARCH WEB", md_bg_color=(0.2, 0.7, 0.4, 1), on_release=self.do_web_search)])
        self.search_input_dialog.text = ""
        self.web_dialog.open()
    def do_web_search(self, *args):
        word = self.search_input_dialog.text.strip()
        if word: webbrowser.open(f"https://www.google.com/search?q=define+{word}")
        self.web_dialog.dismiss()
    def delete_word_prompt(self, word_to_delete):
        word_to_delete = word_to_delete.lower()
        self.dialog = MDDialog(title="Move to Trash?", text=f"Delete '{word_to_delete.capitalize()}'?",
            buttons=[MDFlatButton(text="CANCEL", on_release=lambda x: self.dialog.dismiss()),
            MDRaisedButton(text="DELETE", md_bg_color=(0.8, 0.2, 0.2, 1), on_release=lambda x: self.execute_delete(word_to_delete))])
        self.dialog.open()
    def execute_delete(self, word_to_delete):
        self.dialog.dismiss()
        words = load_words()
        if word_to_delete in words:
            deleted_data = words.pop(word_to_delete)
            save_words(words)
            bin_data = load_recycle_bin()
            deleted_data['deleted_timestamp'] = time.time()
            bin_data[word_to_delete] = deleted_data
            save_recycle_bin(bin_data)
            toast(f"Moved to Trash")
            self.refresh_list()
    def edit_word(self, word_to_edit):
        word_to_edit = word_to_edit.lower()
        words = load_words()
        if word_to_edit in words:
            data = words[word_to_edit]
            app = MDApp.get_running_app()
            add_screen = app.root.get_screen('add')
            add_screen.editing_word = word_to_edit
            add_screen.ids.word_input.text = word_to_edit
            add_screen.ids.category_spinner.text = data['category']
            add_screen.ids.meaning_input.text = data['meaning']
            add_screen.ids.example_input.text = data['example']
            app.change_screen('add', direction='left')
    def refresh_list(self, *args):
        if not hasattr(self, 'ids') or 'words_container' not in self.ids: return
        self.ids.words_container.clear_widgets()
        words = load_words()
        if not words:
            self.ids.words_container.add_widget(create_empty_state("Your dictionary is empty!", "book-open-blank-variant"))
            return
        search_query = self.ids.search_input.text.strip().lower() if 'search_input' in self.ids else ""
        sort_mode = self.ids.sort_spinner.text if 'sort_spinner' in self.ids else "Latest"
        filtered = {}
        for w, d in words.items():
            if search_query and search_query not in w: continue
            if self.active_filter == "Struggling" and d.get('mastery', 0) >= 3: continue
            elif self.active_filter not in ["All", "Struggling"] and self.active_filter.lower() not in d.get('category', '').lower(): continue
            filtered[w] = d
        sorted_items = sorted(filtered.items(), key=lambda i: i[0]) if sort_mode == "Alphabetical" else sorted(filtered.items(), key=lambda i: i[1].get('timestamp', 0), reverse=True)
        from kivy.factory import Factory
        for word, data in sorted_items:
            card = Factory.WordCard()
            card.word_text = word.capitalize()
            card.category_text = data.get('category', 'Uncategorized')
            card.meaning_text = data.get('meaning', '')
            card.example_text = data.get('example', '')
            card.mastery_text = str(data.get('mastery', 0))
            self.ids.words_container.add_widget(card)

class RecycleBinScreen(MDScreen):
    def on_enter(self): self.refresh_bin()
    def restore_word(self, word_to_restore):
        bin_data = load_recycle_bin()
        if word_to_restore in bin_data:
            data = bin_data.pop(word_to_restore)
            save_recycle_bin(bin_data)
            words = load_words()
            words[word_to_restore] = data
            save_words(words)
            toast("Word Restored!")
            self.refresh_bin()
    def permanent_delete(self, word_to_delete):
        bin_data = load_recycle_bin()
        if word_to_delete in bin_data:
            del bin_data[word_to_delete]
            save_recycle_bin(bin_data)
            toast("Permanently Deleted")
            self.refresh_bin()
    def empty_bin(self):
        save_recycle_bin({})
        toast("Trash Emptied")
        self.refresh_bin()
    def refresh_bin(self):
        if not hasattr(self, 'ids') or 'bin_container' not in self.ids: return
        self.ids.bin_container.clear_widgets()
        bin_data = load_recycle_bin()
        if not bin_data:
            self.ids.bin_container.add_widget(create_empty_state("Recycle Bin is empty.", "delete-empty-outline"))
            return
        from kivy.factory import Factory
        for word, data in bin_data.items():
            card = Factory.RecycleCard()
            card.word_text = word.capitalize()
            card.category_text = data.get('category', 'N/A')
            days_left = 30 - int((time.time() - data.get('deleted_timestamp', time.time())) / 86400)
            card.days_left_text = f"{max(0, days_left)} days left"
            self.ids.bin_container.add_widget(card)

class AddWordScreen(MDScreen):
    editing_word = StringProperty("") 
    def magic_fetch(self):
        word = self.ids.word_input.text.strip().lower()
        if not word:
            toast("Type a word first!")
            return
        toast("Fetching meaning...")
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        UrlRequest(url, on_success=self._on_fetch_success, on_failure=self._on_fetch_fail, on_error=self._on_fetch_fail, timeout=5)
    def _on_fetch_success(self, request, result):
        try:
            data = result[0]
            meanings = data.get("meanings", [])
            pos, def_text, ex_text = "Uncategorized", "", ""
            if meanings:
                pos = meanings[0].get("partOfSpeech", "Uncategorized").capitalize()
                def_text = meanings[0]["definitions"][0].get("definition", "")
                for meaning in meanings:
                    for definition in meaning.get("definitions", []):
                        if definition.get("example"):
                            ex_text = definition["example"]
                            break
                    if ex_text: break
            self._update_ui(pos, def_text, ex_text)
        except Exception: self._on_fetch_fail(request, result)
    def _on_fetch_fail(self, request, result): toast("Word not found.")
    def _update_ui(self, pos, def_text, ex_text):
        if pos in self.ids.category_spinner.values: self.ids.category_spinner.text = pos
        self.ids.meaning_input.text = def_text
        self.ids.example_input.text = ex_text
        toast("Magic Fetch Complete!")
    def save_word_to_memory(self):
        word = self.ids.word_input.text.strip().lower()
        if not word or not self.ids.meaning_input.text:
            toast("Word and Meaning required.")
            return
        data = load_words()
        if self.editing_word and self.editing_word != word: data.pop(self.editing_word, None)
        old_data = data.get(word, {})
        data[word] = {"category": self.ids.category_spinner.text, "meaning": self.ids.meaning_input.text, "example": self.ids.example_input.text, "timestamp": old_data.get("timestamp", time.time()), "mastery": old_data.get("mastery", 0)}
        save_words(data)
        toast(f"'{word.capitalize()}' saved!")
        self.clear_inputs()
        MDApp.get_running_app().change_screen('view', direction='right')
    def clear_inputs(self):
        self.ids.word_input.text, self.ids.meaning_input.text, self.ids.example_input.text = "", "", ""
        self.ids.category_spinner.text = "Uncategorized"
        self.editing_word = ""

class DashboardScreen(MDScreen):
    total_words, mastered, struggling, streak_best = StringProperty("0"), StringProperty("0"), StringProperty("0"), StringProperty("0")
    def on_enter(self):
        words = load_words()
        self.total_words = str(len(words))
        self.mastered = str(sum(1 for d in words.values() if d.get('mastery', 0) >= 3))
        self.struggling = str(sum(1 for d in words.values() if d.get('mastery', 0) < 0))
        path = get_path(STATS_FILE)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try: self.streak_best = str(json.load(f).get("best_streak", 0))
                except: pass

class SettingsScreen(MDScreen):
    def export_csv(self):
        words, path = load_words(), os.path.join(os.environ.get('EXTERNAL_STORAGE', get_path('')), 'Download', 'dictionary.csv')
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Word', 'Category', 'Meaning', 'Example', 'Mastery'])
                for w, d in words.items(): writer.writerow([w, d.get('category'), d.get('meaning'), d.get('example'), d.get('mastery')])
            toast("Exported to Downloads!")
        except: toast("Export failed.")

class TestMenuScreen(MDScreen):
    def check_mcq_unlocked(self):
        if len(load_words()) < 5: toast("Save 5 words first!")
        else: MDApp.get_running_app().change_screen('mcq_test')

class FlashcardScreen(MDScreen):
    def on_enter(self):
        self.test_words = list(load_words().items())
        random.shuffle(self.test_words)
        self.current_idx = 0
        self.show_current_word()
    def show_current_word(self):
        if not self.test_words or self.current_idx >= len(self.test_words):
            self.ids.test_word_label.text, self.ids.test_meaning_label.text = "Done!", "Finished!"
            return
        self.ids.test_word_label.text = self.test_words[self.current_idx][0].capitalize()
        self.ids.test_meaning_label.text = "?"
    def play_audio(self): speak_web(self.test_words[self.current_idx][0])
    def reveal_meaning(self):
        data = self.test_words[self.current_idx][1]
        self.ids.test_meaning_label.text = f"Meaning:\n{data.get('meaning')}"
    def next_word(self):
        self.current_idx += 1
        self.show_current_word()

class MCQScreen(MDScreen):
    def on_enter(self):
        self.all_words = load_words()
        self.word_list = list(self.all_words.keys())
        self.next_question()
    def next_question(self):
        self.ids.next_btn.disabled = True
        self.current_word = random.choice(self.word_list)
        correct = self.all_words[self.current_word]['meaning']
        wrong = [self.all_words[w]['meaning'] for w in self.word_list if w != self.current_word]
        self.options = random.sample([correct] + random.sample(wrong, min(len(wrong), 4)), min(len(wrong)+1, 5))
        random.shuffle(self.options)
        self.ids.mcq_word_label.text = self.current_word.capitalize()
        btns = [self.ids.btn1, self.ids.btn2, self.ids.btn3, self.ids.btn4, self.ids.btn5]
        for i, btn in enumerate(btns):
            btn.text = self.options[i] if i < len(self.options) else ""
            btn.disabled = not btn.text
            btn.md_bg_color = app.theme_cls.primary_color
    def play_audio(self): speak_web(self.current_word)
    def check_answer(self, btn):
        correct = self.all_words[self.current_word]['meaning']
        if btn.text == correct:
            btn.md_bg_color, self.all_words[self.current_word]['mastery'] = [0.2, 0.8, 0.2, 1], self.all_words[self.current_word].get('mastery', 0) + 1
        else:
            btn.md_bg_color, self.all_words[self.current_word]['mastery'] = [0.8, 0.2, 0.2, 1], self.all_words[self.current_word].get('mastery', 0) - 1
        save_words(self.all_words)
        self.ids.next_btn.disabled = False

class SelfDictionaryApp(MDApp):
    def build(self):
        Window.bind(on_keyboard=self.hook_keyboard)
        return Builder.load_file("main.kv")
    def on_start(self): self.change_theme("Police")
    def change_theme(self, name):
        themes = {"White (Sadabahar)": ("Light", "Blue"), "Dark": ("Dark", "DeepPurple"), "Police": ("Dark", "Indigo")}
        self.theme_cls.theme_style, self.theme_cls.primary_palette = themes.get(name, ("Dark", "Indigo"))
    def change_screen(self, name, direction='left'):
        self.root.transition = SlideTransition(direction=direction)
        self.root.current = name
    def hook_keyboard(self, window, key, *args):
        if key == 27:
            if self.root.current != 'view': self.change_screen('view', 'right')
            return True
        return False

if __name__ == "__main__":
    SelfDictionaryApp().run()
