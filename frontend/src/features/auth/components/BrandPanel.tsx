// input: bg-grain 纹理 utility (index.css)
// output: BrandPanel 组件 —— 登录页右侧画廊式品牌面板（纸色装裱 + CSS 月夜画 + 作品标签）
// pos: auth feature - 登录页右侧视觉锚(纯装饰，非语义 UI)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md

export function BrandPanel() {
  return (
    <aside aria-hidden className="relative hidden lg:block lg:w-[54%]">
      {/* 画面：纸色留边装裱（inset = 画框卡纸） */}
      <div className="absolute inset-7 bottom-20 overflow-hidden rounded-[2px] bg-[linear-gradient(180deg,#0d1626_0%,#1c3850_44%,#3d6a80_60%,#c99b64_72%,#23201c_72.6%,#171512_100%)]">
        {/* 月亮 */}
        <div className="absolute left-[32%] top-[22%] size-[150px] rounded-full bg-[radial-gradient(circle_at_38%_34%,#f5eddb,#e4d6b4)] shadow-[0_0_90px_30px_rgba(240,225,190,0.28)]" />
        {/* 海面月光倒影 */}
        <div className="absolute left-[30%] top-[72.6%] h-[18%] w-[19%] bg-[linear-gradient(180deg,rgba(240,225,190,0.22),transparent)] blur-[2px]" />
        {/* 胶片颗粒 */}
        <div className="absolute inset-0 bg-grain opacity-15 mix-blend-overlay" />
      </div>

      {/* 画廊式作品标签 */}
      <p className="font-serif text-ink-faint absolute bottom-7 left-8 text-[13.5px]">
        《想法，即产品》{' '}
        <span className="font-display text-ink-ghost italic">no.01 — vibejet studio, 2026</span>
      </p>
    </aside>
  )
}
