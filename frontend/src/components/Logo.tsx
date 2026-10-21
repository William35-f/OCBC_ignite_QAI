// Text logo: "Q AI by Quadrant" with four small squares in a 2x2 grid.
export default function Logo() {
  return (
    <div className="flex items-center gap-2.5" aria-label="Q AI by Quadrant">
      <div className="grid grid-cols-2 gap-0.5" aria-hidden="true">
        <span className="h-2.5 w-2.5 rounded-[3px] bg-brand" />
        <span className="h-2.5 w-2.5 rounded-[3px] bg-ink" />
        <span className="h-2.5 w-2.5 rounded-[3px] bg-ink" />
        <span className="h-2.5 w-2.5 rounded-[3px] bg-brand-dark" />
      </div>
      <div className="leading-tight">
        <span className="text-lg font-bold text-ink">Q AI</span>
        <span className="ml-1.5 text-xs font-medium text-ink-muted">by Quadrant</span>
      </div>
    </div>
  );
}
