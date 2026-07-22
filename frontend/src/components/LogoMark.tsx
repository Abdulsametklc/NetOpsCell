interface LogoMarkProps {
  className?: string
}

/** Sarı kare içinde anten/sinyal ikonu — kurumsal logo yerine kullanılan özgün sembol. */
export function LogoMark({ className = 'h-9 w-9' }: LogoMarkProps) {
  return (
    <span className={`flex items-center justify-center rounded-md bg-tc-yellow-500 text-tc-navy-950 ${className}`}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-[60%] w-[60%]">
        <path strokeLinecap="round" d="M12 4v16" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4l-2.4 2.4M12 4l2.4 2.4" />
        <path strokeLinecap="round" d="M7.8 9.6a6 6 0 018.4 0" />
        <path strokeLinecap="round" d="M9.6 12a3.4 3.4 0 014.8 0" />
      </svg>
    </span>
  )
}
