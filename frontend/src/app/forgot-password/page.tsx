import Link from "next/link";

import { ForgotPasswordForm } from "../../components/ForgotPasswordForm";

export default function ForgotPasswordPage() {
  return (
    <>
      <Link className="back-link" href="/">
        Back to dashboard
      </Link>
      <ForgotPasswordForm />
    </>
  );
}
