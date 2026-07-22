/**
 * Giriş ekranında kullanıcıyı karşılayan özgün maskot illüstrasyonu.
 * Turkcell'in Teknocan konseptinden esinlenir ama kendi çizimimizdir.
 */
export function Teknocan() {
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-20 hidden select-none flex-col items-end gap-2 sm:flex md:bottom-8 md:right-10">
      <div className="pointer-events-auto mr-4 max-w-[190px] rounded-2xl rounded-br-sm bg-white px-4 py-3 text-sm font-medium text-tc-navy-900 shadow-xl">
        Merhaba! 👋 Ben Teknocan.
        <br />
        NetOpsCell'e hoş geldin!
      </div>

      <svg
        viewBox="0 0 160 230"
        className="h-44 w-auto animate-mascot-float drop-shadow-2xl md:h-56"
        aria-hidden="true"
      >
        <ellipse cx="82" cy="222" rx="38" ry="7" fill="#000000" opacity="0.15" />

        {/* sol anten */}
        <path d="M62 26 C50 18 42 8 40 -2" stroke="#e6b400" strokeWidth="6" fill="none" strokeLinecap="round" />
        <circle cx="39" cy="-6" r="8" fill="#ffc900" stroke="#e6b400" strokeWidth="2" />
        {/* sağ (uzun) anten */}
        <path d="M96 22 C100 8 98 -8 92 -20" stroke="#e6b400" strokeWidth="6" fill="none" strokeLinecap="round" />
        <circle cx="90" cy="-24" r="8" fill="#ffc900" stroke="#e6b400" strokeWidth="2" />

        {/* kulak silindirleri */}
        <rect x="20" y="58" width="18" height="30" rx="8" fill="#e6b400" />
        <rect x="122" y="58" width="18" height="30" rx="8" fill="#e6b400" />

        {/* kafa */}
        <ellipse cx="80" cy="72" rx="48" ry="44" fill="#ffc900" />
        <ellipse cx="80" cy="86" rx="48" ry="26" fill="#f2ba00" opacity="0.55" />

        {/* kaşlar */}
        <path d="M50 56 Q59 49 68 55" stroke="#1c2733" strokeWidth="4" fill="none" strokeLinecap="round" />
        <path d="M92 55 Q101 49 110 56" stroke="#1c2733" strokeWidth="4" fill="none" strokeLinecap="round" />

        {/* gözler */}
        <circle cx="61" cy="74" r="16" fill="#16212c" />
        <circle cx="99" cy="74" r="16" fill="#16212c" />
        <circle cx="56" cy="68" r="4.5" fill="#ffffff" />
        <circle cx="94" cy="68" r="4.5" fill="#ffffff" />

        {/* gülümseme */}
        <path d="M68 96 Q80 106 92 96" stroke="#16212c" strokeWidth="4" fill="none" strokeLinecap="round" />

        {/* boyun */}
        <rect x="68" y="112" width="24" height="14" fill="#ffc900" />

        {/* gövde: lacivert ceket + beyaz gömlek */}
        <rect x="34" y="120" width="92" height="76" rx="30" fill="#253342" />
        <rect x="58" y="128" width="44" height="68" rx="16" fill="#f4f7fb" />
        <circle cx="80" cy="146" r="2.6" fill="#94a3b8" />
        <circle cx="80" cy="158" r="2.6" fill="#94a3b8" />
        <circle cx="80" cy="170" r="2.6" fill="#94a3b8" />

        {/* sol kol (aşağıda) */}
        <path d="M40 132c-16 6-22 20-20 36" stroke="#2f4256" strokeWidth="16" fill="none" strokeLinecap="round" />
        <circle cx="22" cy="172" r="13" fill="#ffc900" />

        {/* sağ kol (el sallıyor) */}
        <g className="animate-mascot-wave">
          <path d="M120 130c18 2 30-8 32-24" stroke="#2f4256" strokeWidth="16" fill="none" strokeLinecap="round" />
          <circle cx="154" cy="102" r="13" fill="#ffc900" />
        </g>

        {/* bacaklar */}
        <rect x="48" y="192" width="26" height="30" rx="10" fill="#cbb994" />
        <rect x="86" y="192" width="26" height="30" rx="10" fill="#cbb994" />

        {/* ayakkabılar */}
        <rect x="42" y="214" width="34" height="14" rx="7" fill="#f7f9fb" stroke="#cbd5e1" strokeWidth="1.5" />
        <rect x="84" y="214" width="34" height="14" rx="7" fill="#f7f9fb" stroke="#cbd5e1" strokeWidth="1.5" />
      </svg>
    </div>
  )
}
