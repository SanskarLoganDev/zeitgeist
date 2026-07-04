import Link from "next/link";

import { LoginForm } from "../../components/LoginForm";

export default function LoginPage() {
  return (
    <>
      <Link className="back-link" href="/">
        Back to dashboard
      </Link>
      <LoginForm mode="login" />
    </>
  );
}
