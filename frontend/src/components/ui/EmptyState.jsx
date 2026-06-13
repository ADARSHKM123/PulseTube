export default function EmptyState({ icon: Icon, title, hint, action }) {
  return (
    <div className="card flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      {Icon && (
        <div className="rounded-2xl border border-line bg-raised p-3.5 text-muted">
          <Icon size={26} strokeWidth={1.8} />
        </div>
      )}
      <div>
        <h3 className="text-base font-semibold">{title}</h3>
        {hint && <p className="mx-auto mt-1 max-w-md text-sm text-muted">{hint}</p>}
      </div>
      {action}
    </div>
  );
}
