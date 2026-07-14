import Link from "next/link";

import { VerifyEmailForm } from "../../components/VerifyEmailForm";

type VerifyEmailPageProps = {
  searchParams?: Promise<{
    email?: string | string[];
    resendCooldown?: string | string[];
  }>;
};

export default async function VerifyEmailPage({ searchParams }: VerifyEmailPageProps) {
  const resolvedSearchParams = searchParams === undefined ? undefined : await searchParams;
  const rawEmail = resolvedSearchParams?.email;
  const rawResendCooldown = resolvedSearchParams?.resendCooldown;
  const initialEmail = Array.isArray(rawEmail) ? rawEmail[0] : rawEmail ?? "";
  const initialResendCooldown = parseInitialCooldown(rawResendCooldown);

  return (
    <>
      <Link className="back-link" href="/">
        Back to dashboard
      </Link>
      <VerifyEmailForm
        initialEmail={initialEmail}
        initialResendCooldownSeconds={initialResendCooldown}
      />
    </>
  );
}

function parseInitialCooldown(rawValue: string | string[] | undefined): number {
  const value = Array.isArray(rawValue) ? rawValue[0] : rawValue;
  const parsed = Number(value);

  if (!Number.isInteger(parsed) || parsed < 0) {
    return 0;
  }

  return parsed;
}
