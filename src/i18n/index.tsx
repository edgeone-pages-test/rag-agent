import { createContext, useContext, useState, useCallback, ReactNode } from "react";
import en from "./en";
import zh from "./zh";

type Lang = "en" | "zh";
export type MessageKeys = keyof typeof en;

const locales: Record<Lang, Record<MessageKeys, string>> = { en, zh };

interface I18nContextValue {
  lang: Lang;
  t: (key: MessageKeys) => string;
  toggle: () => void;
}

const I18nContext = createContext<I18nContextValue>(null!);

function getInitialLang(): Lang {
  const saved = localStorage.getItem("lang") as Lang | null;
  if (saved && (saved === "en" || saved === "zh")) return saved;
  return navigator.language.startsWith("zh") ? "zh" : "en";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(getInitialLang);

  const toggle = useCallback(() => {
    setLang((prev) => {
      const next = prev === "en" ? "zh" : "en";
      localStorage.setItem("lang", next);
      return next;
    });
  }, []);

  const t = useCallback(
    (key: MessageKeys) => locales[lang][key] ?? key,
    [lang]
  );

  return (
    <I18nContext.Provider value={{ lang, t, toggle }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useT() {
  return useContext(I18nContext);
}

export function LangToggle() {
  const { lang, toggle } = useT();
  return (
    <button className="lang-toggle" onClick={toggle} title="Switch Language" aria-label="Switch Language">
      <span className={`lang-toggle__label ${lang === "zh" ? "lang-toggle__label--active" : ""}`}>zh</span>
      <span className="lang-toggle__sep">/</span>
      <span className={`lang-toggle__label ${lang === "en" ? "lang-toggle__label--active" : ""}`}>en</span>
    </button>
  );
}
