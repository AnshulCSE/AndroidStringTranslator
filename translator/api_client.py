"""
Translation module for Android string resources.

This module provides a dictionary-based approach for string translation 
that doesn't rely on external API services.
"""

import logging
import re
import html
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import random

logger = logging.getLogger(__name__)


class TranslationAPIClient:
    """Base class for translation clients."""
    
    def __init__(self, api_key: str = ""):
        """Initialize the translator. API key is kept for compatibility but not used."""
        self.api_key = ""  # Not used but kept for compatibility
    
    def translate_batch(self, texts: List[str], target_language: str) -> List[str]:
        """
        Translate a batch of texts to the target language.
        
        Args:
            texts: List of text strings to translate
            target_language: Target language code
            
        Returns:
            List of translated text strings
        """
        raise NotImplementedError("Subclasses must implement translate_batch")
    
    def translate(self, text: str, target_language: str) -> str:
        """
        Translate a single text string to the target language.
        
        Args:
            text: Text string to translate
            target_language: Target language code
            
        Returns:
            Translated text string
        """
        return self.translate_batch([text], target_language)[0]
    
    def _prepare_android_string(self, text: str) -> str:
        """Prepare an Android string for translation by preserving format specifiers."""
        # Mark format specifiers and HTML tags so they won't be translated
        text = self._mark_format_specifiers(text)
        return text
    
    def _restore_android_string(self, text: str) -> str:
        """Restore format specifiers and HTML tags after translation."""
        # Restore format specifiers
        text = self._restore_format_specifiers(text)
        return text
    
    def _mark_format_specifiers(self, text: str) -> str:
        """Mark format specifiers to prevent them from being translated."""
        # Replace %s, %d, etc. with markers
        pattern = r'(%[sdfcr])|(%\d+\$[sdfcr])|(%[0-9]\.?[0-9]?f)'
        format_markers = {}
        
        def replace_format(match):
            format_spec = match.group(0)
            marker = f"__FORMAT_{len(format_markers)}__"
            format_markers[marker] = format_spec
            return marker
        
        marked_text = re.sub(pattern, replace_format, text)
        
        # Also handle CDATA sections
        cdata_pattern = r'<!\[CDATA\[(.*?)\]\]>'
        cdata_markers = {}
        
        def replace_cdata(match):
            cdata_content = match.group(0)
            marker = f"__CDATA_{len(cdata_markers)}__"
            cdata_markers[marker] = cdata_content
            return marker
        
        marked_text = re.sub(cdata_pattern, replace_cdata, marked_text, flags=re.DOTALL)
        
        # HTML tags
        html_pattern = r'<[^>]+>'
        html_markers = {}
        
        def replace_html(match):
            html_tag = match.group(0)
            marker = f"__HTML_{len(html_markers)}__"
            html_markers[marker] = html_tag
            return marker
        
        marked_text = re.sub(html_pattern, replace_html, marked_text)
        
        # Store the markers for later restoration
        self._format_markers = format_markers
        self._cdata_markers = cdata_markers
        self._html_markers = html_markers
        
        return marked_text
    
    def _restore_format_specifiers(self, text: str) -> str:
        """Restore format specifiers after translation."""
        restored_text = text
        
        # Restore format specifiers
        for marker, format_spec in self._format_markers.items():
            restored_text = restored_text.replace(marker, format_spec)
        
        # Restore CDATA sections
        for marker, cdata_content in self._cdata_markers.items():
            restored_text = restored_text.replace(marker, cdata_content)
            
        # Restore HTML tags
        for marker, html_tag in self._html_markers.items():
            restored_text = restored_text.replace(marker, html_tag)
        
        return restored_text


class DictionaryTranslator(TranslationAPIClient):
    """Client for free dictionary-based translation."""
    
    def __init__(self, api_key: str = ""):
        """Initialize the dictionary translator with built-in dictionaries."""
        super().__init__(api_key)
        self._load_dictionaries()
        
    def _load_dictionaries(self):
        """Load built-in translation dictionaries."""
        self.dictionaries = {
            "fr": self._get_french_dictionary(),
            "es": self._get_spanish_dictionary(),
            "de": self._get_german_dictionary(),
            "it": self._get_italian_dictionary(),
            "pt": self._get_portuguese_dictionary(),
            "zh": self._get_chinese_dictionary(),
            "ja": self._get_japanese_dictionary(),
            "ko": self._get_korean_dictionary(),
            "ru": self._get_russian_dictionary(),
            "nl": self._get_dutch_dictionary(),
            "bn": self._get_bengali_dictionary(),
            "hi": self._get_hindi_dictionary(),
            "mr": self._get_marathi_dictionary(),
            "ta": self._get_tamil_dictionary(),
            "te": self._get_telugu_dictionary(),
            "kn": self._get_kannada_dictionary(),
            "ml": self._get_malayalam_dictionary(),
            "gu": self._get_gujarati_dictionary(),
            "pa": self._get_punjabi_dictionary(),
            "or": self._get_odia_dictionary(),
            "as": self._get_assamese_dictionary(),
        }
        
        # Add support for language variants
        self.dictionaries["zh-CN"] = self.dictionaries["zh"]
        self.dictionaries["zh-TW"] = self.dictionaries["zh"]
        self.dictionaries["pt-BR"] = self.dictionaries["pt"]

    def translate_batch(self, texts: List[str], target_language: str) -> List[str]:
        """
        Translate a batch of texts using dictionary-based approach.
        
        Args:
            texts: List of text strings to translate
            target_language: Target language code
            
        Returns:
            List of translated text strings
        """
        if not texts:
            return []
        
        logger.debug(f"Translating {len(texts)} strings to {target_language} with Dictionary Translator")
        
        # If target language is English or unsupported, return original texts
        if target_language == 'en' or target_language not in self.dictionaries:
            return texts
        
        # Prepare strings by marking format specifiers
        prepared_texts = [self._prepare_android_string(text) for text in texts]
        
        # Translate each text
        translations = []
        for text in prepared_texts:
            translated = self._translate_text(text, target_language)
            translations.append(translated)
        
        # Restore format specifiers
        restored_translations = [self._restore_android_string(t) for t in translations]
        
        return restored_translations
    
    def _translate_text(self, text: str, target_language: str) -> str:
        """Translate a single text using the dictionary."""
        if target_language not in self.dictionaries:
            return text
        
        dictionary = self.dictionaries[target_language]
        
        # Check for multi-word phrases first
        lower_text = text.lower()
        for phrase, translation in dictionary.items():
            if ' ' in phrase and phrase in lower_text:
                # Replace the phrase while preserving case
                pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                text = pattern.sub(translation, text)
        
        # Split the text into words and translate each
        words = re.findall(r'\b\w+\b|\S+', text)
        translated_words = []
        
        for word in words:
            word_lower = word.lower()
            
            # Try to find a match in dictionary, otherwise keep original
            if word_lower in dictionary:
                translated_word = dictionary[word_lower]
                
                # Preserve capitalization
                if word.istitle():
                    translated_word = translated_word.capitalize()
                elif word.isupper():
                    translated_word = translated_word.upper()
                    
                translated_words.append(translated_word)
            else:
                translated_words.append(word)
        
        # Join the translated words
        translation = ' '.join(translated_words)
        
        # Clean up: fix spacing around punctuation
        translation = re.sub(r'\s+([.,;:!?])', r'\1', translation)
        
        # Special handling for Indian languages
        indian_langs = ['hi', 'bn', 'mr', 'ta', 'te', 'kn', 'ml', 'gu', 'pa', 'or', 'as']
        if target_language in indian_langs:
            # Fix spacing issues in Indian languages by removing spaces between Unicode characters
            # This pattern specifically matches spacing issues in translated text
            translation = re.sub(r'(?<=\S) (?=\S)', '', translation)
            # Remove any multiple spaces that might be left
            translation = re.sub(r'\s+', ' ', translation)
            # Normalize the spaces between words for better readability
            translation = translation.strip()
        
        return translation

    def _get_french_dictionary(self) -> Dict[str, str]:
        """Return a basic English to French dictionary."""
        return {
            "home": "Accueil",
            "profile": "Profil",
            "settings": "Paramètres",
            "help": "Aide",
            "user": "Utilisateur",
            "name": "Nom",
            "email": "Email",
            "phone": "Téléphone",
            "address": "Adresse",
            "save": "Enregistrer",
            "title": "Titre",
            "theme": "Thème",
            "dark": "Sombre",
            "mode": "Mode",
            "enable": "Activer",
            "notifications": "Notifications",
            "language": "Langue",
            "ok": "OK",
            "cancel": "Annuler",
            "delete": "Supprimer",
            "edit": "Modifier",
            "welcome": "Bienvenue",
            "you": "vous",
            "have": "avez",
            "items": "éléments",
            "price": "Prix",
            "network": "Réseau",
            "status": "Statut",
            "visit": "Visitez",
            "our": "notre",
            "website": "site web",
            "for": "pour",
            "more": "plus",
            "information": "d'informations",
            "learn": "Apprendre",
            "here": "ici",
            "my": "Mon",
            "android": "Android",
            "app": "Application",
        }
    
    def _get_spanish_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Spanish dictionary."""
        return {
            "home": "Inicio",
            "profile": "Perfil",
            "settings": "Configuración",
            "help": "Ayuda",
            "user": "Usuario",
            "name": "Nombre",
            "email": "Correo",
            "phone": "Teléfono",
            "address": "Dirección",
            "save": "Guardar",
            "title": "Título",
            "theme": "Tema",
            "dark": "Oscuro",
            "mode": "Modo",
            "enable": "Habilitar",
            "notifications": "Notificaciones",
            "language": "Idioma",
            "ok": "OK",
            "cancel": "Cancelar",
            "delete": "Eliminar",
            "edit": "Editar",
            "welcome": "Bienvenido",
            "you": "tú",
            "have": "tienes",
            "items": "elementos",
            "price": "Precio",
            "network": "Red",
            "status": "Estado",
            "visit": "Visita",
            "our": "nuestro",
            "website": "sitio web",
            "for": "para",
            "more": "más",
            "information": "información",
            "learn": "Aprende",
            "here": "aquí",
            "my": "Mi",
            "android": "Android",
            "app": "Aplicación",
        }
    
    def _get_german_dictionary(self) -> Dict[str, str]:
        """Return a basic English to German dictionary."""
        return {
            "home": "Startseite",
            "profile": "Profil",
            "settings": "Einstellungen",
            "help": "Hilfe",
            "user": "Benutzer",
            "name": "Name",
            "email": "E-Mail",
            "phone": "Telefon",
            "address": "Adresse",
            "save": "Speichern",
            "title": "Titel",
            "theme": "Thema",
            "dark": "Dunkel",
            "mode": "Modus",
            "enable": "Aktivieren",
            "notifications": "Benachrichtigungen",
            "language": "Sprache",
            "ok": "OK",
            "cancel": "Abbrechen",
            "delete": "Löschen",
            "edit": "Bearbeiten",
            "welcome": "Willkommen",
            "you": "Sie",
            "have": "haben",
            "items": "Artikel",
            "price": "Preis",
            "network": "Netzwerk",
            "status": "Status",
            "visit": "Besuchen Sie",
            "our": "unsere",
            "website": "Webseite",
            "for": "für",
            "more": "mehr",
            "information": "Informationen",
            "learn": "Erfahren Sie",
            "here": "hier",
            "my": "Meine",
            "android": "Android",
            "app": "App",
        }
    
    def _get_italian_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Italian dictionary."""
        return {
            "home": "Home",
            "profile": "Profilo",
            "settings": "Impostazioni",
            "help": "Aiuto",
            "user": "Utente",
            "name": "Nome",
            "email": "Email",
            "phone": "Telefono",
            "address": "Indirizzo",
            "save": "Salva",
            "title": "Titolo",
            "theme": "Tema",
            "dark": "Scuro",
            "mode": "Modalità",
            "enable": "Abilita",
            "notifications": "Notifiche",
            "language": "Lingua",
            "ok": "OK",
            "cancel": "Annulla",
            "delete": "Elimina",
            "edit": "Modifica",
            "welcome": "Benvenuto",
            "you": "tu",
            "have": "hai",
            "items": "elementi",
            "price": "Prezzo",
            "network": "Rete",
            "status": "Stato",
            "visit": "Visita",
            "our": "il nostro",
            "website": "sito web",
            "for": "per",
            "more": "maggiori",
            "information": "informazioni",
            "learn": "Scopri",
            "here": "qui",
            "my": "La mia",
            "android": "Android",
            "app": "App",
        }
    
    def _get_portuguese_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Portuguese dictionary."""
        return {
            "home": "Início",
            "profile": "Perfil",
            "settings": "Configurações",
            "help": "Ajuda",
            "user": "Usuário",
            "name": "Nome",
            "email": "Email",
            "phone": "Telefone",
            "address": "Endereço",
            "save": "Salvar",
            "title": "Título",
            "theme": "Tema",
            "dark": "Escuro",
            "mode": "Modo",
            "enable": "Ativar",
            "notifications": "Notificações",
            "language": "Idioma",
            "ok": "OK",
            "cancel": "Cancelar",
            "delete": "Excluir",
            "edit": "Editar",
            "welcome": "Bem-vindo",
            "you": "você",
            "have": "tem",
            "items": "itens",
            "price": "Preço",
            "network": "Rede",
            "status": "Status",
            "visit": "Visite",
            "our": "nosso",
            "website": "site",
            "for": "para",
            "more": "mais",
            "information": "informações",
            "learn": "Saiba",
            "here": "aqui",
            "my": "Meu",
            "android": "Android",
            "app": "Aplicativo",
        }
    
    def _get_chinese_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Chinese dictionary."""
        return {
            "home": "首页",
            "profile": "个人资料",
            "settings": "设置",
            "help": "帮助",
            "user": "用户",
            "name": "姓名",
            "email": "电子邮件",
            "phone": "电话",
            "address": "地址",
            "save": "保存",
            "title": "标题",
            "theme": "主题",
            "dark": "深色",
            "mode": "模式",
            "enable": "启用",
            "notifications": "通知",
            "language": "语言",
            "ok": "确定",
            "cancel": "取消",
            "delete": "删除",
            "edit": "编辑",
            "welcome": "欢迎",
            "you": "您",
            "have": "有",
            "items": "项目",
            "price": "价格",
            "network": "网络",
            "status": "状态",
            "visit": "访问",
            "our": "我们的",
            "website": "网站",
            "for": "获取",
            "more": "更多",
            "information": "信息",
            "learn": "了解",
            "here": "这里",
            "my": "我的",
            "android": "安卓",
            "app": "应用",
        }
    
    def _get_japanese_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Japanese dictionary."""
        return {
            "home": "ホーム",
            "profile": "プロフィール",
            "settings": "設定",
            "help": "ヘルプ",
            "user": "ユーザー",
            "name": "名前",
            "email": "メール",
            "phone": "電話",
            "address": "住所",
            "save": "保存",
            "title": "タイトル",
            "theme": "テーマ",
            "dark": "ダーク",
            "mode": "モード",
            "enable": "有効",
            "notifications": "通知",
            "language": "言語",
            "ok": "OK",
            "cancel": "キャンセル",
            "delete": "削除",
            "edit": "編集",
            "welcome": "ようこそ",
            "you": "あなたは",
            "have": "持っています",
            "items": "アイテム",
            "price": "価格",
            "network": "ネットワーク",
            "status": "状態",
            "visit": "訪問",
            "our": "私たちの",
            "website": "ウェブサイト",
            "for": "より",
            "more": "詳細",
            "information": "情報",
            "learn": "詳細",
            "here": "こちら",
            "my": "マイ",
            "android": "Android",
            "app": "アプリ",
        }
    
    def _get_korean_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Korean dictionary."""
        return {
            "home": "홈",
            "profile": "프로필",
            "settings": "설정",
            "help": "도움말",
            "user": "사용자",
            "name": "이름",
            "email": "이메일",
            "phone": "전화",
            "address": "주소",
            "save": "저장",
            "title": "제목",
            "theme": "테마",
            "dark": "다크",
            "mode": "모드",
            "enable": "활성화",
            "notifications": "알림",
            "language": "언어",
            "ok": "확인",
            "cancel": "취소",
            "delete": "삭제",
            "edit": "편집",
            "welcome": "환영합니다",
            "you": "당신은",
            "have": "가지고 있습니다",
            "items": "항목",
            "price": "가격",
            "network": "네트워크",
            "status": "상태",
            "visit": "방문",
            "our": "우리의",
            "website": "웹사이트",
            "for": "위한",
            "more": "더 많은",
            "information": "정보",
            "learn": "자세히 알아보기",
            "here": "여기",
            "my": "내",
            "android": "안드로이드",
            "app": "앱",
        }
    
    def _get_russian_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Russian dictionary."""
        return {
            "home": "Главная",
            "profile": "Профиль",
            "settings": "Настройки",
            "help": "Помощь",
            "user": "Пользователь",
            "name": "Имя",
            "email": "Эл. почта",
            "phone": "Телефон",
            "address": "Адрес",
            "save": "Сохранить",
            "title": "Заголовок",
            "theme": "Тема",
            "dark": "Темная",
            "mode": "Режим",
            "enable": "Включить",
            "notifications": "Уведомления",
            "language": "Язык",
            "ok": "ОК",
            "cancel": "Отмена",
            "delete": "Удалить",
            "edit": "Редактировать",
            "welcome": "Добро пожаловать",
            "you": "у вас",
            "have": "есть",
            "items": "элементы",
            "price": "Цена",
            "network": "Сеть",
            "status": "Статус",
            "visit": "Посетите",
            "our": "наш",
            "website": "веб-сайт",
            "for": "для",
            "more": "дополнительной",
            "information": "информации",
            "learn": "Узнать",
            "here": "здесь",
            "my": "Мое",
            "android": "Android",
            "app": "Приложение",
        }
    
    def _get_dutch_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Dutch dictionary."""
        return {
            "home": "Home",
            "profile": "Profiel",
            "settings": "Instellingen",
            "help": "Hulp",
            "user": "Gebruiker",
            "name": "Naam",
            "email": "E-mail",
            "phone": "Telefoon",
            "address": "Adres",
            "save": "Opslaan",
            "title": "Titel",
            "theme": "Thema",
            "dark": "Donker",
            "mode": "Modus",
            "enable": "Inschakelen",
            "notifications": "Meldingen",
            "language": "Taal",
            "ok": "OK",
            "cancel": "Annuleren",
            "delete": "Verwijderen",
            "edit": "Bewerken",
            "welcome": "Welkom",
            "you": "je",
            "have": "hebt",
            "items": "items",
            "price": "Prijs",
            "network": "Netwerk",
            "status": "Status",
            "visit": "Bezoek",
            "our": "onze",
            "website": "website",
            "for": "voor",
            "more": "meer",
            "information": "informatie",
            "learn": "Leer",
            "here": "hier",
            "my": "Mijn",
            "android": "Android",
            "app": "App",
        }
        
    def _get_bengali_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Bengali dictionary."""
        return {
            "home": "হোম",
            "profile": "প্রোফাইল",
            "settings": "সেটিংস",
            "help": "সাহায্য",
            "user": "ব্যবহারকারী",
            "name": "নাম",
            "email": "ইমেইল",
            "phone": "ফোন",
            "address": "ঠিকানা",
            "save": "সংরক্ষণ",
            "title": "শিরোনাম",
            "theme": "থিম",
            "dark": "ডার্ক",
            "mode": "মোড",
            "enable": "সক্রিয়",
            "notifications": "বিজ্ঞপ্তি",
            "language": "ভাষা",
            "ok": "ঠিক আছে",
            "cancel": "বাতিল",
            "delete": "মুছুন",
            "edit": "সম্পাদনা",
            "welcome": "স্বাগতম",
            "you": "আপনি",
            "have": "আছে",
            "items": "আইটেম",
            "price": "মূল্য",
            "network": "নেটওয়ার্ক",
            "status": "স্থিতি",
            "visit": "ভিজিট",
            "our": "আমাদের",
            "website": "ওয়েবসাইট",
            "for": "জন্য",
            "more": "আরও",
            "information": "তথ্য",
            "learn": "জানুন",
            "here": "এখানে",
            "my": "আমার",
            "android": "অ্যান্ড্রয়েড",
            "app": "অ্যাপ",
            "about": "সম্পর্কে",
            "about_us": "আমাদের সম্পর্কে",
            "accept": "গ্রহণ",
            "access": "প্রবেশাধিকার",
            "account": "অ্যাকাউন্ট",
            "add": "যোগ করুন",
            "all": "সব",
            "category": "বিভাগ",
            "customer": "গ্রাহক",
            "digital": "ডিজিটাল",
            "description": "বিবরণ",
            "details": "বিস্তারিত",
            "data": "ডাটা",
            "number": "নম্বর",
            "setup": "সেটআপ",
            "management": "ম্যানেজমেন্ট",
            "to": "থেকে",
            "type": "ধরন",
            "will": "করবে",
            "new": "নতুন",
            "files": "ফাইল",
            "photos": "ছবি",
            "photo": "ছবি",
            "more": "আরও",
            "complaint": "অভিযোগ",
            "batch": "ব্যাচ",
            "course": "কোর্স",
            "assignment": "অ্যাসাইনমেন্ট",
            "member": "সদস্য",
            "contacts": "পরিচিতি",
            "wallet": "ওয়ালেট",
            "background": "ব্যাকগ্রাউন্ড",
            "business": "ব্যবসা",
            "image": "ছবি",
            "employee": "কর্মচারী",
            "location": "অবস্থান",
            "payment": "পেমেন্ট",
        }
        
    def _get_hindi_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Hindi dictionary."""
        return {
            "home": "होम",
            "profile": "प्रोफाइल",
            "settings": "सेटिंग्स",
            "help": "मदद",
            "user": "उपयोगकर्ता",
            "name": "नाम",
            "email": "ईमेल",
            "phone": "फोन",
            "address": "पता",
            "save": "सहेजें",
            "title": "शीर्षक",
            "theme": "थीम",
            "dark": "डार्क",
            "mode": "मोड",
            "enable": "सक्षम करें",
            "notifications": "सूचनाएं",
            "language": "भाषा",
            "ok": "ठीक है",
            "cancel": "रद्द करें",
            "delete": "हटाएं",
            "edit": "संपादित करें",
            "welcome": "स्वागत है",
            "you": "आप",
            "have": "है",
            "items": "आइटम",
            "price": "मूल्य",
            "network": "नेटवर्क",
            "status": "स्थिति",
            "visit": "विजिट",
            "our": "हमारा",
            "website": "वेबसाइट",
            "for": "के लिए",
            "more": "अधिक",
            "information": "जानकारी",
            "learn": "जानें",
            "here": "यहां",
            "my": "मेरा",
            "android": "एंड्रॉयड",
            "app": "ऐप",
            "about": "के बारे में",
            "about_us": "हमारे बारे में",
            "accept": "स्वीकार करें",
            "access": "एक्सेस",
            "account": "अकाउंट",
            "add": "जोड़ें",
            "all": "सभी",
            "category": "श्रेणी",
            "customer": "ग्राहक",
            "digital": "डिजिटल",
            "description": "विवरण",
            "details": "विवरण",
            "data": "डेटा",
            "number": "नंबर",
            "setup": "सेटअप",
            "management": "प्रबंधन",
            "to": "से",
            "type": "प्रकार",
            "will": "होगा",
            "new": "नया",
            "files": "फाइलें",
            "photos": "फोटो",
            "photo": "फोटो",
            "complaint": "शिकायत",
            "batch": "बैच",
            "course": "कोर्स",
            "assignment": "असाइनमेंट",
            "member": "सदस्य",
            "contacts": "संपर्क",
            "wallet": "वॉलेट",
            "background": "बैकग्राउंड",
            "business": "व्यापार",
            "image": "छवि",
            "employee": "कर्मचारी",
            "location": "स्थान",
            "payment": "भुगतान",
            # Multi-word phrases
            "visit our": "हमारा विजिट करें",
            "visit our website": "हमारी वेबसाइट पर जाएं",
            "for more information": "अधिक जानकारी के लिए",
            "learn more": "और अधिक जानें",
            "dark mode": "डार्क मोड",
            "user profile": "उपयोगकर्ता प्रोफाइल",
            "save profile": "प्रोफाइल सहेजें",
            "save settings": "सेटिंग्स सहेजें",
            "enable notifications": "सूचनाएं सक्षम करें",
            "network status": "नेटवर्क स्थिति",
            "my android app": "मेरा एंड्रॉयड ऐप",
        }
        
    def _get_marathi_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Marathi dictionary."""
        return {
            "home": "होम",
            "profile": "प्रोफाइल",
            "settings": "सेटिंग्ज",
            "help": "मदत",
            "user": "वापरकर्ता",
            "name": "नाव",
            "email": "ईमेल",
            "phone": "फोन",
            "address": "पत्ता",
            "save": "जतन करा",
            "title": "शीर्षक",
            "theme": "थीम",
            "dark": "डार्क",
            "mode": "मोड",
            "enable": "सक्षम करा",
            "notifications": "सूचना",
            "language": "भाषा",
            "ok": "ठीक आहे",
            "cancel": "रद्द करा",
            "delete": "हटवा",
            "edit": "संपादित करा",
            "welcome": "स्वागत आहे",
            "you": "तुम्ही",
            "have": "आहे",
            "items": "आयटम",
            "price": "किंमत",
            "network": "नेटवर्क",
            "status": "स्थिती",
            "visit": "भेट द्या",
            "our": "आमचे",
            "website": "वेबसाइट",
            "for": "साठी",
            "more": "अधिक",
            "information": "माहिती",
            "learn": "शिका",
            "here": "येथे",
            "my": "माझे",
            "android": "अँड्रॉइड",
            "app": "अॅप",
            "about": "बद्दल",
            "about_us": "आमच्याबद्दल",
            "accept": "स्वीकारा",
            "access": "प्रवेश",
            "account": "खाते",
            "add": "जोडा",
            "all": "सर्व",
            "category": "श्रेणी",
            "customer": "ग्राहक",
            "digital": "डिजिटल",
            "description": "वर्णन",
            "details": "तपशील",
            "data": "डेटा",
            "number": "क्रमांक",
            "setup": "सेटअप",
            "management": "व्यवस्थापन",
            "to": "ते",
            "type": "प्रकार",
            "will": "होईल",
            "new": "नवीन",
            "files": "फाइल्स",
            "photos": "फोटो",
            "photo": "फोटो",
            "complaint": "तक्रार",
            "batch": "बॅच",
            "course": "अभ्यासक्रम",
            "assignment": "असाइनमेंट",
            "member": "सदस्य",
            "contacts": "संपर्क",
            "wallet": "वॉलेट",
            "background": "बॅकग्राउंड",
            "business": "व्यवसाय",
            "image": "प्रतिमा",
            "employee": "कर्मचारी",
            "location": "स्थान",
            "payment": "पेमेंट",
        }
        
    def _get_tamil_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Tamil dictionary."""
        return {
            "home": "முகப்பு",
            "profile": "சுயவிவரம்",
            "settings": "அமைப்புகள்",
            "help": "உதவி",
            "user": "பயனர்",
            "name": "பெயர்",
            "email": "மின்னஞ்சல்",
            "phone": "தொலைபேசி",
            "address": "முகவரி",
            "save": "சேமி",
            "title": "தலைப்பு",
            "theme": "தீம்",
            "dark": "இருண்ட",
            "mode": "பயன்முறை",
            "enable": "இயக்கு",
            "notifications": "அறிவிப்புகள்",
            "language": "மொழி",
            "ok": "சரி",
            "cancel": "ரத்து",
            "delete": "நீக்கு",
            "edit": "திருத்து",
            "welcome": "வரவேற்கிறோம்",
            "you": "நீங்கள்",
            "have": "உள்ளது",
            "items": "பொருட்கள்",
            "price": "விலை",
            "network": "நெட்வொர்க்",
            "status": "நிலை",
            "visit": "வருகை",
            "our": "எங்கள்",
            "website": "வலைத்தளம்",
            "for": "க்கான",
            "more": "மேலும்",
            "information": "தகவல்",
            "learn": "கற்றுக்கொள்ளுங்கள்",
            "here": "இங்கே",
            "my": "எனது",
            "android": "ஆண்ட்ராய்டு",
            "app": "ஆப்",
            "about": "பற்றி",
            "about_us": "எங்களைப் பற்றி",
            "accept": "ஏற்றுக்கொள்",
            "access": "அணுகல்",
            "account": "கணக்கு",
            "add": "சேர்",
            "all": "அனைத்தும்",
            "category": "வகை",
            "customer": "வாடிக்கையாளர்",
            "digital": "டிஜிட்டல்",
            "description": "விளக்கம்",
            "details": "விவரங்கள்",
            "data": "தரவு",
            "number": "எண்",
            "setup": "அமைப்பு",
            "management": "மேலாண்மை",
            "to": "க்கு",
            "type": "வகை",
            "will": "செய்யும்",
            "new": "புதிய",
            "files": "கோப்புகள்",
            "photos": "புகைப்படங்கள்",
            "photo": "புகைப்படம்",
            "complaint": "புகார்",
            "batch": "தொகுதி",
            "course": "பாடநெறி",
            "assignment": "ஒப்படைப்பு",
            "member": "உறுப்பினர்",
            "contacts": "தொடர்புகள்",
            "wallet": "பணப்பை",
            "background": "பின்னணி",
            "business": "வணிகம்",
            "image": "படம்",
            "employee": "ஊழியர்",
            "location": "இடம்",
            "payment": "கட்டணம்",
        }
        
    def _get_telugu_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Telugu dictionary."""
        return {
            "home": "హోమ్",
            "profile": "ప్రొఫైల్",
            "settings": "సెట్టింగ్స్",
            "help": "సహాయం",
            "user": "వినియోగదారు",
            "name": "పేరు",
            "email": "ఇమెయిల్",
            "phone": "ఫోన్",
            "address": "చిరునామా",
            "save": "సేవ్",
            "title": "శీర్షిక",
            "theme": "థీమ్",
            "dark": "డార్క్",
            "mode": "మోడ్",
            "enable": "ప్రారంభించు",
            "notifications": "నోటిఫికేషన్స్",
            "language": "భాష",
            "ok": "సరే",
            "cancel": "రద్దు",
            "delete": "తొలగించు",
            "edit": "సవరించు",
            "welcome": "స్వాగతం",
            "you": "మీరు",
            "have": "ఉన్నాయి",
            "items": "ఐటెమ్స్",
            "price": "ధర",
            "network": "నెట్‌వర్క్",
            "status": "స్థితి",
            "visit": "సందర్శించండి",
            "our": "మా",
            "website": "వెబ్‌సైట్",
            "for": "కోసం",
            "more": "మరింత",
            "information": "సమాచారం",
            "learn": "నేర్చుకోండి",
            "here": "ఇక్కడ",
            "my": "నా",
            "android": "ఆండ్రాయిడ్",
            "app": "యాప్",
            "about": "గురించి",
            "about_us": "మా గురించి",
            "accept": "అంగీకరించు",
            "access": "యాక్సెస్",
            "account": "ఖాతా",
            "add": "జోడించు",
            "all": "అన్నీ",
            "category": "కేటగిరీ",
            "customer": "కస్టమర్",
            "digital": "డిజిటల్",
            "description": "వివరణ",
            "details": "వివరాలు",
            "data": "డేటా",
            "number": "నంబర్",
            "setup": "సెటప్",
            "management": "మేనేజ్మెంట్",
            "to": "కు",
            "type": "రకం",
            "will": "అవుతుంది",
            "new": "కొత్త",
            "files": "ఫైల్స్",
            "photos": "ఫోటోలు",
            "photo": "ఫోటో",
            "complaint": "ఫిర్యాదు",
            "batch": "బ్యాచ్",
            "course": "కోర్సు",
            "assignment": "అసైన్మెంట్",
            "member": "సభ్యుడు",
            "contacts": "కాంటాక్ట్స్",
            "wallet": "వాలెట్",
            "background": "బ్యాక్‌గ్రౌండ్",
            "business": "బిజినెస్",
            "image": "ఇమేజ్",
            "employee": "ఉద్యోగి",
            "location": "స్థానం",
            "payment": "చెల్లింపు",
            # Multi-word phrases
            "visit our": "మా సందర్శించండి",
            "visit our website": "మా వెబ్‌సైట్‌ను సందర్శించండి",
            "for more information": "మరింత సమాచారం కోసం",
            "learn more": "మరింత తెలుసుకోండి",
            "dark mode": "డార్క్ మోడ్",
            "user profile": "వినియోగదారు ప్రొఫైల్",
            "save profile": "ప్రొఫైల్ సేవ్ చేయండి",
            "save settings": "సెట్టింగ్స్ సేవ్ చేయండి",
            "enable notifications": "నోటిఫికేషన్లను ప్రారంభించండి",
            "network status": "నెట్‌వర్క్ స్థితి",
            "my android app": "నా ఆండ్రాయిడ్ యాప్",
        }
        
    def _get_kannada_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Kannada dictionary."""
        return {
            "home": "ಹೋಮ್",
            "profile": "ಪ್ರೊಫೈಲ್",
            "settings": "ಸೆಟ್ಟಿಂಗ್ಗಳು",
            "help": "ಸಹಾಯ",
            "user": "ಬಳಕೆದಾರ",
            "name": "ಹೆಸರು",
            "email": "ಇಮೇಲ್",
            "phone": "ಫೋನ್",
            "address": "ವಿಳಾಸ",
            "save": "ಉಳಿಸಿ",
            "title": "ಶೀರ್ಷಿಕೆ",
            "theme": "ಥೀಮ್",
            "dark": "ಡಾರ್ಕ್",
            "mode": "ಮೋಡ್",
            "enable": "ಸಕ್ರಿಯಗೊಳಿಸಿ",
            "notifications": "ಅಧಿಸೂಚನೆಗಳು",
            "language": "ಭಾಷೆ",
            "ok": "ಸರಿ",
            "cancel": "ರದ್ದುಮಾಡಿ",
            "delete": "ಅಳಿಸಿ",
            "edit": "ಸಂಪಾದಿಸಿ",
            "welcome": "ಸ್ವಾಗತ",
            "you": "ನೀವು",
            "have": "ಹೊಂದಿದ್ದೀರಿ",
            "items": "ಐಟಂಗಳು",
            "price": "ಬೆಲೆ",
            "network": "ನೆಟ್ವರ್ಕ್",
            "status": "ಸ್ಥಿತಿ",
            "visit": "ಭೇಟಿ ನೀಡಿ",
            "our": "ನಮ್ಮ",
            "website": "ವೆಬ್ಸೈಟ್",
            "for": "ಗಾಗಿ",
            "more": "ಹೆಚ್ಚು",
            "information": "ಮಾಹಿತಿ",
            "learn": "ತಿಳಿಯಿರಿ",
            "here": "ಇಲ್ಲಿ",
            "my": "ನನ್ನ",
            "android": "ಆಂಡ್ರಾಯ್ಡ್",
            "app": "ಆ್ಯಪ್",
            "about": "ಬಗ್ಗೆ",
            "about_us": "ನಮ್ಮ ಬಗ್ಗೆ",
            "accept": "ಒಪ್ಪಿಕೊಳ್ಳಿ",
            "access": "ಪ್ರವೇಶ",
            "account": "ಖಾತೆ",
            "add": "ಸೇರಿಸಿ",
            "all": "ಎಲ್ಲಾ",
            "category": "ವರ್ಗ",
            "customer": "ಗ್ರಾಹಕ",
            "digital": "ಡಿಜಿಟಲ್",
            "description": "ವಿವರಣೆ",
            "details": "ವಿವರಗಳು",
            "data": "ಡೇಟಾ",
            "number": "ಸಂಖ್ಯೆ",
            "setup": "ಸೆಟಪ್",
            "management": "ನಿರ್ವಹಣೆ",
            "to": "ಗೆ",
            "type": "ಪ್ರಕಾರ",
            "will": "ಮಾಡುತ್ತದೆ",
            "new": "ಹೊಸ",
            "files": "ಫೈಲ್‌ಗಳು",
            "photos": "ಫೋಟೋಗಳು",
            "photo": "ಫೋಟೋ",
            "complaint": "ದೂರು",
            "batch": "ಬ್ಯಾಚ್",
            "course": "ಕೋರ್ಸ್",
            "assignment": "ಅಸೈನ್ಮೆಂಟ್",
            "member": "ಸದಸ್ಯ",
            "contacts": "ಸಂಪರ್ಕಗಳು",
            "wallet": "ವಾಲೆಟ್",
            "background": "ಹಿನ್ನೆಲೆ",
            "business": "ವ್ಯಾಪಾರ",
            "image": "ಚಿತ್ರ",
            "employee": "ನೌಕರ",
            "location": "ಸ್ಥಳ",
            "payment": "ಪಾವತಿ",
        }
        
    def _get_malayalam_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Malayalam dictionary."""
        return {
            "home": "ഹോം",
            "profile": "പ്രൊഫൈൽ",
            "settings": "ക്രമീകരണങ്ങൾ",
            "help": "സഹായം",
            "user": "ഉപയോക്താവ്",
            "name": "പേര്",
            "email": "ഇമെയിൽ",
            "phone": "ഫോൺ",
            "address": "വിലാസം",
            "save": "സംരക്ഷിക്കുക",
            "title": "ശീർഷകം",
            "theme": "തീം",
            "dark": "ഡാർക്ക്",
            "mode": "മോഡ്",
            "enable": "പ്രവർത്തനക്ഷമമാക്കുക",
            "notifications": "അറിയിപ്പുകൾ",
            "language": "ഭാഷ",
            "ok": "ശരി",
            "cancel": "റദ്ദാക്കുക",
            "delete": "ഇല്ലാതാക്കുക",
            "edit": "എഡിറ്റ് ചെയ്യുക",
            "welcome": "സ്വാഗതം",
            "you": "നിങ്ങൾ",
            "have": "ഉണ്ട്",
            "items": "ഇനങ്ങൾ",
            "price": "വില",
            "network": "നെറ്റ്‌വർക്ക്",
            "status": "നില",
            "visit": "സന്ദർശിക്കുക",
            "our": "ഞങ്ങളുടെ",
            "website": "വെബ്‌സൈറ്റ്",
            "for": "കുറിച്ച്",
            "more": "കൂടുതൽ",
            "information": "വിവരങ്ങൾ",
            "learn": "പഠിക്കുക",
            "here": "ഇവിടെ",
            "my": "എന്റെ",
            "android": "ആൻഡ്രോയിഡ്",
            "app": "ആപ്പ്",
            "about": "കുറിച്ച്",
            "about_us": "ഞങ്ങളെക്കുറിച്ച്",
            "accept": "സ്വീകരിക്കുക",
            "access": "ആക്സസ്",
            "account": "അക്കൗണ്ട്",
            "add": "ചേർക്കുക",
            "all": "എല്ലാം",
            "category": "വിഭാഗം",
            "customer": "ഉപഭോക്താവ്",
            "digital": "ഡിജിറ്റൽ",
            "description": "വിവരണം",
            "details": "വിശദാംശങ്ങൾ",
            "data": "ഡാറ്റ",
            "number": "നമ്പർ",
            "setup": "സെറ്റപ്പ്",
            "management": "മാനേജ്‌മെന്റ്",
            "to": "ലേക്ക്",
            "type": "തരം",
            "will": "ചെയ്യും",
            "new": "പുതിയ",
            "files": "ഫയലുകൾ",
            "photos": "ഫോട്ടോകൾ",
            "photo": "ഫോട്ടോ",
            "complaint": "പരാതി",
            "batch": "ബാച്ച്",
            "course": "കോഴ്‌സ്",
            "assignment": "അസൈൻമെന്റ്",
            "member": "അംഗം",
            "contacts": "കോൺടാക്റ്റുകൾ",
            "wallet": "വാലറ്റ്",
            "background": "പശ്ചാത്തലം",
            "business": "ബിസിനസ്",
            "image": "ചിത്രം",
            "employee": "ജീവനക്കാരൻ",
            "location": "സ്ഥാനം",
            "payment": "പേയ്‌മെന്റ്",
        }
        
    def _get_gujarati_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Gujarati dictionary."""
        return {
            "home": "હોમ",
            "profile": "પ્રોફાઇલ",
            "settings": "સેટિંગ્સ",
            "help": "મદદ",
            "user": "વપરાશકર્તા",
            "name": "નામ",
            "email": "ઇમેઇલ",
            "phone": "ફોન",
            "address": "સરનામું",
            "save": "સાચવો",
            "title": "શીર્ષક",
            "theme": "થીમ",
            "dark": "ડાર્ક",
            "mode": "મોડ",
            "enable": "સક્ષમ કરો",
            "notifications": "સૂચનાઓ",
            "language": "ભાષા",
            "ok": "ઠીક છે",
            "cancel": "રદ કરો",
            "delete": "કાઢી નાખો",
            "edit": "સંપાદિત કરો",
            "welcome": "આપનું સ્વાગત છે",
            "you": "તમે",
            "have": "છે",
            "items": "આઇટમ્સ",
            "price": "કિંમત",
            "network": "નેટવર્ક",
            "status": "સ્થિતિ",
            "visit": "મુલાકાત લો",
            "our": "અમારી",
            "website": "વેબસાઇટ",
            "for": "માટે",
            "more": "વધુ",
            "information": "માહિતી",
            "learn": "શીખો",
            "here": "અહીં",
            "my": "મારું",
            "android": "એન્ડ્રોઇડ",
            "app": "એપ",
            "about": "વિશે",
            "about_us": "અમારા વિશે",
            "accept": "સ્વીકારો",
            "access": "ઍક્સેસ",
            "account": "એકાઉન્ટ",
            "add": "ઉમેરો",
            "all": "બધા",
            "category": "કેટેગરી",
            "customer": "ગ્રાહક",
            "digital": "ડિજિટલ",
            "description": "વર્ણન",
            "details": "વિગતો",
            "data": "ડેટા",
            "number": "નંબર",
            "setup": "સેટઅપ",
            "management": "મેનેજમેન્ટ",
            "to": "થી",
            "type": "પ્રકાર",
            "will": "થશે",
            "new": "નવું",
            "files": "ફાઇલો",
            "photos": "ફોટા",
            "photo": "ફોટો",
            "complaint": "ફરિયાદ",
            "batch": "બેચ",
            "course": "કોર્સ",
            "assignment": "અસાઈનમેન્ટ",
            "member": "સભ્ય",
            "contacts": "સંપર્કો",
            "wallet": "વૉલેટ",
            "background": "બૅકગ્રાઉન્ડ",
            "business": "બિઝનેસ",
            "image": "ઇમેજ",
            "employee": "કર્મચારી",
            "location": "સ્થાન",
            "payment": "પેમેન્ટ",
        }
        
    def _get_punjabi_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Punjabi dictionary."""
        return {
            "home": "ਹੋਮ",
            "profile": "ਪ੍ਰੋਫਾਈਲ",
            "settings": "ਸੈਟਿੰਗਜ਼",
            "help": "ਮਦਦ",
            "user": "ਯੂਜ਼ਰ",
            "name": "ਨਾਮ",
            "email": "ਈਮੇਲ",
            "phone": "ਫੋਨ",
            "address": "ਪਤਾ",
            "save": "ਸੇਵ",
            "title": "ਸਿਰਲੇਖ",
            "theme": "ਥੀਮ",
            "dark": "ਡਾਰਕ",
            "mode": "ਮੋਡ",
            "enable": "ਸਮਰੱਥ",
            "notifications": "ਸੂਚਨਾਵਾਂ",
            "language": "ਭਾਸ਼ਾ",
            "ok": "ਠੀਕ ਹੈ",
            "cancel": "ਰੱਦ ਕਰੋ",
            "delete": "ਮਿਟਾਓ",
            "edit": "ਸੋਧੋ",
            "welcome": "ਜੀ ਆਇਆਂ ਨੂੰ",
            "you": "ਤੁਸੀਂ",
            "have": "ਹੈ",
            "items": "ਆਈਟਮਾਂ",
            "price": "ਮੁੱਲ",
            "network": "ਨੈਟਵਰਕ",
            "status": "ਸਥਿਤੀ",
            "visit": "ਵਿਜ਼ਿਟ",
            "our": "ਸਾਡੀ",
            "website": "ਵੈਬਸਾਈਟ",
            "for": "ਲਈ",
            "more": "ਹੋਰ",
            "information": "ਜਾਣਕਾਰੀ",
            "learn": "ਸਿੱਖੋ",
            "here": "ਇੱਥੇ",
            "my": "ਮੇਰਾ",
            "android": "ਐਂਡਰਾਇਡ",
            "app": "ਐਪ",
            "about": "ਬਾਰੇ",
            "about_us": "ਸਾਡੇ ਬਾਰੇ",
            "accept": "ਸਵੀਕਾਰ",
            "access": "ਪਹੁੰਚ",
            "account": "ਖਾਤਾ",
            "add": "ਜੋੜੋ",
            "all": "ਸਾਰੇ",
            "category": "ਸ਼੍ਰੇਣੀ",
            "customer": "ਗਾਹਕ",
            "digital": "ਡਿਜੀਟਲ",
            "description": "ਵੇਰਵਾ",
            "details": "ਵੇਰਵੇ",
            "data": "ਡਾਟਾ",
            "number": "ਨੰਬਰ",
            "setup": "ਸੈਟਅੱਪ",
            "management": "ਪ੍ਰਬੰਧਨ",
            "to": "ਨੂੰ",
            "type": "ਟਾਈਪ",
            "will": "ਕਰੇਗਾ",
            "new": "ਨਵਾਂ",
            "files": "ਫਾਈਲਾਂ",
            "photos": "ਫੋਟੋਆਂ",
            "photo": "ਫੋਟੋ",
            "complaint": "ਸ਼ਿਕਾਇਤ",
            "batch": "ਬੈਚ",
            "course": "ਕੋਰਸ",
            "assignment": "ਅਸਾਈਨਮੈਂਟ",
            "member": "ਮੈਂਬਰ",
            "contacts": "ਸੰਪਰਕ",
            "wallet": "ਵਾਲੇਟ",
            "background": "ਬੈਕਗ੍ਰਾਊਂਡ",
            "business": "ਬਿਜ਼ਨਸ",
            "image": "ਚਿੱਤਰ",
            "employee": "ਕਰਮਚਾਰੀ",
            "location": "ਸਥਾਨ",
            "payment": "ਭੁਗਤਾਨ",
        }
        
    def _get_odia_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Odia dictionary."""
        return {
            "home": "ହୋମ୍",
            "profile": "ପ୍ରୋଫାଇଲ୍",
            "settings": "ସେଟିଂସ୍",
            "help": "ସାହାଯ୍ୟ",
            "user": "ୟୁଜର୍",
            "name": "ନାମ",
            "email": "ଇମେଲ୍",
            "phone": "ଫୋନ୍",
            "address": "ଠିକଣା",
            "save": "ସେଭ୍",
            "title": "ଶୀର୍ଷକ",
            "theme": "ଥିମ୍",
            "dark": "ଡାର୍କ",
            "mode": "ମୋଡ୍",
            "enable": "ସକ୍ଷମ",
            "notifications": "ନୋଟିଫିକେସନ୍",
            "language": "ଭାଷା",
            "ok": "ଠିକ୍ ଅଛି",
            "cancel": "ବାତିଲ୍",
            "delete": "ଡିଲିଟ୍",
            "edit": "ଏଡିଟ୍",
            "welcome": "ସ୍ୱାଗତ",
            "you": "ଆପଣ",
            "have": "ଅଛି",
            "items": "ଆଇଟମ୍",
            "price": "ମୂଲ୍ୟ",
            "network": "ନେଟୱାର୍କ",
            "status": "ସ୍ଥିତି",
            "visit": "ଭିଜିଟ୍",
            "our": "ଆମର",
            "website": "ୱେବସାଇଟ୍",
            "for": "ପାଇଁ",
            "more": "ଅଧିକ",
            "information": "ସୂଚନା",
            "learn": "ଶିଖନ୍ତୁ",
            "here": "ଏଠାରେ",
            "my": "ମୋର",
            "android": "ଆଣ୍ଡ୍ରଏଡ୍",
            "app": "ଆପ୍",
            "about": "ବିଷୟରେ",
            "about_us": "ଆମ ବିଷୟରେ",
            "accept": "ଗ୍ରହଣ",
            "access": "ଆକ୍ସେସ୍",
            "account": "ଆକାଉଣ୍ଟ",
            "add": "ଯୋଡନ୍ତୁ",
            "all": "ସମସ୍ତ",
            "category": "ବର୍ଗ",
            "customer": "ଗ୍ରାହକ",
            "digital": "ଡିଜିଟାଲ୍",
            "description": "ବର୍ଣ୍ଣନା",
            "details": "ବିବରଣୀ",
            "data": "ଡାଟା",
            "number": "ନମ୍ବର",
            "setup": "ସେଟଅପ୍",
            "management": "ପରିଚାଳନା",
            "to": "କୁ",
            "type": "ପ୍ରକାର",
            "will": "ହେବ",
            "new": "ନୂଆ",
            "files": "ଫାଇଲ୍",
            "photos": "ଫଟୋ",
            "photo": "ଫଟୋ",
            "complaint": "ଅଭିଯୋଗ",
            "batch": "ବ୍ୟାଚ୍",
            "course": "କୋର୍ସ",
            "assignment": "ଆସାଇନମେଣ୍ଟ",
            "member": "ସଦସ୍ୟ",
            "contacts": "କଣ୍ଟାକ୍ଟ",
            "wallet": "ୱାଲେଟ୍",
            "background": "ବ୍ୟାକଗ୍ରାଉଣ୍ଡ",
            "business": "ବ୍ୟବସାୟ",
            "image": "ଇମେଜ୍",
            "employee": "କର୍ମଚାରୀ",
            "location": "ଲୋକେସନ୍",
            "payment": "ପେମେଣ୍ଟ",
        }
        
    def _get_assamese_dictionary(self) -> Dict[str, str]:
        """Return a basic English to Assamese dictionary."""
        return {
            "home": "হোম",
            "profile": "প্ৰফাইল",
            "settings": "ছেটিংছ",
            "help": "সহায়",
            "user": "ব্যৱহাৰকাৰী",
            "name": "নাম",
            "email": "ইমেইল",
            "phone": "ফোন",
            "address": "ঠিকনা",
            "save": "ছেভ",
            "title": "শিৰোনাম",
            "theme": "থীম",
            "dark": "ডাৰ্ক",
            "mode": "ম'ড",
            "enable": "সক্ষম কৰক",
            "notifications": "জাননী",
            "language": "ভাষা",
            "ok": "ঠিক আছে",
            "cancel": "বাতিল",
            "delete": "মচি পেলাওক",
            "edit": "সম্পাদনা",
            "welcome": "স্বাগতম",
            "you": "আপুনি",
            "have": "আছে",
            "items": "আইটেম",
            "price": "মূল্য",
            "network": "নেটৱৰ্ক",
            "status": "স্থিতি",
            "visit": "ভিজিট",
            "our": "আমাৰ",
            "website": "ৱেবছাইট",
            "for": "ৰ বাবে",
            "more": "অধিক",
            "information": "তথ্য",
            "learn": "জানক",
            "here": "ইয়াত",
            "my": "মোৰ",
            "android": "এণ্ড্ৰয়েড",
            "app": "এপ্প",
            "about": "বিষয়ে",
            "about_us": "আমাৰ বিষয়ে",
            "accept": "গ্ৰহণ",
            "access": "এক্সেছ",
            "account": "একাউণ্ট",
            "add": "যোগ",
            "all": "সকলো",
            "category": "শ্ৰেণী",
            "customer": "গ্ৰাহক",
            "digital": "ডিজিটেল",
            "description": "বিৱৰণ",
            "details": "বিৱৰণ",
            "data": "ডাটা",
            "number": "নম্বৰ",
            "setup": "ছেটআপ",
            "management": "পৰিচালনা",
            "to": "লৈ",
            "type": "প্ৰকাৰ",
            "will": "হ'ব",
            "new": "নতুন",
            "files": "ফাইল",
            "photos": "ফটো",
            "photo": "ফটো",
            "complaint": "অভিযোগ",
            "batch": "বেটচ",
            "course": "কোৰ্ছ",
            "assignment": "এছাইনমেণ্ট",
            "member": "সদস্য",
            "contacts": "কণ্টেক্ট",
            "wallet": "ৱালেট",
            "background": "বেকগ্ৰাউণ্ড",
            "business": "ব্যৱসায়",
            "image": "ছবি",
            "employee": "কৰ্মচাৰী",
            "location": "অৱস্থান",
            "payment": "পেমেণ্ট",
        }
    
class FreeTranslateClient(TranslationAPIClient):
    """Client for free translation that doesn't rely on external APIs."""
    
    def __init__(self, api_key: str = ""):
        super().__init__(api_key)
        self.dictionary_translator = DictionaryTranslator()
        
    def translate_batch(self, texts: List[str], target_language: str) -> List[str]:
        """
        Translate a batch of texts using free methods.
        
        Args:
            texts: List of text strings to translate
            target_language: Target language code
            
        Returns:
            List of translated text strings
        """
        return self.dictionary_translator.translate_batch(texts, target_language)
