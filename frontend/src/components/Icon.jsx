/** Consistent 20px stroke icon set — no emoji anywhere in the product. */
const PATHS = {
  pulse: <><path d="M3 12h3.5l2-5.5 4 11 2-5.5H21" /></>,
  route: <><circle cx="6" cy="19" r="2.2" /><circle cx="18" cy="5" r="2.2" /><path d="M8.2 19H14a3.5 3.5 0 0 0 0-7h-4a3.5 3.5 0 0 1 0-7h5.8" /></>,
  folder: <path d="M3.5 6.5A1.5 1.5 0 0 1 5 5h4l2 2.5h8a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 19 18.5H5A1.5 1.5 0 0 1 3.5 17z" />,
  monitor: <><rect x="3.5" y="4.5" width="17" height="13" rx="1.8" /><path d="M8 21h8M12 17.5V21" /><path d="M6.8 11h2l1.4-3 2.4 6 1.4-3h3" /></>,
  calendar: <><rect x="3.5" y="5" width="17" height="15.5" rx="1.8" /><path d="M3.5 9.5h17M8 3v3.5M16 3v3.5" /></>,
  phone: <path d="M20.5 16.6v2.6a1.7 1.7 0 0 1-1.9 1.7 17 17 0 0 1-7.4-2.6 16.6 16.6 0 0 1-5.1-5.1A17 17 0 0 1 3.5 5.8 1.7 1.7 0 0 1 5.2 4h2.6a1.7 1.7 0 0 1 1.7 1.4c.1.9.3 1.7.6 2.5a1.7 1.7 0 0 1-.4 1.8l-1.1 1.1a13.6 13.6 0 0 0 5.1 5.1l1.1-1.1a1.7 1.7 0 0 1 1.8-.4c.8.3 1.6.5 2.5.6a1.7 1.7 0 0 1 1.4 1.7z" />,
  chat: <path d="M20.5 12a8.5 7.6 0 0 1-8.5 7.6 9 9 0 0 1-3.2-.6L4 20.5l1.5-4A7.3 7.3 0 0 1 3.5 12 8.5 7.6 0 0 1 12 4.4a8.5 7.6 0 0 1 8.5 7.6z" />,
  flask: <path d="M10 3.5h4M10.5 3.5v5L5.2 17.6A2 2 0 0 0 7 20.5h10a2 2 0 0 0 1.8-2.9L13.5 8.5v-5M8 14h8" />,
  stethoscope: <><path d="M5 3.5v5a4.5 4.5 0 0 0 9 0v-5" /><path d="M9.5 3v1M9.5 4H5.2M14 4H9.7" opacity="0" /><path d="M9.5 12.5v3a4.5 4.5 0 0 0 9 0v-2.2" /><circle cx="18.5" cy="10.8" r="2" /></>,
  shield: <path d="M12 3.5l7 2.6v5.4c0 4.4-3 7.7-7 9-4-1.3-7-4.6-7-9V6.1z" />,
  alert: <><path d="M12 4L2.8 19.5h18.4z" /><path d="M12 10v4M12 16.8v.4" /></>,
  check: <path d="M4.5 12.5l5 5L19.5 7" />,
  x: <path d="M6 6l12 12M18 6L6 18" />,
  arrowRight: <path d="M4.5 12h15M13.5 6l6 6-6 6" />,
  clock: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2.5" /></>,
  file: <><path d="M6 3.5h8L19 8.5V19a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 5 19V5A1.5 1.5 0 0 1 6.5 3.5z" /><path d="M13.5 3.5V9H19" /></>,
  user: <><circle cx="12" cy="8" r="3.8" /><path d="M4.5 20.5a7.5 7.5 0 0 1 15 0" /></>,
  refresh: <><path d="M20 12a8 8 0 1 1-2.3-5.6M20 3.5V8h-4.5" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  logout: <><path d="M14.5 8V5.5A1.5 1.5 0 0 0 13 4H6a1.5 1.5 0 0 0-1.5 1.5v11A1.5 1.5 0 0 0 6 18h7a1.5 1.5 0 0 0 1.5-1.5V14" /><path d="M10 12h10.5M17 8.5l3.5 3.5-3.5 3.5" /></>,
  bell: <><path d="M18 9.5a6 6 0 1 0-12 0c0 6-2.5 7-2.5 7h17s-2.5-1-2.5-7" /><path d="M10 20a2.2 2.2 0 0 0 4 0" /></>,
  book: <><path d="M4.5 5A1.5 1.5 0 0 1 6 3.5h13.5V18H6A1.5 1.5 0 0 0 4.5 19.5z" /><path d="M4.5 19.5A1.5 1.5 0 0 0 6 21h13.5" /></>,
  heart: <path d="M12 20s-7.5-4.6-7.5-10A4.3 4.3 0 0 1 12 7a4.3 4.3 0 0 1 7.5 3c0 5.4-7.5 10-7.5 10z" />,
  target: <><circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="4.5" /><circle cx="12" cy="12" r="1" fill="currentColor" /></>,
}

export default function Icon({ name, size = 18, strokeWidth = 1.9, className = '', style }) {
  const path = PATHS[name]
  if (!path) return null
  return (
    <svg
      className={className}
      style={style}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {path}
    </svg>
  )
}
