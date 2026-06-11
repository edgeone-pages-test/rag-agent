import { useRef } from "react";
import { I18nProvider, LangToggle, useT } from "./i18n";
import RagChat from "./components/RagChat";
import KnowledgeBaseSummary from "./components/KnowledgeBaseSummary";
import GitHubLink from "./components/GitHubLink";
import DeployLink from "./components/DeployLink";
import "./App.css";

const CONVERSATION_ID_KEY = "rag_conversation_id";

/**
 * Hoisted to App so multiple children (RagChat, KnowledgeBaseSummary)
 * can share the same per-browser conversation id without each one
 * minting its own. KnowledgeBaseSummary needs it because the EdgeOne
 * agents/ runtime requires every agents/* request (including read-only
 * ones like /rag-stats) to carry Markers-Conversation-Id.
 */
function getOrCreateConversationId(): string {
  const cached = localStorage.getItem(CONVERSATION_ID_KEY);
  if (cached) return cached;
  const id = crypto.randomUUID();
  localStorage.setItem(CONVERSATION_ID_KEY, id);
  return id;
}

export default function App() {
  return (
    <I18nProvider>
      <LangToggle />
      <AppInner />
      <GitHubLink />
      <DeployLink />
    </I18nProvider>
  );
}

function AppInner() {
  const { t } = useT();
  const conversationIdRef = useRef<string>(getOrCreateConversationId());
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
        <KnowledgeBaseSummary conversationId={conversationIdRef.current} />
        <RagChat />
      </main>
    </div>
  );
}
