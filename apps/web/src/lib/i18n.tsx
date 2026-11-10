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
  "nav.requirements": "Requirements",
  "nav.compare": "Compare",
  "nav.evaluation": "Evaluation",
  "nav.settings": "Settings",
  "nav.signOut": "Sign out",
  "nav.menu": "Menu",
  "lang.toggle": "עברית",
  "lang.toggleTitle": "Switch to Hebrew",

  "signin.lede":
    "Upload specs, chat in plain language, and keep versions side by side — built for clear answers with evidence.",
  "signin.label": "Workspace access key",
  "signin.placeholder": "Paste your access key",
  "signin.continue": "Continue",
  "signin.checking": "Checking…",
  "signin.hint":
    "SpecLens AI is built as a workspace API product, not a consumer accounts system. If you want to run it on your localhost, the default key is: speclens-local-dev-key",
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
  "chat.placeholder": "Message SpecLens AI…",
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
  "settings.deployment": "Deployment mode",
  "settings.authState": "Authentication",
  "settings.providers": "Configured providers",
  "settings.retention": "Retention policy",
  "settings.retentionHint":
    "Deployment-wide RETENTION_DAYS. Destructive sweeps are not auto-run in local mode.",
  "settings.securityLimits": "Security notes",
  "settings.securityBody":
    "Local mode may use the documented bootstrap key. Hosted mode refuses development passwords and the public bootstrap key. Secrets are never shown here.",

  "req.title": "Requirements",
  "req.subtitle": "Inspect extracted requirements with provenance and review actions.",
  "req.document": "Document",
  "req.version": "Version",
  "req.pickDocument": "Choose a document",
  "req.noVersions": "No versions",
  "req.search": "Search requirements",
  "req.type": "Type",
  "req.status": "Status",
  "req.allTypes": "All types",
  "req.allStatus": "All statuses",
  "req.statement": "Statement",
  "req.quote": "Source quote",
  "req.provenance": "Heading / page",
  "req.actions": "Actions",
  "req.accept": "Accept",
  "req.reject": "Reject",
  "req.extract": "Run extraction",
  "req.extracting": "Extracting…",
  "req.exportJson": "Export JSON",
  "req.exportCsv": "Export CSV",
  "req.loading": "Loading requirements…",
  "req.empty": "No requirements for this version yet. Run extraction.",
  "req.backend": "Extraction backend",
  "req.loadFailed": "Failed to load requirements",
  "req.extractFailed": "Extraction failed",
  "req.reviewFailed": "Review update failed",
  "req.exportFailed": "Export failed",

  "cmp.title": "Version compare",
  "cmp.subtitle": "Diff requirements between two versions of one document.",
  "cmp.document": "Document",
  "cmp.pickDocument": "Choose a document",
  "cmp.base": "Base version",
  "cmp.target": "Target version",
  "cmp.start": "Compare",
  "cmp.running": "Comparing…",
  "cmp.empty": "Select two versions and start a comparison.",
  "cmp.progress": "Status {status} · {pct}% · {n} changes",
  "cmp.old": "Old",
  "cmp.new": "New",
  "cmp.evidence": "Evidence",
  "cmp.decision": "Decision",
  "cmp.confirm": "Confirm",
  "cmp.reject": "Reject",
  "cmp.evalExample": "eval example",
  "cmp.failed": "Comparison failed",
  "cmp.decideFailed": "Could not save decision",
  "cmp.loadFailed": "Failed to load documents",
  "cmp.cat.added": "Added",
  "cmp.cat.removed": "Removed",
  "cmp.cat.behavior_changed": "Behavior changed",
  "cmp.cat.clarified": "Clarified",
  "cmp.cat.priority_changed": "Priority changed",
  "cmp.cat.acceptance_criteria_changed": "Acceptance criteria changed",
  "cmp.cat.potential_breaking_change": "Potential breaking change",
  "cmp.cat.uncertain": "Uncertain",

  "eval.title": "Evaluation",
  "eval.subtitle": "Latest harness report for this deployment.",
  "eval.loading": "Loading evaluation report…",
  "eval.none": "No evaluation run available. Generate one with make eval.",
  "eval.loadFailed": "Failed to load evaluation report",
  "eval.stubBadge": "Synthetic / stub",
  "eval.liveBadge": "Live provider",
  "eval.stubCaveat":
    "Stub/synthetic metrics are not production accuracy. They validate deterministic pipelines on fixtures.",
  "eval.runTime": "Run time",
  "eval.mode": "Mode",
  "eval.dataset": "Dataset",
  "eval.samples": "Question-like samples",
  "eval.backends": "Backends / models",
  "eval.metrics": "Metrics",
  "eval.metric": "Metric",
  "eval.value": "Value",
  "eval.threshold": "Threshold",
  "eval.gate": "Gate",
  "eval.baseline": "Baseline differences",
  "eval.latencyCost": "Latency / tokens / cost",
};

const he: Dict = {
  "nav.home": "בית",
  "nav.documents": "מסמכים",
  "nav.requirements": "דרישות",
  "nav.compare": "השוואה",
  "nav.evaluation": "הערכה",
  "nav.settings": "הגדרות",
  "nav.signOut": "יציאה",
  "nav.menu": "תפריט",
  "lang.toggle": "English",
  "lang.toggleTitle": "מעבר לאנגלית",

  "signin.lede":
    "העלו מפרטים, שוחחו בשפה פשוטה, ושמרו גרסאות זה לצד זה — תשובות ברורות עם ביסוס במסמך.",
  "signin.label": "מפתח גישה למרחב העבודה",
  "signin.placeholder": "הדביקו את מפתח הגישה",
  "signin.continue": "המשך",
  "signin.checking": "בודק…",
  "signin.hint":
    "SpecLens AI נבנה כמוצר API למרחב עבודה, לא כמערכת חשבונות צרכנית. אם מריצים ב־localhost, מפתח ברירת המחדל הוא: speclens-local-dev-key",
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
  "chat.placeholder": "כתבו ל־SpecLens AI…",
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
  "settings.deployment": "מצב פריסה",
  "settings.authState": "אימות",
  "settings.providers": "ספקים מוגדרים",
  "settings.retention": "מדיניות שמירה",
  "settings.retentionHint":
    "RETENTION_DAYS ברמת הפריסה. מחיקות הרסניות אינן רצות אוטומטית במצב מקומי.",
  "settings.securityLimits": "הערות אבטחה",
  "settings.securityBody":
    "במצב מקומי אפשר להשתמש במפתח ה־bootstrap המתועד. במצב hosted נדחים סיסמאות פיתוח ומפתח ה־bootstrap הציבורי. סודות אינם מוצגים כאן.",

  "req.title": "דרישות",
  "req.subtitle": "צפייה בדרישות מחולצות עם מקור ופעולות סקירה.",
  "req.document": "מסמך",
  "req.version": "גרסה",
  "req.pickDocument": "בחרו מסמך",
  "req.noVersions": "אין גרסאות",
  "req.search": "חיפוש דרישות",
  "req.type": "סוג",
  "req.status": "סטטוס",
  "req.allTypes": "כל הסוגים",
  "req.allStatus": "כל הסטטוסים",
  "req.statement": "ניסוח",
  "req.quote": "ציטוט מקור",
  "req.provenance": "כותרת / עמוד",
  "req.actions": "פעולות",
  "req.accept": "אישור",
  "req.reject": "דחייה",
  "req.extract": "הפעלת חילוץ",
  "req.extracting": "מחלץ…",
  "req.exportJson": "ייצוא JSON",
  "req.exportCsv": "ייצוא CSV",
  "req.loading": "טוען דרישות…",
  "req.empty": "אין דרישות לגרסה זו עדיין. הפעילו חילוץ.",
  "req.backend": "רקע חילוץ",
  "req.loadFailed": "טעינת הדרישות נכשלה",
  "req.extractFailed": "החילוץ נכשל",
  "req.reviewFailed": "עדכון הסקירה נכשל",
  "req.exportFailed": "הייצוא נכשל",

  "cmp.title": "השוואת גרסאות",
  "cmp.subtitle": "השוואת דרישות בין שתי גרסאות של אותו מסמך.",
  "cmp.document": "מסמך",
  "cmp.pickDocument": "בחרו מסמך",
  "cmp.base": "גרסת בסיס",
  "cmp.target": "גרסת יעד",
  "cmp.start": "השוואה",
  "cmp.running": "משווה…",
  "cmp.empty": "בחרו שתי גרסאות והתחילו השוואה.",
  "cmp.progress": "סטטוס {status} · {pct}% · {n} שינויים",
  "cmp.old": "ישן",
  "cmp.new": "חדש",
  "cmp.evidence": "ראיות",
  "cmp.decision": "החלטה",
  "cmp.confirm": "אישור",
  "cmp.reject": "דחייה",
  "cmp.evalExample": "דוגמת הערכה",
  "cmp.failed": "ההשוואה נכשלה",
  "cmp.decideFailed": "לא ניתן לשמור את ההחלטה",
  "cmp.loadFailed": "טעינת המסמכים נכשלה",
  "cmp.cat.added": "נוסף",
  "cmp.cat.removed": "הוסר",
  "cmp.cat.behavior_changed": "שינוי התנהגות",
  "cmp.cat.clarified": "הובהר",
  "cmp.cat.priority_changed": "שינוי עדיפות",
  "cmp.cat.acceptance_criteria_changed": "שינוי קריטריוני קבלה",
  "cmp.cat.potential_breaking_change": "שינוי שובר פוטנציאלי",
  "cmp.cat.uncertain": "לא ודאי",

  "eval.title": "הערכה",
  "eval.subtitle": "דוח ההרצה האחרון לפריסה זו.",
  "eval.loading": "טוען דוח הערכה…",
  "eval.none": "אין הרצת הערכה. צרו אחת עם make eval.",
  "eval.loadFailed": "טעינת דוח ההערכה נכשלה",
  "eval.stubBadge": "סינתטי / stub",
  "eval.liveBadge": "ספק חי",
  "eval.stubCaveat":
    "מדדי stub/סינתטיים אינם דיוק ייצור. הם מאמתים צינורות דטרמיניסטיים על fixtures.",
  "eval.runTime": "זמן הרצה",
  "eval.mode": "מצב",
  "eval.dataset": "מערך נתונים",
  "eval.samples": "דוגמאות שאלות",
  "eval.backends": "רקעים / מודלים",
  "eval.metrics": "מדדים",
  "eval.metric": "מדד",
  "eval.value": "ערך",
  "eval.threshold": "סף",
  "eval.gate": "שער",
  "eval.baseline": "הפרשי baseline",
  "eval.latencyCost": "השהיה / טוקנים / עלות",
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
