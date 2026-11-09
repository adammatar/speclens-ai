import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Locale = "en" | "he";

const STORAGE_KEY = "speclens.locale";

type Dict = Record<string, string>;

const en: Dict = {
  "nav.home": "Home",
  "nav.documents": "Documents",
  "nav.settings": "Settings",
  "nav.signOut": "Sign out",
  "lang.toggle": "עברית",
  "lang.toggleTitle": "Switch to Hebrew",

  "signin.lede":
    "Upload specs, chat in plain language, and keep versions side by side — built for clear answers with evidence.",
  "signin.label": "Workspace access key",
  "signin.placeholder": "Paste your access key",
  "signin.continue": "Continue",
  "signin.checking": "Checking…",
  "signin.hint":
    "This is your SpecLens workspace key (local default: speclens-local-dev-key). It is not your Gemini/OpenAI key — that stays in the server .env. Stored in this browser session only.",
  "signin.failed": "Sign-in failed",

  "home.title": "Workspace",
  "home.subtitle": "Your files and live stats — chat stays on the right.",
  "home.upload": "Upload",
  "home.search": "Search documents",
  "home.allStatus": "All status",
  "home.statusReady": "Ready",
  "home.statusReading": "Reading",
  "home.statusQueued": "Queued",
  "home.statusFailed": "Failed",
  "home.docs": "Documents",
  "home.versions": "Versions",
  "home.api": "API",
  "home.retention": "Retention days",
  "home.chat": "Chat",
  "home.inChat": "In chat",
  "home.newVersion": "New version",
  "home.emptyDocs": "No documents yet. Upload a file to begin.",
  "home.scrollMore": "Scroll for more…",
  "home.seeAll": "See all documents",
  "home.working": "Working",
  "home.waitReady": "Wait until the document is Ready",

  "chat.title": "Chat",
  "chat.subtitle": "Answers stay in plain language, grounded in the documents you pick.",
  "chat.new": "New chat",
  "chat.empty": "Ask anything about your selected documents.",
  "chat.searching": "Searching:",
  "chat.needUpload": "Upload a document to get started",
  "chat.pickDocs": "Pick at least one document below the composer before asking.",
  "chat.placeholder": "Message SpecLens…",
  "chat.placeholderNeedDoc": "Select at least one document, then ask…",
  "chat.send": "Send",
  "chat.citeOne": "Based on {n} source quote from your documents",
  "chat.citeMany": "Based on {n} source quotes from your documents",
  "chat.suggest1": "When was John born?",
  "chat.suggest2": "Summarize the key points in plain language",
  "chat.suggest3": "What changed in the latest version?",
  "chat.askFailed": "Ask failed",

  "docs.title": "Documents",
  "docs.subtitle":
    "Full library with search and filters. Upload new versions without leaving this page.",
  "docs.upload": "Upload",
  "docs.search": "Search by title",
  "docs.delete": "Delete",
  "docs.newVersion": "New version",
  "docs.empty": "No matching documents.",
  "docs.confirmDelete": "Delete “{title}”?",

  "detail.library": "Library",
  "detail.homeChat": "Home chat",
  "detail.uploadVersion": "Upload new version",
  "detail.delete": "Delete",
  "detail.confirmDelete": "Delete this document and all versions?",
  "detail.lede":
    "Latest and previous versions are kept for change questions. Processing runs automatically in the background.",
  "detail.latest": "Latest",
  "detail.previous": "Previous",
  "detail.kept": " · kept with previous for compare",
  "detail.preview": "Preview (latest)",
  "detail.noPreview": "No preview yet — wait until status is Ready.",
  "detail.noVersions": "No versions yet.",

  "settings.title": "Settings",
  "settings.subtitle": "Workspace session, language, and runtime backends.",
  "settings.sessionKey": "Session access key",
  "settings.sessionHint": "Stored in sessionStorage only. Sign out clears it.",
  "settings.runtime": "Runtime",
  "settings.language": "Interface language",
  "settings.langEn": "English",
  "settings.langHe": "Hebrew",
  "settings.authRequired": "required",
  "settings.authOpen": "open",
};

const he: Dict = {
  "nav.home": "בית",
  "nav.documents": "מסמכים",
  "nav.settings": "הגדרות",
  "nav.signOut": "יציאה",
  "lang.toggle": "English",
  "lang.toggleTitle": "מעבר לאנגלית",

  "signin.lede":
    "העלו מפרטים, שוחחו בשפה פשוטה, ושמרו גרסאות זה לצד זה — תשובות ברורות עם ביסוס במסמך.",
  "signin.label": "מפתח גישה למרחב העבודה",
  "signin.placeholder": "הדביקו את מפתח הגישה",
  "signin.continue": "המשך",
  "signin.checking": "בודק…",
  "signin.hint":
    "זה מפתח הגישה של SpecLens למרחב העבודה (ברירת מחדל מקומית: speclens-local-dev-key). זה לא מפתח Gemini/OpenAI — הוא נשאר בקובץ .env בשרת. נשמר רק בסשן הדפדפן.",
  "signin.failed": "הכניסה נכשלה",

  "home.title": "מרחב עבודה",
  "home.subtitle": "הקבצים והסטטיסטיקה — הצ׳אט בצד השני.",
  "home.upload": "העלאה",
  "home.search": "חיפוש מסמכים",
  "home.allStatus": "כל הסטטוסים",
  "home.statusReady": "מוכן",
  "home.statusReading": "קורא",
  "home.statusQueued": "בתור",
  "home.statusFailed": "נכשל",
  "home.docs": "מסמכים",
  "home.versions": "גרסאות",
  "home.api": "API",
  "home.retention": "ימי שמירה",
  "home.chat": "צ׳אט",
  "home.inChat": "בצ׳אט",
  "home.newVersion": "גרסה חדשה",
  "home.emptyDocs": "אין מסמכים עדיין. העלו קובץ כדי להתחיל.",
  "home.scrollMore": "גללו לעוד…",
  "home.seeAll": "לכל המסמכים",
  "home.working": "בעבודה",
  "home.waitReady": "המתינו עד שהמסמך יהיה מוכן",

  "chat.title": "צ׳אט",
  "chat.subtitle": "תשובות בשפה פשוטה, מבוססות על המסמכים שבחרתם.",
  "chat.new": "צ׳אט חדש",
  "chat.empty": "שאלו כל דבר על המסמכים שנבחרו.",
  "chat.searching": "מחפש ב:",
  "chat.needUpload": "העלו מסמך כדי להתחיל",
  "chat.pickDocs": "בחרו לפחות מסמך אחד מתחת לפני השאלה.",
  "chat.placeholder": "כתבו ל־SpecLens…",
  "chat.placeholderNeedDoc": "בחרו מסמך ואז שאלו…",
  "chat.send": "שליחה",
  "chat.citeOne": "מבוסס על ציטוט מקור אחד מהמסמכים שלכם",
  "chat.citeMany": "מבוסס על {n} ציטוטי מקור מהמסמכים שלכם",
  "chat.suggest1": "מתי נולד ג׳ון?",
  "chat.suggest2": "סכמו את הנקודות העיקריות בשפה פשוטה",
  "chat.suggest3": "מה השתנה בגרסה האחרונה?",
  "chat.askFailed": "השאלה נכשלה",

  "docs.title": "מסמכים",
  "docs.subtitle": "ספרייה מלאה עם חיפוש וסינון. העלאת גרסה חדשה בלי לעזוב את העמוד.",
  "docs.upload": "העלאה",
  "docs.search": "חיפוש לפי כותרת",
  "docs.delete": "מחיקה",
  "docs.newVersion": "גרסה חדשה",
  "docs.empty": "אין מסמכים תואמים.",
  "docs.confirmDelete": "למחוק את “{title}”?",

  "detail.library": "ספרייה",
  "detail.homeChat": "צ׳אט בבית",
  "detail.uploadVersion": "העלאת גרסה חדשה",
  "detail.delete": "מחיקה",
  "detail.confirmDelete": "למחוק את המסמך ואת כל הגרסאות?",
  "detail.lede":
    "הגרסה האחרונה והקודמת נשמרות לשאלות על שינויים. העיבוד רץ אוטומטית ברקע.",
  "detail.latest": "אחרונה",
  "detail.previous": "קודמת",
  "detail.kept": " · נשמרת עם הקודמת להשוואה",
  "detail.preview": "תצוגה מקדימה (אחרונה)",
  "detail.noPreview": "אין תצוגה עדיין — המתינו עד שהסטטוס יהיה מוכן.",
  "detail.noVersions": "אין גרסאות עדיין.",

  "settings.title": "הגדרות",
  "settings.subtitle": "סשן מרחב העבודה, שפה, ורקעי הריצה.",
  "settings.sessionKey": "מפתח גישה בסשן",
  "settings.sessionHint": "נשמר ב־sessionStorage בלבד. יציאה מוחקת אותו.",
  "settings.runtime": "ריצה",
  "settings.language": "שפת ממשק",
  "settings.langEn": "אנגלית",
  "settings.langHe": "עברית",
  "settings.authRequired": "נדרש",
  "settings.authOpen": "פתוח",
};

const catalogs: Record<Locale, Dict> = { en, he };

type LocaleContextValue = {
  locale: Locale;
  dir: "ltr" | "rtl";
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

function readInitialLocale(): Locale {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "he" || saved === "en") return saved;
  } catch {
    // ignore
  }
  return "en";
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(readInitialLocale);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore
    }
  }, []);

  const toggleLocale = useCallback(() => {
    setLocale(locale === "en" ? "he" : "en");
  }, [locale, setLocale]);

  const dir: "ltr" | "rtl" = locale === "he" ? "rtl" : "ltr";

  useEffect(() => {
    document.documentElement.lang = locale === "he" ? "he" : "en";
    document.documentElement.dir = dir;
  }, [locale, dir]);

  const t = useCallback(
    (key: string, vars?: Record<string, string | number>) => {
      let text = catalogs[locale][key] ?? catalogs.en[key] ?? key;
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          text = text.replace(`{${k}}`, String(v));
        }
      }
      return text;
    },
    [locale],
  );

  const value = useMemo(
    () => ({ locale, dir, setLocale, toggleLocale, t }),
    [locale, dir, setLocale, toggleLocale, t],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within LocaleProvider");
  return ctx;
}
