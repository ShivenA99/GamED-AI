'use client';

import { useCallback, useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import type { Extension } from '@codemirror/state';

// Lazy-load CodeMirror to avoid SSR issues
const CodeMirror = dynamic(
  () => import('@uiw/react-codemirror').then((mod) => mod.default),
  { ssr: false, loading: () => <div className="h-64 animate-pulse bg-gray-800 rounded-lg" /> },
);

interface CodeEditorPanelProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  theme?: 'dark' | 'light';
  height?: string;
}

export default function CodeEditorPanel({
  value,
  onChange,
  disabled = false,
  theme = 'dark',
  height = '300px',
}: CodeEditorPanelProps) {
  const [extensions, setExtensions] = useState<Extension[]>([]);

  // Lazy-load Python language support
  useEffect(() => {
    import('@codemirror/lang-python').then((mod) => {
      setExtensions([mod.python()]);
    });
  }, []);

  const handleChange = useCallback(
    (val: string) => {
      if (!disabled) onChange(val);
    },
    [disabled, onChange],
  );

  return (
    <div className="rounded-lg overflow-hidden border border-gray-700">
      <CodeMirror
        value={value}
        height={height}
        theme={theme}
        editable={!disabled}
        onChange={handleChange}
        extensions={extensions}
        basicSetup={{
          lineNumbers: true,
          foldGutter: false,
          highlightActiveLineGutter: true,
          tabSize: 4,
        }}
      />
    </div>
  );
}
