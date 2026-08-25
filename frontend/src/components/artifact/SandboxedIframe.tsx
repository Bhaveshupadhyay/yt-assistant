import React, { useMemo } from 'react';

interface SandboxedIframeProps {
  content: string;
  title?: string;
  isDark?: boolean;
}

export const SandboxedIframe: React.FC<SandboxedIframeProps> = ({
  content,
  title = "Sandboxed Artifact",
  isDark = false,
}) => {
  const processedDoc = useMemo(() => {
    // Check if the content is complete HTML or a snippet
    const isFullHtml = content.toLowerCase().includes('<html') || content.toLowerCase().includes('<!doctype');

    if (isFullHtml) {
      return content;
    }

    // Wrap snippet in standard responsive container with styling
    return `
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <script src="https://cdn.tailwindcss.com"></script>
          <style>
            body {
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
              padding: 1.25rem;
              background-color: ${isDark ? '#0f172a' : '#ffffff'};
              color: ${isDark ? '#f8fafc' : '#0f172a'};
            }
          </style>
        </head>
        <body class="${isDark ? 'dark' : ''}">
          ${content}
        </body>
      </html>
    `;
  }, [content, isDark]);

  return (
    <div className="w-full h-full bg-white dark:bg-slate-950 overflow-hidden relative">
      <iframe
        title={title}
        srcDoc={processedDoc}
        sandbox="allow-scripts"
        className="w-full h-full border-0"
      />
    </div>
  );
};
