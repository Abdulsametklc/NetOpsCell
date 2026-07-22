import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'

type Variant = 'primary' | 'secondary' | 'danger' | 'success' | 'ghost'
type Size = 'sm' | 'md'

const base =
  'inline-flex items-center justify-center gap-1.5 rounded-lg font-semibold transition disabled:cursor-not-allowed disabled:opacity-60'

const variantClass: Record<Variant, string> = {
  primary: 'bg-tc-yellow-500 text-tc-navy-950 hover:bg-tc-yellow-400',
  secondary:
    'border border-slate-300 bg-white text-tc-navy-800 hover:bg-slate-50 dark:border-tc-navy-600 dark:bg-transparent dark:text-slate-200 dark:hover:bg-tc-navy-800',
  danger: 'bg-rose-600 text-white hover:bg-rose-500',
  success: 'bg-emerald-600 text-white hover:bg-emerald-500',
  ghost: 'text-tc-navy-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-tc-navy-800',
}

const sizeClass: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
}

export function Button({ variant = 'secondary', size = 'md', className = '', ...props }: ButtonProps) {
  return (
    <button
      className={`${base} ${variantClass[variant]} ${sizeClass[size]} ${className}`}
      {...props}
    />
  )
}

interface CardProps {
  className?: string
  children: ReactNode
  as?: 'div' | 'form'
  [key: string]: unknown
}

export function Card({ className = '', children, as = 'div', ...rest }: CardProps) {
  const Tag = as
  return (
    <Tag
      className={`rounded-xl border border-slate-200 bg-white shadow-sm dark:border-tc-navy-800 dark:bg-tc-navy-900/60 ${className}`}
      {...rest}
    >
      {children}
    </Tag>
  )
}

const fieldBase =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-tc-navy-950 outline-none transition placeholder:text-slate-400 focus:border-tc-yellow-500 focus:ring-2 focus:ring-tc-yellow-500/30 dark:border-tc-navy-600 dark:bg-tc-navy-950 dark:text-slate-100 dark:placeholder:text-slate-500'

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={fieldBase} {...props} />
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={fieldBase} {...props} />
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={fieldBase} {...props} />
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">{label}</span>
      {children}
    </label>
  )
}

export function Pill({
  active,
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      type="button"
      className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${
        active
          ? 'bg-tc-yellow-500 text-tc-navy-950'
          : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-tc-navy-800 dark:text-slate-300 dark:hover:bg-tc-navy-700'
      } ${className}`}
      {...props}
    />
  )
}
