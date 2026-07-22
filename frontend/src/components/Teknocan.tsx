/**
 * Giriş ekranında kullanıcıyı karşılayan özgün maskot illüstrasyonu.
 * Turkcell'in Teknocan konseptinden esinlenir ama kendi çizimimizdir.
 */
export function Teknocan() {
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-20 hidden select-none flex-col items-end gap-2 sm:flex md:bottom-10 md:right-10">
      <div className="pointer-events-auto mr-2 max-w-[190px] rounded-2xl rounded-br-sm bg-white px-4 py-3 text-sm font-medium text-tc-navy-900 shadow-xl">
        Merhaba! 👋 Ben Teknocan.
        <br />
        NetOpsCell'e hoş geldin!
      </div>

      <svg
        viewBox="0 0 160 190"
        className="h-36 w-auto animate-mascot-float drop-shadow-2xl md:h-44"
        aria-hidden="true"
      >
        <ellipse cx="80" cy="178" rx="34" ry="7" fill="#000000" opacity="0.15" />

        <line x1="80" y1="10" x2="80" y2="34" stroke="#253342" strokeWidth="4" strokeLinecap="round" />
        <circle cx="80" cy="8" r="6" fill="#ffc900" />

        <rect x="42" y="32" width="76" height="58" rx="24" fill="#2855ac" />
        <rect x="54" y="50" width="52" height="22" rx="11" fill="#e9f1ff" />
        <circle cx="70" cy="61" r="6" fill="#253342" />
        <circle cx="90" cy="61" r="6" fill="#253342" />
        <path d="M72 66 Q80 71 88 66" stroke="#253342" strokeWidth="2.5" fill="none" strokeLinecap="round" />

        <rect x="36" y="88" width="88" height="72" rx="26" fill="#f4f7fb" stroke="#2855ac" strokeWidth="3" />
        <rect x="63" y="108" width="34" height="34" rx="10" fill="#ffc900" />
        <path
          d="M74 125h12M80 119v12"
          stroke="#253342"
          strokeWidth="3"
          strokeLinecap="round"
        />

        <g className="animate-mascot-wave">
          <path
            d="M116 104c14-4 24-16 22-28"
            stroke="#2855ac"
            strokeWidth="10"
            fill="none"
            strokeLinecap="round"
          />
          <circle cx="139" cy="75" r="8" fill="#f4c9a0" />
        </g>
        <path
          d="M44 104c-14-2-24 8-24 20"
          stroke="#2855ac"
          strokeWidth="10"
          fill="none"
          strokeLinecap="round"
        />
        <circle cx="20" cy="126" r="8" fill="#f4c9a0" />

        <ellipse cx="58" cy="150" rx="14" ry="9" fill="#2855ac" />
        <ellipse cx="102" cy="150" rx="14" ry="9" fill="#2855ac" />
      </svg>
    </div>
  )
}
