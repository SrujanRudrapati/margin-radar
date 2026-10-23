export function Loading({ what }: { what: string }) {
  return <p role="status" className="py-10 text-muted">Loading {what}…</p>;
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="rounded-panel border border-dashed border-grid px-5 py-8 text-muted">{children}</div>;
}

export function ErrorNote({ what, error }: { what: string; error: string }) {
  return (
    <div role="alert" className="rounded-panel border border-risk/40 bg-riskwash px-5 py-4">
      <p className="font-semibold">Couldn't load {what}.</p>
      <p className="mt-1 text-sm text-muted">{error}. Check that the API is running (make api) or rebuild the static export (make export).</p>
    </div>
  );
}
