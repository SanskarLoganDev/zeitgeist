import { DashboardClient } from "../components/DashboardClient";
import { getDashboard } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const dashboard = await getDashboard();

  return <DashboardClient dashboard={dashboard} />;
}
