import { I18nProvider, LangToggle, useT } from "./i18n";
import RagChat from "./components/RagChat";
import KnowledgeBaseSummary from "./components/KnowledgeBaseSummary";
import "./App.css";

export default function App() {
  return (
    <I18nProvider>
      <LangToggle />
      <AppInner />
    </I18nProvider>
  );
}

function AppInner() {
  const { t } = useT();
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-brand">
          <div className="brand-mark" />
          <div className="brand-text">
            <h1>{t("app.title")}</h1>
            <p>{t("app.subtitle")}</p>
          </div>
        </div>
      </header>
      <main className="app-main">
        <KnowledgeBaseSummary />
        <RagChat />
      </main>
    </div>
  );
}
