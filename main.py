import json, os, time, random, csv, webbrowser
from datetime import datetime, timedelta

from kivy.core.window import Window
from kivy.utils import platform
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.screenmanager import SlideTransition
from kivy.network.urlrequest import UrlRequest 
from kivy.core.audio import SoundLoader 

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

def get_path(filename):
    try:
        app = MDApp.get_running_app()
        if app and app.user_data_dir:
            return os.path.join(app.user_data_dir, filename)
    except: pass
    return filename

def load_words():
    path = get_path(DATA_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: pass
    return {}

def save_words(data):
    with open(get_path(DATA_FILE), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def speak_web(text):
    if not text: return
    # Android 16 handles this as a media stream, preventing hardware-bridge crashes
    url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={text.lower()}&tl=en&client=tw-ob"
    sound = SoundLoader.load(url)
    if sound:
        sound.play()

class ViewDictionaryScreen(MDScreen):
    def on_enter(self):
        self.refresh_list()

    def refresh_list(self):
        if not hasattr(self, 'ids') or 'words_container' not in self.ids: return
        self.ids.words_container.clear_widgets()
        words = load_words()
        if not words:
            self.ids.words_container.add_widget(MDLabel(text="No words saved yet!", halign="center"))
            return
        from kivy.factory import Factory
        for word, data in sorted(words.items()):
            card = Factory.WordCard()
            card.word_text = word.capitalize()
            card.meaning_text = data.get('meaning', '')
            self.ids.words_container.add_widget(card)

class AddWordScreen(MDScreen):
    editing_word = StringProperty("") 
    
    def magic_fetch(self):
        word = self.ids.word_input.text.strip().lower()
        if not word: 
            toast("Enter a word first")
            return
        toast("Fetching...")
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        UrlRequest(url, on_success=self._on_success, on_error=self._on_fail)
        
    def _on_success(self, req, res):
        if res and isinstance(res, list):
            self.ids.meaning_input.text = res[0]['meanings'][0]['definitions'][0]['definition']
            toast("Meaning found!")

    def _on_fail(self, req, res):
        toast("Word not found")

    def save_word_to_memory(self):
        word = self.ids.word_input.text.strip().lower()
        meaning = self.ids.meaning_input.text.strip()
        if word and meaning:
            words = load_words()
            words[word] = {"meaning": meaning, "timestamp": time.time(), "mastery": 0}
            save_words(words)
            self.ids.word_input.text = ""
            self.ids.meaning_input.text = ""
            MDApp.get_running_app().change_screen('view')
            toast("Saved!")

class MCQScreen(MDScreen):
    def on_enter(self):
        self.words = load_words()
        if len(self.words) < 2:
            toast("Add more words for MCQ")
            MDApp.get_running_app().change_screen('view')
            return
        self.next_q()

    def next_q(self):
        self.current = random.choice(list(self.words.keys()))
        self.ids.mcq_word_label.text = self.current.capitalize()
        correct = self.words[self.current]['meaning']
        all_meanings = [d['meaning'] for d in self.words.values() if d['meaning'] != correct]
        wrong = random.sample(all_meanings, min(len(all_meanings), 4))
        options = [correct] + wrong
        random.shuffle(options)
        
        for i in range(1, 6):
            btn = getattr(self.ids, f'btn{i}')
            if i-1 < len(options):
                btn.text = options[i-1]
                btn.disabled = False
                btn.opacity = 1
            else:
                btn.disabled = True
                btn.opacity = 0

    def check(self, btn):
        if btn.text == self.words[self.current]['meaning']:
            toast("Correct!")
            self.next_q()
        else:
            toast("Try again!")

    def play_audio(self):
        speak_web(self.current)

class SelfDictionaryApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Indigo"
        Window.softinput_mode = "below_target"
        return Builder.load_file("main.kv")

    def change_screen(self, name):
        self.root.current = name

if __name__ == "__main__":
    SelfDictionaryApp().run()

