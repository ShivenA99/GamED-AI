'use client';

import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';

interface DraggableLabelProps {
  id: string;
  text: string;
  isDragging?: boolean;
  isIncorrect?: boolean;
}

export default function DraggableLabel({
  id,
  text,
  isDragging,
  isIncorrect,
}: DraggableLabelProps) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id,
  });

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={`
        px-4 py-2 rounded-lg cursor-grab active:cursor-grabbing
        font-medium text-sm shadow-md
        transition-all duration-200
        select-none
        ${
          isIncorrect
            ? 'bg-red-100 border-2 border-red-400 text-red-800 animate-shake'
            : 'bg-white border-2 border-primary-300 text-gray-800 hover:border-primary-500 hover:shadow-lg'
        }
      `}
    >
      {text}
    </div>
  );
}
