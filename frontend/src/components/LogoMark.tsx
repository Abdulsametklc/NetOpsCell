import turkcellLogo from '../assets/turkcell_logo.jpg'

interface LogoMarkProps {
  className?: string
}

export function LogoMark({ className = 'h-9 w-9' }: LogoMarkProps) {
  return (
    <span className={`inline-flex overflow-hidden rounded-full ${className}`}>
      <img src={turkcellLogo} alt="NetOpsCell logosu" className="h-full w-full object-cover" />
    </span>
  )
}
