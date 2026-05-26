import { useState } from "react";
import { useT } from "../i18n";
import "./CitationCard.css";

export default function CitationCard({
  docName,
  docId,
  pages,
  pageCount,
  totalChars,
  content,
}) {
  const { t, lang } = useT();
  const [expandedPages, setExpandedPages] = useState({});
  const [copiedIdx, setCopiedIdx] = useState(null);

  const togglePage = (idx) => {
    setExpandedPages((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  const handleCopy = async (text, idx) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx(null), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx(null), 2000);
    }
  };

  const pageRange = pages
    ? Array.isArray(pages)
      ? `pp. ${pages[0]}–${pages[pages.length - 1]}`
      : `p. ${pages}`
    : pageCount
      ? `${pageCount} pages`
      : "";

  const formatPageLabel = (pageNum) => {
    if (lang === "zh") {
      return t("citation.page").replace("{n}", String(pageNum));
    }
    return `${t("citation.page")} ${pageNum}`;
  };

  return (
    <div className="citation-card">
      <div className="citation-accent-strip" />
      <div className="citation-torn-edge" />

      <div className="citation-body">
        <div className="citation-header">
          <div className="citation-doc-info">
            <svg className="citation-doc-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14,2 14,8 20,8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10,9 9,9 8,9" />
            </svg>
            <span className="citation-doc-name">{docName || t("citation.unknownDoc")}</span>
          </div>
          <div className="citation-badge">{t("citation.badge")}</div>
        </div>

        <div className="citation-meta">
          {docId && (
            <span className="citation-meta-item">
              <span className="citation-meta-label">{t("citation.id")}</span> {docId}
            </span>
          )}
          {pageRange && (
            <span className="citation-meta-item">
              <span className="citation-meta-label">{t("citation.range")}</span> {pageRange}
            </span>
          )}
          {totalChars != null && (
            <span className="citation-meta-item">
              <span className="citation-meta-label">{t("citation.chars")}</span>{" "}
              {totalChars.toLocaleString()}
            </span>
          )}
        </div>

        {content && content.length > 0 && (
          <div className="citation-pages">
            {content.map((item, idx) => {
              const isExpanded = expandedPages[idx];
              const displayText = isExpanded
                ? item.content
                : item.preview || (item.content && item.content.slice(0, 400));
              const canExpand =
                item.content && item.content.length > 400;

              return (
                <div key={idx} className="citation-page-item">
                  <div className="citation-page-header">
                    <span className="citation-page-number">
                      {formatPageLabel(item.page)}
                    </span>
                    <div className="citation-page-actions">
                      <button
                        className={`citation-copy-btn ${copiedIdx === idx ? "copied" : ""}`}
                        onClick={() => handleCopy(item.content, idx)}
                        title="Copy content"
                      >
                        {copiedIdx === idx ? (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        ) : (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                            <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                          </svg>
                        )}
                      </button>
                      {canExpand && (
                        <button
                          className="citation-expand-btn"
                          onClick={() => togglePage(idx)}
                        >
                          {isExpanded ? t("citation.collapse") : t("citation.expand")}
                        </button>
                      )}
                    </div>
                  </div>
                  <div className={`citation-page-content ${isExpanded ? "expanded" : ""}`}>
                    {displayText}
                    {!isExpanded && canExpand && (
                      <span className="citation-ellipsis">...</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
