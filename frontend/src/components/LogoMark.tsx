interface LogoMarkProps {
  className?: string
}

/** Turkcell amblemini anımsatan sarı disk + çift virgül sembolü — özgün vektör çizim. */
export function LogoMark({ className = 'h-9 w-9' }: LogoMarkProps) {
  const comma = 'M0,-38 C21,-13 30,6 30,19 A30,30 0 1,1 -30,19 C-30,6 -21,-13 0,-38 Z'
  return (
    <svg viewBox="0 0 100 100" className={className} role="img" aria-label="NetOpsCell logosu">
      <circle cx="50" cy="50" r="50" fill="#ffc900" />
      <g fill="#ffffff">
        <path d={comma} transform="translate(33,32) rotate(-42) scale(0.6)" />
        <path d={comma} transform="translate(60,62) rotate(-42) scale(0.78)" />
      </g>
    </svg>
  )
}
