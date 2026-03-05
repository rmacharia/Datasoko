import { AuthGuard } from "@/components/auth-guard";

type Props = {
  title: string;
  description: string;
};

export function PlaceholderPage({ title, description }: Props) {
  return (
    <AuthGuard>
      <main className="mx-auto max-w-6xl p-4 md:p-6">
        <section className="card p-6">
          <h1 className="text-2xl font-semibold">{title}</h1>
          <p className="mt-2 text-sm muted">{description}</p>
          <p className="mt-4 text-sm muted">This screen is scaffolded and reserved for the next implementation step.</p>
        </section>
      </main>
    </AuthGuard>
  );
}
