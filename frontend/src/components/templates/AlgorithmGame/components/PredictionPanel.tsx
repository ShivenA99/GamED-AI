'use client';

import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  ExtendedPrediction,
  ArrangementPrediction as ArrangementType,
  ValuePrediction as ValueType,
  MultipleChoicePrediction as MCType,
  MultiSelectPrediction as MSType,
  CodeCompletionPrediction as CCType,
  TrueFalsePrediction as TFType,
} from '../types';
import ArrangementPrediction from './ArrangementPrediction';

interface PredictionPanelProps {
  prediction: ExtendedPrediction;
  onSubmit: (answer: number[] | string | string[] | boolean) => void;
  disabled?: boolean;
  theme?: 'dark' | 'light';
}

function ValueInput({
  prediction,
  onSubmit,
  disabled,
  theme,
}: {
  prediction: ValueType;
  onSubmit: (answer: string) => void;
  disabled: boolean;
  theme: string;
}) {
  const [value, setValue] = useState('');

  return (
    <div className="space-y-3">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={prediction.placeholder || 'Type your answer...'}
        disabled={disabled}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && value.trim()) onSubmit(value.trim());
        }}
        className={`w-full p-3 rounded-lg border-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/30 ${
          theme === 'dark'
            ? 'bg-gray-800 border-gray-600 text-white placeholder-gray-500'
            : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'
        }`}
      />
      <div className="flex justify-center">
        <button
          onClick={() => value.trim() && onSubmit(value.trim())}
          disabled={disabled || !value.trim()}
          className={`px-6 py-2 rounded-lg font-medium text-sm transition-colors ${
            disabled || !value.trim()
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : 'bg-primary-500 text-white hover:bg-primary-600'
          }`}
        >
          Submit
        </button>
      </div>
    </div>
  );
}

function MultipleChoiceInput({
  prediction,
  onSubmit,
  disabled,
  theme,
}: {
  prediction: MCType;
  onSubmit: (answer: string) => void;
  disabled: boolean;
  theme: string;
}) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="space-y-2">
      {prediction.options.map((opt) => (
        <motion.button
          key={opt.id}
          whileHover={disabled ? {} : { scale: 1.01 }}
          whileTap={disabled ? {} : { scale: 0.99 }}
          onClick={() => {
            if (disabled) return;
            setSelected(opt.id);
            onSubmit(opt.id);
          }}
          disabled={disabled}
          className={`w-full text-left p-3 rounded-lg border-2 transition-all text-sm ${
            selected === opt.id
              ? 'border-primary-500 bg-primary-500/10'
              : theme === 'dark'
              ? 'border-gray-700 bg-gray-800 hover:border-gray-500'
              : 'border-gray-200 bg-white hover:border-gray-400'
          } ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'} ${
            theme === 'dark' ? 'text-gray-200' : 'text-gray-800'
          }`}
        >
          {opt.label}
        </motion.button>
      ))}
    </div>
  );
}

function MultiSelectInput({
  prediction,
  onSubmit,
  disabled,
  theme,
}: {
  prediction: MSType;
  onSubmit: (answer: string[]) => void;
  disabled: boolean;
  theme: string;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggle = useCallback(
    (id: string) => {
      if (disabled) return;
      setSelected((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
    },
    [disabled],
  );

  return (
    <div className="space-y-2">
      {prediction.options.map((opt) => (
        <button
          key={opt.id}
          onClick={() => toggle(opt.id)}
          disabled={disabled}
          className={`w-full text-left p-3 rounded-lg border-2 transition-all text-sm flex items-center gap-2 ${
            selected.has(opt.id)
              ? 'border-primary-500 bg-primary-500/10'
              : theme === 'dark'
              ? 'border-gray-700 bg-gray-800 hover:border-gray-500'
              : 'border-gray-200 bg-white hover:border-gray-400'
          } ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'} ${
            theme === 'dark' ? 'text-gray-200' : 'text-gray-800'
          }`}
        >
          <div
            className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
              selected.has(opt.id)
                ? 'border-primary-500 bg-primary-500'
                : theme === 'dark'
                ? 'border-gray-500'
                : 'border-gray-400'
            }`}
          >
            {selected.has(opt.id) && (
              <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            )}
          </div>
          {opt.label}
        </button>
      ))}
      <div className="flex justify-center mt-2">
        <button
          onClick={() => onSubmit([...selected])}
          disabled={disabled || selected.size === 0}
          className={`px-6 py-2 rounded-lg font-medium text-sm transition-colors ${
            disabled || selected.size === 0
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : 'bg-primary-500 text-white hover:bg-primary-600'
          }`}
        >
          Submit Selection
        </button>
      </div>
    </div>
  );
}

function CodeCompletionInput({
  prediction,
  onSubmit,
  disabled,
  theme,
}: {
  prediction: CCType;
  onSubmit: (answer: string) => void;
  disabled: boolean;
  theme: string;
}) {
  const [code, setCode] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);

  const handleSubmit = () => {
    if (!code.trim() || disabled) return;
    const trimmed = code.trim();
    const correct =
      trimmed === prediction.correctCode.trim() ||
      (prediction.acceptableVariants ?? []).some((v) => trimmed === v.trim());
    setIsCorrect(correct);
    setSubmitted(true);
    onSubmit(trimmed);
  };

  return (
    <div className="space-y-3">
      {/* Code template display */}
      {prediction.codeTemplate && (
        <pre
          className={`p-3 rounded-lg text-xs font-mono overflow-x-auto ${
            theme === 'dark'
              ? 'bg-gray-900 text-gray-300 border border-gray-700'
              : 'bg-gray-100 text-gray-700 border border-gray-300'
          }`}
        >
          {prediction.codeTemplate}
        </pre>
      )}

      {/* Code input */}
      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="Type your code here..."
        disabled={disabled || submitted}
        rows={3}
        className={`w-full p-3 rounded-lg border-2 font-mono text-sm resize-y focus:outline-none focus:ring-2 focus:ring-primary-500/30 ${
          theme === 'dark'
            ? 'bg-gray-800 border-gray-600 text-white placeholder-gray-500'
            : 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'
        } ${submitted ? 'opacity-70' : ''}`}
      />

      {/* Feedback after submission */}
      {submitted && isCorrect !== null && (
        <div
          className={`text-sm px-3 py-2 rounded-lg ${
            isCorrect
              ? theme === 'dark'
                ? 'bg-green-500/10 text-green-400 border border-green-500/30'
                : 'bg-green-50 text-green-700 border border-green-300'
              : theme === 'dark'
              ? 'bg-red-500/10 text-red-400 border border-red-500/30'
              : 'bg-red-50 text-red-700 border border-red-300'
          }`}
        >
          {isCorrect ? 'Correct!' : 'Incorrect. Expected: '}
          {!isCorrect && (
            <code
              className={`font-mono text-xs ${
                theme === 'dark' ? 'text-red-300' : 'text-red-800'
              }`}
            >
              {prediction.correctCode}
            </code>
          )}
        </div>
      )}

      {!submitted && (
        <div className="flex justify-center">
          <button
            onClick={handleSubmit}
            disabled={disabled || !code.trim()}
            className={`px-6 py-2 rounded-lg font-medium text-sm transition-colors ${
              disabled || !code.trim()
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                : 'bg-primary-500 text-white hover:bg-primary-600'
            }`}
          >
            Submit Code
          </button>
        </div>
      )}
    </div>
  );
}

function TrueFalseInput({
  prediction,
  onSubmit,
  disabled,
  theme,
}: {
  prediction: TFType;
  onSubmit: (answer: boolean) => void;
  disabled: boolean;
  theme: string;
}) {
  const [selected, setSelected] = useState<boolean | null>(null);

  const handleSelect = (answer: boolean) => {
    if (disabled) return;
    setSelected(answer);
    onSubmit(answer);
  };

  return (
    <div className="flex gap-3 justify-center">
      <motion.button
        whileHover={disabled ? {} : { scale: 1.03 }}
        whileTap={disabled ? {} : { scale: 0.97 }}
        onClick={() => handleSelect(true)}
        disabled={disabled}
        className={`px-8 py-3 rounded-lg font-semibold text-sm transition-all border-2 ${
          selected === true
            ? 'border-green-500 bg-green-500/15'
            : theme === 'dark'
            ? 'border-gray-700 bg-gray-800 hover:border-green-500/50'
            : 'border-gray-200 bg-white hover:border-green-400'
        } ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'} ${
          theme === 'dark' ? 'text-green-400' : 'text-green-700'
        }`}
      >
        True
      </motion.button>
      <motion.button
        whileHover={disabled ? {} : { scale: 1.03 }}
        whileTap={disabled ? {} : { scale: 0.97 }}
        onClick={() => handleSelect(false)}
        disabled={disabled}
        className={`px-8 py-3 rounded-lg font-semibold text-sm transition-all border-2 ${
          selected === false
            ? 'border-red-500 bg-red-500/15'
            : theme === 'dark'
            ? 'border-gray-700 bg-gray-800 hover:border-red-500/50'
            : 'border-gray-200 bg-white hover:border-red-400'
        } ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'} ${
          theme === 'dark' ? 'text-red-400' : 'text-red-700'
        }`}
      >
        False
      </motion.button>
    </div>
  );
}

export default function PredictionPanel({
  prediction,
  onSubmit,
  disabled = false,
  theme = 'dark',
}: PredictionPanelProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-4 rounded-lg border-2 ${
        theme === 'dark'
          ? 'border-blue-500/30 bg-blue-500/5'
          : 'border-blue-300 bg-blue-50'
      }`}
    >
      <h4
        className={`text-sm font-semibold mb-3 ${
          theme === 'dark' ? 'text-blue-300' : 'text-blue-700'
        }`}
      >
        {prediction.prompt}
      </h4>

      {prediction.type === 'arrangement' && (
        <ArrangementPrediction
          elements={prediction.elements}
          onSubmit={(arr) => onSubmit(arr)}
          disabled={disabled}
          theme={theme}
        />
      )}

      {prediction.type === 'value' && (
        <ValueInput
          prediction={prediction}
          onSubmit={(v) => onSubmit(v)}
          disabled={disabled}
          theme={theme}
        />
      )}

      {prediction.type === 'multiple_choice' && (
        <MultipleChoiceInput
          prediction={prediction}
          onSubmit={(id) => onSubmit(id)}
          disabled={disabled}
          theme={theme}
        />
      )}

      {prediction.type === 'multi_select' && (
        <MultiSelectInput
          prediction={prediction}
          onSubmit={(ids) => onSubmit(ids)}
          disabled={disabled}
          theme={theme}
        />
      )}

      {prediction.type === 'code_completion' && (
        <CodeCompletionInput
          prediction={prediction as CCType}
          onSubmit={(code) => onSubmit(code)}
          disabled={disabled}
          theme={theme}
        />
      )}

      {prediction.type === 'true_false' && (
        <TrueFalseInput
          prediction={prediction as TFType}
          onSubmit={(answer) => onSubmit(answer)}
          disabled={disabled}
          theme={theme}
        />
      )}

      {/* Fallback for unknown prediction types */}
      {!['arrangement', 'value', 'multiple_choice', 'multi_select', 'code_completion', 'true_false'].includes(
        prediction.type,
      ) && (
        <div
          className={`text-sm italic ${
            theme === 'dark' ? 'text-gray-400' : 'text-gray-500'
          }`}
        >
          Unsupported prediction type: {(prediction as { type: string }).type}
        </div>
      )}
    </motion.div>
  );
}
