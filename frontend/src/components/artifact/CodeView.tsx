import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { copyToClipboard } from '../../lib/utils';

interface CodeViewProps {
  code: string;
  language?: string;
}

export const CodeView: React.FC<CodeViewProps> = ({ code, language = 'html' }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const success = await copyToClipboard(code);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const lines = code.split('\n');

  return (
    <div className="relative w-full h-full bg-slate-950 text-slate-100 font-mono text-xs overflow-auto">
      <div className="sticky top-0 z-10 flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800 text-[11px] text-slate-400">
        <span className="uppercase font-semibold tracking-wider">{language}</span>
        <button
          onClick={handleCopy}
          className="cursor-pointer inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-400" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy Code</span>
            </>
          )}
        </button>
      </div>

      <div className="p-4 flex">
        {/* Line Numbers */}
        <div className="select-none text-slate-600 text-right pr-4 font-mono text-[11px]">
          {lines.map((_, i) => (
            <div key={i}>{i + 1}</div>
          ))}
        </div>

        {/* Code Content */}
        <pre className="flex-1 overflow-x-auto">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
};
