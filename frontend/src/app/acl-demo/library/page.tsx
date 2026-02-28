import { Suspense } from 'react';
import LibraryClient from './LibraryClient';

export default function ACLDemoLibraryPage() {
  return (
    <Suspense fallback={<div className="animate-pulse p-8"><div className="h-64 bg-gray-200 rounded" /></div>}>
      <LibraryClient />
    </Suspense>
  );
}
