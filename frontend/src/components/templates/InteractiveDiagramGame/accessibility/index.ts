/**
 * Accessibility exports for WCAG 2.2 Level AA compliance
 *
 * Provides:
 * - Keyboard navigation
 * - Screen reader announcements
 * - Focus management
 * - ARIA live regions
 */

export {
  KeyboardNav,
  useKeyboardNav,
  type KeyboardNavConfig,
  type KeyboardNavProps,
} from './KeyboardNav';

export {
  AnnouncementProvider,
  useAnnouncements,
  Announce,
  type AnnouncementPriority,
  type Announcement,
  type GameAction,
} from './ScreenReaderAnnouncements';
