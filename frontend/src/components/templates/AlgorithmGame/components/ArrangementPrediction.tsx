'use client';

import { useState, useCallback } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  horizontalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { motion } from 'framer-motion';

interface ArrangementPredictionProps {
  elements: number[];
  onSubmit: (arrangement: number[]) => void;
  disabled?: boolean;
  theme?: 'dark' | 'light';
}

function SortableItem({
  id,
  value,
  theme,
}: {
  id: string;
  value: number;
  theme: string;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 10 : 0,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`
        w-14 h-14 flex items-center justify-center rounded-lg
        font-mono text-lg font-bold cursor-grab active:cursor-grabbing
        border-2 select-none touch-none
        transition-shadow
        ${isDragging ? 'shadow-xl scale-110' : 'shadow-sm'}
        ${
          theme === 'dark'
            ? 'bg-gray-700 border-gray-600 text-white hover:border-blue-400'
            : 'bg-white border-gray-300 text-gray-900 hover:border-blue-500'
        }
      `}
    >
      {value}
    </div>
  );
}

export default function ArrangementPrediction({
  elements,
  onSubmit,
  disabled = false,
  theme = 'dark',
}: ArrangementPredictionProps) {
  const [items, setItems] = useState(() =>
    elements.map((val, idx) => ({ id: `item-${idx}`, value: val })),
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      setItems((prev) => {
        const oldIndex = prev.findIndex((i) => i.id === active.id);
        const newIndex = prev.findIndex((i) => i.id === over.id);
        return arrayMove(prev, oldIndex, newIndex);
      });
    },
    [],
  );

  const handleSubmit = useCallback(() => {
    onSubmit(items.map((i) => i.value));
  }, [items, onSubmit]);

  return (
    <div className="space-y-3">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={items.map((i) => i.id)}
          strategy={horizontalListSortingStrategy}
          disabled={disabled}
        >
          <div className="flex gap-2 justify-center py-2">
            {items.map((item) => (
              <SortableItem
                key={item.id}
                id={item.id}
                value={item.value}
                theme={theme}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <div className="flex justify-center">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleSubmit}
          disabled={disabled}
          className={`
            px-6 py-2 rounded-lg font-medium text-sm transition-colors
            ${
              disabled
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                : 'bg-primary-500 text-white hover:bg-primary-600'
            }
          `}
        >
          Submit Arrangement
        </motion.button>
      </div>
    </div>
  );
}
