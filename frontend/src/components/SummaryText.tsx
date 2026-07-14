import type { ReactNode } from "react";

type SummaryTextProps = {
  className?: string;
  text: string;
};

export function SummaryText({ className, text }: SummaryTextProps) {
  const blocks = normaliseSummaryText(text);

  return (
    <div className={className}>
      {blocks.map((block, index) =>
        block.kind === "bullet" ? (
          <ul className="summary-list" key={`${block.kind}-${index}`}>
            {block.items.map((item, itemIndex) => (
              <li key={`${item}-${itemIndex}`}>{renderInlineMarkdown(item)}</li>
            ))}
          </ul>
        ) : (
          <p key={`${block.kind}-${index}`}>{renderInlineMarkdown(block.text)}</p>
        )
      )}
    </div>
  );
}

type SummaryBlock =
  | { kind: "paragraph"; text: string }
  | { kind: "bullet"; items: string[] };

function normaliseSummaryText(text: string): SummaryBlock[] {
  const cleanedText = text
    .replace(/\s*\(#[0-9]+,\s*[^)]*\)/g, "")
    .replace(/\s+([*-])\s+\*\*/g, "\n$1 **")
    .replace(/\r\n/g, "\n")
    .trim();
  const lines = cleanedText
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  const blocks: SummaryBlock[] = [];
  let bulletItems: string[] = [];

  for (const line of lines) {
    const bulletMatch = line.match(/^[-*]\s+(.*)$/);
    if (bulletMatch !== null) {
      bulletItems.push(bulletMatch[1]);
      continue;
    }

    if (bulletItems.length > 0) {
      blocks.push({ kind: "bullet", items: bulletItems });
      bulletItems = [];
    }
    blocks.push({ kind: "paragraph", text: line });
  }

  if (bulletItems.length > 0) {
    blocks.push({ kind: "bullet", items: bulletItems });
  }

  return blocks;
}

function renderInlineMarkdown(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);

  return parts
    .filter((part) => part.length > 0)
    .map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
      }

      return part;
    });
}
